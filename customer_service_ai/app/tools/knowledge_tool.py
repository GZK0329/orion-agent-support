"""
知识库查询 Tool
包装现有的 RAG 服务，供 Agent 调用
"""
from langchain_core.tools import tool

from app.services.rag_service import query as rag_query


@tool
def query_knowledge_base(question: str) -> str:
    """
    查询产品知识库、技术文档、API 接口文档和系统操作说明。
    当用户询问产品政策、售后规则、常见问题、使用指南、接口文档、API 参数、系统功能说明等任何需要查阅文档才能回答的问题时使用。
    根据问题检索知识库中最相关的内容并返回答案。
    注意：这是获取产品信息和技术文档的唯一途径！
    """
    result = rag_query(question)
    return result.get("answer", "抱歉，知识库中没有找到相关信息。")
