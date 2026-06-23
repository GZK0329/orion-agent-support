"""
RAG（检索增强生成）核心服务
负责文档向量化存储、检索和生成回答

检索管线：
  MultiQuery(4 queries)
    → Hybrid Search (Vector + BM25 via RRF)
    → MMR 多样性重排(k=20)
    → Reranker 精排(top k)
    → LLM 生成回答

支持：响应缓存、混合搜索、多级 Embedding 回退、知识库版本过滤
"""
import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.schema import Document
from langchain_core.embeddings import Embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from app.config import settings
from app.prompts.customer_service import get_rag_prompt
from app.services.embedding_service import get_embedding_model
from app.services.fts_service import fts_search
from app.services.llm_service import get_llm
from app.services.reranker_service import reranker

CACHE: Dict[str, Tuple[float, dict]] = {}
_ACTIVE_VERSION_ID: Optional[int] = None

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


# ── 缓存 ──────────────────────────────────────────────────────────────

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


# ── 向量库 ────────────────────────────────────────────────────────────

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
    fts_search.index_documents(documents)


def delete_by_source(source: str) -> None:
    vector_store = get_vector_store()
    vector_store.delete(where={"source": source})
    fts_search.delete_by_source(source)


# ── 文本切分 ──────────────────────────────────────────────────────────

def get_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n\n", "\n", "。", "；", " ", ""],
    )


# ── 知识库版本管理 ────────────────────────────────────────────────────

def _get_active_version() -> Optional[dict]:
    from app.database import SessionLocal
    from app.models.db_models import KbVersion
    try:
        with SessionLocal() as session:
            v = session.query(KbVersion).filter_by(is_active=1).first()
            if v:
                return {"id": v.id, "description": v.description, "file_count": v.file_count,
                        "chunk_count": v.chunk_count, "created_at": str(v.created_at)}
    except Exception as e:
        logger.warning(f"获取活跃版本失败: {e}")
    return None


def _set_active_version(version_id: int) -> bool:
    from app.database import SessionLocal
    from app.models.db_models import KbVersion
    try:
        with SessionLocal() as session:
            v = session.query(KbVersion).filter_by(id=version_id).first()
            if not v:
                logger.error(f"版本 #{version_id} 不存在")
                return False
            session.query(KbVersion).filter_by(is_active=1).update({"is_active": 0})
            v.is_active = 1
            session.commit()
            return True
    except Exception as e:
        logger.warning(f"设置活跃版本失败: {e}")
        return False


def create_version(description: str = "", file_count: int = 0, chunk_count: int = 0,
                   file_manifest: Optional[dict] = None) -> Optional[int]:
    from app.database import SessionLocal
    from app.models.db_models import KbVersion
    try:
        with SessionLocal() as session:
            session.query(KbVersion).filter_by(is_active=1).update({"is_active": 0})
            v = KbVersion(
                description=description or f"重建 {time.strftime('%Y-%m-%d %H:%M:%S')}",
                file_count=file_count,
                chunk_count=chunk_count,
                file_manifest=json.dumps(file_manifest or {}, ensure_ascii=False),
                is_active=1,
            )
            session.add(v)
            session.commit()
            session.refresh(v)
            logger.info(f"已创建知识库版本 #{v.id}: {description}")
            return v.id
    except Exception as e:
        logger.error(f"创建版本失败: {e}")
        return None


def list_versions() -> List[dict]:
    from app.database import SessionLocal
    from app.models.db_models import KbVersion
    try:
        with SessionLocal() as session:
            versions = session.query(KbVersion).order_by(KbVersion.id.desc()).all()
            return [{"id": v.id, "description": v.description, "file_count": v.file_count,
                     "chunk_count": v.chunk_count, "is_active": bool(v.is_active),
                     "created_at": str(v.created_at)} for v in versions]
    except Exception as e:
        logger.warning(f"列出版本失败: {e}")
        return []


def rollback_version(version_id: int) -> bool:
    ok = _set_active_version(version_id)
    if ok:
        logger.info(f"已回滚到知识库版本 #{version_id}")
    else:
        logger.error(f"回滚到版本 #{version_id} 失败")
    return ok


# ── 混合检索 ──────────────────────────────────────────────────────────

def _reciprocal_rank_fusion(
    vector_docs: List[Document],
    bm25_docs: List[Document],
    k: int = 60,
) -> List[Document]:
    seen: Dict[str, float] = {}
    for rank, doc in enumerate(vector_docs):
        cid = _doc_key(doc)
        seen[cid] = seen.get(cid, 0.0) + 1.0 / (k + rank)
    for rank, doc in enumerate(bm25_docs):
        cid = _doc_key(doc)
        seen[cid] = seen.get(cid, 0.0) + 1.0 / (k + rank)
    sorted_ids = sorted(seen, key=seen.get, reverse=True)
    id_to_doc: Dict[str, Document] = {}
    for doc in vector_docs:
        id_to_doc[_doc_key(doc)] = doc
    for doc in bm25_docs:
        id_to_doc.setdefault(_doc_key(doc), doc)
    return [id_to_doc[cid] for cid in sorted_ids if cid in id_to_doc]


def _doc_key(doc: Document) -> str:
    import hashlib
    raw = f"{doc.metadata.get('source', '')}:{doc.page_content[:100]}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _hybrid_search(
    query: str,
    vector_store: Chroma,
    embedding: Embeddings,
    top_k: int = 20,
) -> Tuple[List[Document], float]:
    query_embedding = embedding.embed_query(query)
    vector_results = vector_store.similarity_search_by_vector(
        embedding=query_embedding,
        k=settings.hybrid_search_fetch_k,
    )

    bm25_results = fts_search.search(query, top_k=settings.hybrid_search_fetch_k)

    alpha = settings.hybrid_search_alpha
    if not settings.hybrid_search_enabled or not bm25_results:
        docs = vector_results[:top_k]
    elif not vector_results:
        docs = bm25_results[:top_k]
    else:
        combined = _reciprocal_rank_fusion(
            vector_results, bm25_results, k=settings.hybrid_search_rrf_k
        )
        docs = combined[:top_k]

    confidence = 1.0
    if len(docs) > settings.retrieval_rerank_top_k:
        docs, confidence = reranker.rerank(query, docs, settings.retrieval_rerank_top_k)

    return docs, confidence


def _generate_query_variants(question: str) -> List[str]:
    try:
        llm = get_llm()
        messages = _MQ_PROMPT.format_messages(question=question)
        response = llm.invoke(messages)
        variants = [line.strip().lstrip("1234567890.、- ") for line in response.content.strip().split("\n") if line.strip()]
        variants = [v for v in variants if len(v) > 3][:3]
        if variants:
            logger.debug(f"MultiQuery 变体: {variants}")
            return variants
    except Exception as e:
        logger.warning(f"MultiQuery 生成失败: {e}")
    return []


def retrieve(query_text: str) -> Tuple[List[Document], float]:
    logger.debug(f"检索问题: {query_text[:50]}...")
    vector_store = get_vector_store()
    embedding = get_embedding_model()
    variants = _generate_query_variants(query_text)
    all_queries = [query_text] + variants

    all_docs: List[Document] = []
    seen_keys: set = set()
    for q in all_queries:
        docs, _ = _hybrid_search(q, vector_store, embedding, top_k=settings.retrieval_rerank_candidate_k)
        for d in docs:
            k = _doc_key(d)
            if k not in seen_keys:
                seen_keys.add(k)
                all_docs.append(d)

    logger.debug(f"混合检索召回: {len(all_docs)} 篇（去重后）")

    # 截断到 reranker 候选数
    if len(all_docs) > settings.retrieval_rerank_candidate_k:
        all_docs = all_docs[:settings.retrieval_rerank_candidate_k]

    confidence = 1.0
    if len(all_docs) > settings.retrieval_rerank_top_k:
        all_docs, confidence = reranker.rerank(
            query_text, all_docs, settings.retrieval_rerank_top_k
        )

    return all_docs, confidence


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
