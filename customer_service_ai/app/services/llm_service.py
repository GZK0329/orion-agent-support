"""
LLM 客户端初始化
DeepSeek 兼容 OpenAI API，因此使用 langchain_openai 的 ChatOpenAI
"""
from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm() -> ChatOpenAI:
    """获取配置好的 LLM 实例"""
    return ChatOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )
