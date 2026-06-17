"""
调度组件文档查询 Tool
包装现有的 RAG 服务，供 Agent 调用
"""
from langchain_core.tools import tool

from app.services.rag_service import query as rag_query


@tool
def search_documentation(question: str) -> str:
    """
    查询调度组件的接口文档、参数说明、请求示例和最佳实践。
    当用户询问调度组件的接口地址、请求参数、返回参数、请求示例、错误码等任何需要查阅文档才能回答的问题时使用。
    根据问题在知识库中检索最相关的内容并返回。
    注意：这是获取调度组件接口文档的唯一途径！
    """
    result = rag_query(question)
    return result.get("answer", "抱歉，知识库中没有找到相关信息。")
