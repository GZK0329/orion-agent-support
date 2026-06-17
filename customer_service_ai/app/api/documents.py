"""
文档管理 API
支持上传、列表、删除、全量重建，上传后自动增量导入向量库
管理员权限控制：需要 X-Admin-Token header
"""
import shutil
from pathlib import Path

from fastapi import APIRouter, File, Header, HTTPException, UploadFile, status
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from pydantic import BaseModel

from app.api.auth import validate_admin_token
from app.services.rag_service import add_documents, build_vector_store, delete_by_source

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


def _split_text(texts: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500, chunk_overlap=200,
        separators=["\n\n", "\n", "。", "；", " ", ""],
    )
    return splitter.split_documents(texts)


@router.get("/")
async def list_documents(x_admin_token: str = Header(default="")):
    """列出已上传的文档（仅管理员）"""
    _require_admin(x_admin_token)
    return _list_files()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    x_admin_token: str = Header(default=""),
):
    """上传文档并自动导入向量库（仅管理员）"""
    _require_admin(x_admin_token)

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {ext}，支持 {ALLOWED_EXT}")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    save_path = DOCS_DIR / file.filename  # type: ignore

    with open(save_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    try:
        if ext == ".pdf":
            docs = PyPDFLoader(str(save_path)).load()
        else:
            docs = TextLoader(str(save_path), encoding="utf-8").load()

        for d in docs:
            d.metadata["source"] = file.filename
        chunks = _split_text(docs)
        add_documents(chunks)

        return {"message": f"导入成功，共 {len(chunks)} 个文本块", "filename": file.filename}
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/reindex")
async def reindex_documents(x_admin_token: str = Header(default="")):
    """全量重建向量库（基于 data/docs/ 下所有文档，仅管理员）"""
    _require_admin(x_admin_token)

    if not DOCS_DIR.exists() or not any(DOCS_DIR.iterdir()):
        raise HTTPException(status_code=400, detail="文档目录为空，请先上传文档")

    documents: list[Document] = []
    for ext, loader_cls in [("**/*.txt", TextLoader), ("**/*.md", TextLoader), ("**/*.pdf", PyPDFLoader)]:
        loader = DirectoryLoader(str(DOCS_DIR), glob=ext, loader_cls=loader_cls, show_progress=False)
        documents.extend(loader.load())

    chunks = _split_text(documents)
    for chunk in chunks:
        src = chunk.metadata.get("source", "")
        if src:
            chunk.metadata["source"] = str(Path(src).resolve().relative_to(DOCS_DIR))

    build_vector_store(chunks)
    return {"message": f"向量库重建完成，共 {len(chunks)} 个文本块", "total_chunks": len(chunks)}


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    filename: str,
    x_admin_token: str = Header(default=""),
):
    """删除文档并从向量库移除（仅管理员）"""
    _require_admin(x_admin_token)
    delete_by_source(filename)
    (DOCS_DIR / filename).unlink(missing_ok=True)
