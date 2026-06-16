"""
转人工 Tool
模拟转人工服务
"""
from langchain_core.tools import tool


@tool
def transfer_to_human(reason: str = "") -> str:
    """
    转接人工客服。
    当用户明确要求转人工、投诉、遇到复杂问题工具无法解决时使用。
    如果用户未提供原因，可设置为空字符串。
    """
    reason_text = f"（原因：{reason}）" if reason else ""
    return f"已为您转接人工客服，请稍候，我们将优先为您服务{reason_text}。"
