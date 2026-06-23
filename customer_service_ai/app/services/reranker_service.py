"""
Reranker 精排服务
使用 SiliconFlow / Jina 等 OpenAI 兼容提供商的 /rerank 接口
对 MMR 粗排结果做二次精排，集成断路器保护
返回精排后的文档列表和 top relevance_score（供置信度评估使用）
"""
from typing import List, Tuple

import httpx
from langchain.schema import Document
from loguru import logger

from app.config import settings
from app.utils.circuit_breaker import reranker_breaker
from app.utils.retry import with_retry


class RerankerService:

    def __init__(self):
        api_key = settings.reranker_api_key or settings.embedding_api_key
        base_url = (settings.reranker_base_url or settings.embedding_base_url).rstrip("/")
        self._api_key = api_key
        self._base_url = base_url
        self._endpoint = f"{base_url}/rerank"
        self.model = settings.reranker_model
        self._available = bool(api_key) and api_key != "test-dummy-key"

    @with_retry(max_attempts=2, operation_name="Reranker API")
    def _call_rerank_api(self, query: str, documents: List[str]) -> List[float]:
        resp = httpx.post(
            self._endpoint,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": len(documents),
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        scores = [0.0] * len(documents)
        for item in data.get("results", []):
            idx = item.get("index", -1)
            score = item.get("relevance_score", 0.0)
            if 0 <= idx < len(scores):
                scores[idx] = score
        return scores

    def rerank(
        self, query: str, docs: List[Document], top_k: int
    ) -> Tuple[List[Document], float]:
        """返回 (精排后的文档列表, top relevance_score)"""
        if not docs:
            return docs, 0.0

        if not self._available:
            logger.debug("Reranker 未配置有效 API Key，跳过精排")
            return docs[:top_k], 0.0

        try:
            texts = [d.page_content for d in docs]

            def _do_rerank():
                return self._call_rerank_api(query, texts)

            scores = reranker_breaker.call(_do_rerank)
            scored = list(zip(docs, scores))
            scored.sort(key=lambda x: x[1], reverse=True)
            top_score = scored[0][1] if scored else 0.0
            reranked = [d for d, s in scored[:top_k]]
            logger.debug(
                f"Reranker 精排: {len(docs)}→{len(reranked)}, "
                f"top score={top_score:.3f}"
            )
            return reranked, top_score
        except Exception as e:
            logger.warning(f"Reranker 失败，降级使用原始排序: {e}")
            return docs[:top_k], 0.0


reranker = RerankerService()
