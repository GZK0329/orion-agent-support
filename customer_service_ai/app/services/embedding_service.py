"""
Embedding 模型初始化
用于将文本转换为向量，支持 OpenAI 兼容的 Embedding 服务
"""
from typing import List

from langchain_core.embeddings import Embeddings
from openai import OpenAI

from app.config import settings


class OpenAICompatibleEmbeddings(Embeddings):
    """
    兼容 OpenAI API 格式的 Embedding 客户端
    直接用 openai SDK 调用，避免 LangChain 传递服务商不支持的参数
    """

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本向量（自动分批，防止超过服务商限制）"""
        BATCH_SIZE = 20
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
            )
            all_embeddings.extend(item.embedding for item in response.data)
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """获取单个查询文本的向量"""
        response = self.client.embeddings.create(
            model=self.model,
            input=[text],
        )
        return response.data[0].embedding


def get_embedding_model() -> Embeddings:
    """获取配置好的 Embedding 模型实例"""
    return OpenAICompatibleEmbeddings(
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        model=settings.embedding_model,
    )
