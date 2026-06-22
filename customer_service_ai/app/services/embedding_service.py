"""
Embedding 模型初始化
用于将文本转换为向量，支持 OpenAI 兼容的 Embedding 服务
"""
from typing import List

from langchain_core.embeddings import Embeddings
from loguru import logger
from openai import OpenAI

from app.config import settings
from app.utils.retry import with_retry


class OpenAICompatibleEmbeddings(Embeddings):
    """
    兼容 OpenAI API 格式的 Embedding 客户端
    直接用 openai SDK 调用，避免 LangChain 传递服务商不支持的参数
    """

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    @with_retry(max_attempts=3, operation_name="Embedding API")
    def _call_embedding_api(self, batch: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model=self.model,
            input=batch,
            timeout=30,
        )
        return [item.embedding for item in response.data]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本向量（自动分批，防止超过服务商限制）"""
        BATCH_SIZE = 20
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            try:
                embeddings = self._call_embedding_api(batch)
                all_embeddings.extend(embeddings)
            except Exception as e:
                logger.error(f"Embedding batch {i // BATCH_SIZE} 失败: {e}")
                raise
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """获取单个查询文本的向量"""
        return self._call_embedding_api([text])[0]


def get_embedding_model() -> Embeddings:
    """获取配置好的 Embedding 模型实例"""
    return OpenAICompatibleEmbeddings(
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        model=settings.embedding_model,
    )
