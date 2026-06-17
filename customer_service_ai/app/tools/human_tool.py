"""
转人工 Tool
模拟转人工服务（调度组件上下文）
"""
from langchain_core.tools import tool


@tool
def transfer_to_human(reason: str = "") -> str:
    """
    转接调度组件开发人员。
    当用户需要后端开发人员介入、报告调度组件 bug、需求沟通，或问题超出文档范围无法处理时使用。
    如果用户未提供原因，可设置为空字符串。
    """
    reason_text = f"（原因：{reason}）" if reason else ""
    return f"已为您转接调度组件开发人员，请稍候，我们将优先为您服务{reason_text}。"
