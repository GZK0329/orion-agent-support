"""
FTS5 全文检索服务（BM25）
在 SQLite FTS5 虚拟表中建立文档块倒排索引，用于混合搜索中的关键词检索
"""
import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

from langchain.schema import Document
from loguru import logger

from app.config import settings


class FTSSearch:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (settings.vector_db_dir / "fts_index.db")
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            with self._lock:
                if self._conn is None:
                    self.db_path.parent.mkdir(parents=True, exist_ok=True)
                    self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                    self._conn.execute("PRAGMA journal_mode=WAL")
                    self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def _execute(self, sql: str, params=()) -> sqlite3.Cursor:
        conn = self._connect()
        with self._lock:
            return conn.execute(sql, params)

    def _commit(self) -> None:
        with self._lock:
            self._connect().commit()

    def create_index(self) -> None:
        self._execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS doc_chunks_fts USING fts5("
            "  chunk_id UNINDEXED,"
            "  source UNINDEXED,"
            "  content,"
            "  tokenize='porter unicode61'"
            ")"
        )
        self._execute(
            "CREATE TABLE IF NOT EXISTS chunk_metadata ("
            "  chunk_id TEXT PRIMARY KEY,"
            "  source TEXT NOT NULL,"
            "  metadata TEXT NOT NULL"
            ")"
        )
        self._commit()
        logger.info("FTS5 索引已就绪")

    def index_documents(self, chunks: List[Document]) -> int:
        self.create_index()
        count = 0
        for chunk in chunks:
            chunk_id = _chunk_id(chunk)
            content = chunk.page_content
            source = chunk.metadata.get("source", "unknown")
            meta_json = json.dumps(chunk.metadata, ensure_ascii=False)
            try:
                self._execute(
                    "INSERT OR REPLACE INTO doc_chunks_fts (chunk_id, source, content) VALUES (?, ?, ?)",
                    (chunk_id, source, content),
                )
                self._execute(
                    "INSERT OR REPLACE INTO chunk_metadata (chunk_id, source, metadata) VALUES (?, ?, ?)",
                    (chunk_id, source, meta_json),
                )
                count += 1
            except Exception as e:
                logger.warning(f"FTS 索引写入失败 chunk={chunk_id}: {e}")
        self._commit()
        logger.debug(f"FTS5 索引已更新: {count} 块")
        return count

    def delete_by_source(self, source: str) -> int:
        rows = self._execute(
            "SELECT chunk_id FROM chunk_metadata WHERE source = ?", (source,)
        ).fetchall()
        ids = [r[0] for r in rows]
        if not ids:
            return 0
        for cid in ids:
            self._execute("DELETE FROM doc_chunks_fts WHERE chunk_id = ?", (cid,))
            self._execute("DELETE FROM chunk_metadata WHERE chunk_id = ?", (cid,))
        self._commit()
        logger.debug(f"FTS5 已删除 source={source}: {len(ids)} 块")
        return len(ids)

    def delete_all(self) -> None:
        self._execute("DELETE FROM doc_chunks_fts")
        self._execute("DELETE FROM chunk_metadata")
        self._commit()
        logger.info("FTS5 索引已清空")

    def search(self, query: str, top_k: int = 20) -> List[Document]:
        fts_query = _to_fts_query(query)
        if not fts_query:
            return []
        rows = self._execute(
            "SELECT c.chunk_id, c.content, m.source, m.metadata "
            "FROM doc_chunks_fts c "
            "JOIN chunk_metadata m ON c.chunk_id = m.chunk_id "
            "WHERE doc_chunks_fts MATCH ? "
            "ORDER BY rank "
            "LIMIT ?",
            (fts_query, top_k),
        ).fetchall()
        docs: List[Document] = []
        for rank, (chunk_id, content, source, meta_json) in enumerate(rows):
            meta = json.loads(meta_json) if meta_json else {}
            meta["source"] = source
            meta["_bm25_rank"] = rank
            docs.append(Document(page_content=content, metadata=meta))
        logger.debug(f"BM25 检索: q={query[:30]}... → {len(docs)} 结果")
        return docs

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def _chunk_id(chunk: Document) -> str:
    raw = f"{chunk.metadata.get('source', '')}:{chunk.page_content}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _to_fts_query(user_query: str) -> str:
    terms = user_query.strip().split()
    if not terms:
        return ""
    fts_terms = []
    for t in terms:
        cleaned = t.translate(str.maketrans('', '', "'\"(),;:!?."))
        if cleaned:
            fts_terms.append(f'"{cleaned}"')
    return " AND ".join(fts_terms) if fts_terms else ""


fts_search = FTSSearch()
