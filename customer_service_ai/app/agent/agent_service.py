"""
Agent 编排服务
组装 Tool、LLM、Prompt 为可调用的 Agent
"""
from typing import List, Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool

from app.prompts.agent_system import AGENT_SYSTEM_PROMPT
from app.services.llm_service import get_llm
from app.tools.human_tool import transfer_to_human
from app.tools.knowledge_tool import search_documentation


def get_tools() -> List[BaseTool]:
    """获取所有可用的 Tool 列表"""
    return [
        search_documentation,
        transfer_to_human,
    ]


def _create_executor(verbose: bool = False) -> AgentExecutor:
    """创建 Agent 执行器（内部使用，每次复用相同的 Tool/LLM/Prompt）"""
    llm = get_llm()
    tools = get_tools()

    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    prompt = ChatPromptTemplate.from_messages([
        ("system", AGENT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        handle_parsing_errors=True,
        max_iterations=5,
        early_stopping_method="force",
    )


def chat(
    question: str,
    chat_history: Optional[List[BaseMessage]] = None,
    verbose: bool = False,
) -> str:
    """
    执行一次 Agent 对话
    返回 AI 的回答文本
    """
    executor = _create_executor(verbose=verbose)
    result = executor.invoke({
        "input": question,
        "chat_history": chat_history or [],
    })
    return result.get("output", "")
