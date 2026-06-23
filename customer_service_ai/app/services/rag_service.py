"""
RAG（检索增强生成）核心服务
负责文档向量化存储、检索和生成回答
支持 MultiQuery 改写 + MMR 粗排 + Reranker 精排 + 响应缓存
"""
import hashlib
import time
from typing import List, Optional, Tuple

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.retrievers import MultiQueryRetriever
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from loguru import logger

from app.config import settings
from app.prompts.customer_service import get_rag_prompt
from app.services.embedding_service import get_embedding_model
from app.services.llm_service import get_llm
from app.services.reranker_service import reranker

CACHE: dict[str, Tuple[float, dict]] = {}

_MQ_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "你是一个调度组件文档检索专家。用户问题可能不精确，"
        "请从不同角度改写搜索词，包含接口名、功能描述词、业务术语。"
        "调度组件常见接口: saveCommonJobPlan, updateCommonJobPlan, listJobPlan, "
        "deleteJobPlan, saveK8sJobPlan, saveShellJobPlan。"
        "调度组件核心概念: 作业计划(jobPlan)、作业(job)、作业分片(分片/slice)、"
        "工作流(workflow)、资源组、程序包、Cron 调度。"
        "每个搜索词一行，生成 3 个，不要编号。"
    )),
    ("human", "{question}"),
])


def _cache_key(question: str) -> str:
    return hashlib.md5(question.strip().encode()).hexdigest()


def _cache_get(question: str) -> Optional[dict]:
    if not settings.cache_enabled:
        return None
    key = _cache_key(question)
    entry = CACHE.get(key)
    if entry is None:
        return None
    ts, result = entry
    if time.time() - ts > settings.cache_ttl:
        del CACHE[key]
        return None
    logger.debug(f"缓存命中: {question[:30]}...")
    return result


def _cache_set(question: str, result: dict) -> None:
    if not settings.cache_enabled:
        return
    if len(CACHE) >= settings.cache_max_entries:
        oldest = min(CACHE, key=lambda k: CACHE[k][0])
        del CACHE[oldest]
    CACHE[_cache_key(question)] = (time.time(), result)


def get_vector_store() -> Chroma:
    embedding = get_embedding_model()
    settings.vector_db_dir.mkdir(parents=True, exist_ok=True)

    return Chroma(
        persist_directory=str(settings.vector_db_dir),
        embedding_function=embedding,
        collection_name=settings.collection_name,
    )


def build_vector_store(documents: List[Document]) -> Chroma:
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
    vector_store = get_vector_store()
    vector_store.add_documents(documents)


def delete_by_source(source: str) -> None:
    vector_store = get_vector_store()
    vector_store.delete(where={"source": source})


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """获取统一的文本分块器（ingest.py 和 documents.py 共用，避免配置漂移）"""
    return RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n\n", "\n", "。", "；", " ", ""],
    )


def _make_base_retriever(vector_store: Chroma):
    return vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": settings.retrieval_rerank_candidate_k,
            "fetch_k": max(settings.retrieval_rerank_candidate_k * 2, 50),
            "lambda_mult": settings.retrieval_lambda_mult,
        },
    )


def retrieve(query_text: str) -> Tuple[List[Document], float]:
    """返回 (精排后的文档列表, 置信度分数 0~1)"""
    vector_store = get_vector_store()
    base_retriever = _make_base_retriever(vector_store)
    llm = get_llm()

    retriever = MultiQueryRetriever.from_llm(
        retriever=base_retriever,
        llm=llm,
        prompt=_MQ_PROMPT,
        include_original=True,
    )

    logger.debug(f"检索问题: {query_text[:50]}...")
    docs = retriever.invoke(query_text)
    logger.debug(f"MMR 粗排召回: {len(docs)} 篇")

    confidence = 1.0
    if len(docs) > settings.retrieval_rerank_top_k:
        docs, confidence = reranker.rerank(
            query_text, docs, settings.retrieval_rerank_top_k
        )

    return docs, confidence


def get_context(question: str) -> Tuple[List[Document], float]:
    return retrieve(question)


def query(question: str) -> dict:
    cached = _cache_get(question)
    if cached is not None:
        return cached

    docs, confidence = retrieve(question)

    llm = get_llm()
    prompt = get_rag_prompt()
    combine_docs_chain = create_stuff_documents_chain(llm, prompt)

    result = combine_docs_chain.invoke({
        "context": docs,
        "input": question,
    })

    if confidence < settings.confidence_threshold:
        result = f"> ⚠️ **以下回答仅供参考**（检索置信度较低，建议核实）\n\n{result}"
        logger.info(f"低置信度回答: confidence={confidence:.3f}, q={question[:30]}")

    output = {"answer": result, "context": docs, "confidence": confidence}
    _cache_set(question, output)
    return output
