"""
知识库文档加载与导入脚本
支持全量重建（默认）和增量更新两种模式

使用方法：
    # 全量重建
    python scripts/ingest.py

    # 增量更新（只处理变化的文件）
    python scripts/ingest.py --incremental
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保无论从哪运行都能导入 app 包
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
)

from app.services.rag_service import (
    add_documents,
    build_vector_store,
    delete_by_source,
)

DOCS_DIR = Path(__file__).parent.parent / "data" / "docs"
INDEX_FILE = Path(__file__).parent.parent / "data" / "vector_db" / ".file_index.json"


def _compute_file_hash(filepath: Path) -> str:
    """计算文件的 MD5 哈希"""
    return hashlib.md5(filepath.read_bytes()).hexdigest()


def _load_index() -> dict:
    """加载文件索引"""
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text())
    return {"files": {}}


def _save_index(index: dict) -> None:
    """保存文件索引"""
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2))


def load_documents(docs_dir: Path) -> list[Document]:
    """加载指定目录下的文档"""
    docs_dir = docs_dir.resolve()
    if not docs_dir.exists():
        raise FileNotFoundError(f"文档目录不存在: {docs_dir}")

    documents: list[Document] = []

    txt_loader = DirectoryLoader(
        str(docs_dir),
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    documents.extend(txt_loader.load())

    md_loader = DirectoryLoader(
        str(docs_dir),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    documents.extend(md_loader.load())

    pdf_loader = DirectoryLoader(
        str(docs_dir),
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True,
    )
    documents.extend(pdf_loader.load())

    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    """将文档切分为固定大小的文本块，并在 metadata 中标记来源"""
    # BAAI/bge-large-zh-v1.5 最大输入 512 tokens（约 600~800 中文字符）
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", "。", "；", " ", ""],
    )
    return text_splitter.split_documents(documents)


def build_label_chunks(docs_dir: Path) -> list[Document]:
    """加载并切分文档，将 source 统一为相对路径（和增量模式一致）"""
    documents = load_documents(docs_dir)
    chunks = split_documents(documents)
    for chunk in chunks:
        src = chunk.metadata.get("source", "")
        if src:
            chunk.metadata["source"] = str(Path(src).resolve().relative_to(docs_dir))
    return chunks


def incremental_sync(docs_dir: Path) -> None:
    """
    增量同步：对比文件索引，只处理新增或变化的文件
    """
    docs_dir = docs_dir.resolve()
    index = _load_index()
    old_files = index.get("files", {})

    # 扫描当前所有文件
    current_files: dict[str, str] = {}
    for ext in ("**/*.txt", "**/*.md", "**/*.pdf"):
        for fpath in docs_dir.glob(ext):
            rel_path = str(fpath.relative_to(docs_dir))
            current_files[rel_path] = _compute_file_hash(fpath)

    # 处理被删除的文件
    for rel_path in list(old_files):
        if rel_path not in current_files:
            print(f"  删除: {rel_path}")
            delete_by_source(rel_path)
    deleted = [f for f in old_files if f not in current_files]
    if deleted:
        print(f"已从向量库移除 {len(deleted)} 个已删除文件")

    # 处理新增或修改的文件
    changed = {
        f: h for f, h in current_files.items()
        if f not in old_files or old_files[f] != h
    }

    if not changed:
        print("没有文件发生变化，无需更新。")
        _save_index({"files": current_files})
        return

    print(f"发现 {len(changed)} 个文件发生变化：")

    for rel_path in changed:
        change_type = "新增" if rel_path not in old_files else "修改"
        print(f"  {change_type}: {rel_path}")

        fpath = docs_dir / rel_path
        # 加载文档
        if fpath.suffix == ".pdf":
            loader = PyPDFLoader(str(fpath))
        else:
            loader = TextLoader(str(fpath), encoding="utf-8")
        docs = loader.load()

        # 标记 source 用于增量删除
        for doc in docs:
            doc.metadata["source"] = rel_path

        # 旧数据先删后插
        if rel_path in old_files:
            delete_by_source(rel_path)

        chunks = split_documents(docs)
        add_documents(chunks)
        print(f"  -> 更新 {len(chunks)} 个文本块")

    # 更新索引
    _save_index({"files": current_files})


def main():
    parser = argparse.ArgumentParser(description="知识库文档导入工具")
    parser.add_argument(
        "--incremental", "-i",
        action="store_true",
        help="增量模式：只处理新增或变化的文件",
    )
    args = parser.parse_args()

    docs_dir = DOCS_DIR.resolve()
    if not docs_dir.exists():
        print(f"文档目录不存在: {docs_dir}")
        sys.exit(1)

    if args.incremental:
        print(f"增量模式，扫描目录: {docs_dir}")
        incremental_sync(docs_dir)
        print("增量同步完成！")
    else:
        print(f"全量模式，加载文档目录: {docs_dir}")
        chunks = build_label_chunks(docs_dir)
        print(f"加载 {len(chunks)} 个文本块")
        print("正在构建向量数据库...")
        build_vector_store(chunks)
        print("向量数据库构建完成！")


if __name__ == "__main__":
    main()
