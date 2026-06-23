"""
RAG 检索质量评测脚本

用法:
    cd customer_service_ai && python scripts/eval_rag.py

会自动加载 tests/golden_set.json，逐一检索并统计召回率。
"""
import json
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger
from app.services.rag_service import retrieve

GOLDEN_FILE = PROJECT_ROOT / "tests" / "golden_set.json"


def _eval_keyword_recall(docs: List, keywords: List[str]) -> float:
    """计算关键词在检索文档中的召回率"""
    if not keywords:
        return 1.0
    all_text = " ".join(d.page_content for d in docs).lower()
    hits = sum(1 for kw in keywords if kw.lower() in all_text)
    return hits / len(keywords)


def main():
    if not GOLDEN_FILE.exists():
        logger.error(f"Golden QA 文件不存在: {GOLDEN_FILE}")
        sys.exit(1)

    with open(GOLDEN_FILE, encoding="utf-8") as f:
        golden = json.load(f)

    items = golden.get("items", [])
    logger.info(f"加载 {len(items)} 条 Golden QA，开始评测...")

    total_keyword_recall = 0.0
    total_doc_recall = 0.0
    results: List[dict] = []

    for item in items:
        qid = item["id"]
        question = item["question"]
        keywords = item.get("keywords", [])
        min_docs = item.get("min_docs", 1)

        try:
            docs = retrieve(question)
        except Exception as e:
            logger.error(f"Q{qid:02d} 检索失败: {e}")
            results.append({
                "id": qid,
                "question": question[:50],
                "keyword_recall": 0.0,
                "doc_count": 0,
                "min_docs": min_docs,
                "status": "ERROR",
            })
            continue

        kw_recall = _eval_keyword_recall(docs, keywords)
        doc_count = len(docs)
        doc_ok = doc_count >= min_docs

        total_keyword_recall += kw_recall
        total_doc_recall += 1.0 if doc_ok else 0.0

        status = "✓" if kw_recall >= 0.6 else "✗"
        results.append({
            "id": qid,
            "question": question[:50],
            "keyword_recall": round(kw_recall, 3),
            "doc_count": doc_count,
            "min_docs": min_docs,
            "status": "PASS" if kw_recall >= 0.6 else "FAIL",
        })
        logger.info(
            f"{status} Q{qid:02d}: keyword_recall={kw_recall:.2f}, "
            f"docs={doc_count}/{min_docs}, "
            f"q={question[:40]}..."
        )

    n = len(items)
    avg_kw_recall = total_keyword_recall / n if n else 0
    avg_doc_recall = total_doc_recall / n if n else 0
    passed = sum(1 for r in results if r["status"] == "PASS")

    print("\n" + "=" * 60)
    print(f"评测完成: {n} 条")
    print(f"  平均关键词召回率: {avg_kw_recall:.2%}")
    print(f"  文档数量达标率:   {avg_doc_recall:.2%}")
    print(f"  通过 (recall≥60%): {passed}/{n}")
    print("=" * 60)

    fail_items = [r for r in results if r["status"] == "FAIL"]
    if fail_items:
        print("\n需改进的问题:")
        for r in fail_items:
            print(f"  Q{r['id']:02d}: {r['question']} (recall={r['keyword_recall']})")


if __name__ == "__main__":
    main()
