"""
Embedding 模型初始化
支持多级回退：primary → fallback → 降级
"""
from typing import List, Optional

from langchain_core.embeddings import Embeddings
from loguru import logger
from openai import OpenAI

from app.config import settings
from app.utils.retry import with_retry


class OpenAICompatibleEmbeddings(Embeddings):
    def __init__(self, api_key: str, base_url: str, model: str, name: str = "primary") -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.name = name

    @with_retry(max_attempts=2, operation_name="Embedding API")
    def _call_embedding_api(self, batch: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model=self.model,
            input=batch,
            timeout=(10, 30),  # connect=10s, read=30s
        )
        return [item.embedding for item in response.data]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        BATCH_SIZE = 20
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            try:
                embeddings = self._call_embedding_api(batch)
                all_embeddings.extend(embeddings)
            except Exception as e:
                logger.error(f"Embedding[{self.name}] batch {i // BATCH_SIZE} 失败: {e}")
                raise
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        return self._call_embedding_api([text])[0]


class EmbeddingFallback(Embeddings):
    """多级回退 Embedding，按顺序尝试每个 provider，失败则切到下一个"""

    def __init__(self, providers: List[OpenAICompatibleEmbeddings]) -> None:
        self.providers = providers

    def _try_embed(self, method: str, texts: List[str]) -> Optional[List[List[float]]]:
        for i, prov in enumerate(self.providers):
            try:
                if method == "documents":
                    return prov.embed_documents(texts)
                else:
                    return [prov.embed_query(texts[0])]
            except Exception as e:
                logger.warning(f"Embedding[{prov.name}] 失败，尝试下一个: {e}")
        logger.error(f"所有 Embedding provider 均不可用")
        return None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        result = self._try_embed("documents", texts)
        if result is None:
            return _zero_embeddings(texts)
        return result

    def embed_query(self, text: str) -> List[float]:
        result = self._try_embed("query", [text])
        if result is None:
            return _zero_embedding()
        return result[0]


def _zero_embedding(dim: int = 1536) -> List[float]:
    return [0.0] * dim


def _zero_embeddings(texts: List[str], dim: int = 1536) -> List[List[float]]:
    return [[0.0] * dim for _ in texts]


def get_embedding_model() -> Embeddings:
    providers: List[OpenAICompatibleEmbeddings] = []
    providers.append(OpenAICompatibleEmbeddings(
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        model=settings.embedding_model,
        name="primary",
    ))
    if settings.embedding_fallback_api_key:
        providers.append(OpenAICompatibleEmbeddings(
            api_key=settings.embedding_fallback_api_key,
            base_url=settings.embedding_fallback_base_url,
            model=settings.embedding_fallback_model,
            name="fallback",
        ))
    if len(providers) == 1:
        return providers[0]
    return EmbeddingFallback(providers)
