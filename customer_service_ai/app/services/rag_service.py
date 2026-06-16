"""
RAG（检索增强生成）核心服务
负责文档向量化存储、检索和生成回答
"""
from pathlib import Path
from typing import List

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.schema import Document
from langchain_chroma import Chroma

from app.config import settings
from app.prompts.customer_service import get_rag_prompt
from app.services.embedding_service import get_embedding_model
from app.services.llm_service import get_llm


def get_vector_store() -> Chroma:
    """
    获取向量数据库实例
    如果目录已存在则加载，不存在则创建空库
    """
    embedding = get_embedding_model()
    settings.vector_db_dir.mkdir(parents=True, exist_ok=True)

    return Chroma(
        persist_directory=str(settings.vector_db_dir),
        embedding_function=embedding,
        collection_name=settings.collection_name,
    )


def build_vector_store(documents: List[Document]) -> Chroma:
    """
    全量重建向量数据库
    先清空集合，再导入所有文档
    """
    embedding = get_embedding_model()
    settings.vector_db_dir.mkdir(parents=True, exist_ok=True)

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embedding,
        persist_directory=str(settings.vector_db_dir),
        collection_name=settings.collection_name,
    )
    return vector_store


def add_documents(documents: List[Document]) -> None:
    """增量添加文档到已有的向量库（不删除已有数据）"""
    vector_store = get_vector_store()
    vector_store.add_documents(documents)


def delete_by_source(source: str) -> None:
    """按文件源路径删除向量库中的对应数据"""
    vector_store = get_vector_store()
    vector_store.delete(where={"source": source})


def get_rag_chain():
    """构建 RAG 问答链"""
    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(
        search_kwargs={"k": settings.retrieval_top_k}
    )

    llm = get_llm()
    prompt = get_rag_prompt()
    combine_docs_chain = create_stuff_documents_chain(llm, prompt)

    return create_retrieval_chain(retriever, combine_docs_chain)


def query(question: str) -> dict:
    """
    对外提供的 RAG 查询接口
    返回包含 answer 和 context 的字典
    """
    chain = get_rag_chain()
    return chain.invoke({"input": question})
