"""
文档管理 API
支持上传、列表、删除、全量重建，上传后自动增量导入向量库
知识库版本管理：每次全量重建自动创建版本，支持列表和回滚
管理员权限控制：需要 X-Admin-Token 或 JWT Bearer token
"""
import hashlib
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, File, Header, HTTPException, UploadFile, status
from langchain.schema import Document
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from pydantic import BaseModel

from app.api.auth import validate_admin_token
from app.services.fts_service import fts_search
from app.services.rag_service import (
    add_documents,
    build_vector_store,
    create_version,
    delete_by_source,
    get_text_splitter,
    list_versions,
    rollback_version,
)

router = APIRouter(prefix="/documents", tags=["文档管理"])
DOCS_DIR = Path(__file__).parent.parent / "data" / "docs"

ALLOWED_EXT = {".txt", ".md", ".pdf"}


class FileItem(BaseModel):
    filename: str
    size: int
    updated_at: str


def _require_admin(x_admin_token: str = Header(default="")) -> None:
    if not validate_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="需要管理员权限")


def _safe_path(filename: str) -> Path:
    target = (DOCS_DIR / filename).resolve()
    if not target.is_relative_to(DOCS_DIR.resolve()):
        raise HTTPException(status_code=400, detail="非法文件名")
    return target


def _list_files() -> list[FileItem]:
    if not DOCS_DIR.exists():
        return []
    items = []
    for f in sorted(DOCS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.suffix.lower() in ALLOWED_EXT:
            stat = f.stat()
            items.append(FileItem(
                filename=f.name,
                size=stat.st_size,
                updated_at=str(stat.st_mtime),
            ))
    return items


def _compute_manifest() -> dict:
    manifest = {}
    if not DOCS_DIR.exists():
        return manifest
    for f in sorted(DOCS_DIR.iterdir()):
        if f.suffix.lower() in ALLOWED_EXT:
            content = f.read_bytes()
            manifest[f.name] = hashlib.md5(content).hexdigest()
    return manifest


def _split_text(texts: list[Document]) -> list[Document]:
    return get_text_splitter().split_documents(texts)


@router.get("/")
async def list_documents(x_admin_token: str = Header(default="")):
    _require_admin(x_admin_token)
    return _list_files()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    x_admin_token: str = Header(default=""),
):
    _require_admin(x_admin_token)

    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {ext}，支持 {ALLOWED_EXT}")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    save_path = _safe_path(filename)

    with open(save_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        if ext == ".pdf":
            docs = PyPDFLoader(str(save_path)).load()
        else:
            docs = TextLoader(str(save_path), encoding="utf-8").load()

        for d in docs:
            d.metadata["source"] = filename
        chunks = _split_text(docs)
        add_documents(chunks)

        return {"message": f"导入成功，共 {len(chunks)} 个文本块", "filename": filename}
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/reindex")
async def reindex_documents(x_admin_token: str = Header(default="")):
    _require_admin(x_admin_token)

    if not DOCS_DIR.exists() or not any(DOCS_DIR.iterdir()):
        raise HTTPException(status_code=400, detail="文档目录为空，请先上传文档")

    manifest = _compute_manifest()

    documents: list[Document] = []
    for ext, loader_cls in [("**/*.txt", TextLoader), ("**/*.md", TextLoader), ("**/*.pdf", PyPDFLoader)]:
        loader = DirectoryLoader(str(DOCS_DIR), glob=ext, loader_cls=loader_cls, show_progress=False)
        documents.extend(loader.load())

    chunks = _split_text(documents)
    for chunk in chunks:
        src = chunk.metadata.get("source", "")
        if src:
            chunk.metadata["source"] = str(Path(src).resolve().relative_to(DOCS_DIR.resolve()))

    version_id = create_version(
        description=f"全量重建 {len(chunks)} 块",
        file_count=len(manifest),
        chunk_count=len(chunks),
        file_manifest=manifest,
    )

    build_vector_store(chunks)
    fts_search.delete_all()
    fts_search.index_documents(chunks)

    return {
        "message": f"向量库重建完成，共 {len(chunks)} 个文本块",
        "total_chunks": len(chunks),
        "version_id": version_id,
    }


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    filename: str,
    x_admin_token: str = Header(default=""),
):
    _require_admin(x_admin_token)
    delete_by_source(filename)
    target = _safe_path(filename)
    target.unlink(missing_ok=True)


# ── 知识库版本管理 ─────────────────────────────────────────────────


@router.get("/versions")
async def get_versions(x_admin_token: str = Header(default="")):
    _require_admin(x_admin_token)
    return list_versions()


@router.post("/versions/{version_id}/rollback")
async def rollback(version_id: int, x_admin_token: str = Header(default="")):
    _require_admin(x_admin_token)
    ok = rollback_version(version_id)
    if not ok:
        raise HTTPException(status_code=400, detail="回滚失败")
    return {"message": f"已回滚到版本 #{version_id}"}
