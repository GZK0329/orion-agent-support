"""
RAG（检索增强生成）核心服务
负责文档向量化存储、检索和生成回答
"""
from pathlib import Path
from typing import List

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.retrievers import MultiQueryRetriever
from langchain.schema import Document
from langchain_core.prompts import ChatPromptTemplate
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


def _make_base_retriever(vector_store: Chroma):
    """构建 MMR 基础检索器（多样性优先）"""
    return vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": settings.retrieval_top_k,
            "fetch_k": settings.retrieval_fetch_k,
            "lambda_mult": settings.retrieval_lambda_mult,
        },
    )


def get_rag_chain():
    """
    构建 RAG 问答链
    使用 MultiQueryRetriever（多查询改写+MMR）提升召回率
    """
    vector_store = get_vector_store()
    base_retriever = _make_base_retriever(vector_store)

    llm = get_llm()

    # 中文多查询改写 prompt：生成 3 个不同表述的中文搜索词
    MQ_PROMPT = ChatPromptTemplate.from_messages([
        ("system", (
            "你是一个中文文档检索助手。你的任务是根据用户的问题，生成 3 个不同的中文搜索词，"
            "用于从知识库中检索相关文档。这些搜索词应该从不同角度改写原问题，"
            "包含可能的接口名（如 jobPlan、listJobPlan 等）、功能描述词和业务术语。"
            "每个搜索词一行，不要编号。"
        )),
        ("human", "{question}"),
    ])

    retriever = MultiQueryRetriever.from_llm(
        retriever=base_retriever,
        llm=llm,
        prompt=MQ_PROMPT,
        include_original=True,
    )

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
