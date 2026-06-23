"""
Agent 编排服务
组装 Tool、LLM、Prompt 为可调用的 Agent
"""
from typing import AsyncGenerator, List, Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool
from loguru import logger

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


async def chat_stream(
    question: str,
    chat_history: Optional[List[BaseMessage]] = None,
    verbose: bool = False,
) -> AsyncGenerator[str, None]:
    """
    流式执行 Agent 对话，逐 token 产出最终回答文本。
    过滤中间推理（如"好的，我来查询"）和工具内部 LLM 调用，
    只输出最后一轮不含 tool_call 的 LLM 回答。
    """
    executor = _create_executor(verbose=verbose)
    yielded_any = False

    tool_active = False
    llm_buffer: list[str] = []
    llm_has_tool_call = False

    async for event in executor.astream_events(
        {"input": question, "chat_history": chat_history or []},
        version="v2",
    ):
        kind = event["event"]

        if kind == "on_tool_start":
            tool_active = True
            llm_has_tool_call = True
            llm_buffer = []

        elif kind == "on_tool_end":
            tool_active = False

        elif kind == "on_chat_model_start":
            if not tool_active:
                llm_buffer = []
                llm_has_tool_call = False

        elif kind == "on_chat_model_stream":
            if tool_active:
                continue

            chunk = event["data"].get("chunk")
            if not chunk:
                continue

            if getattr(chunk, "tool_call_chunks", None):
                llm_has_tool_call = True

            text = getattr(chunk, "content", None)
            if text:
                llm_buffer.append(text)

        elif kind == "on_chat_model_end":
            if not tool_active and not llm_has_tool_call and llm_buffer:
                for text in llm_buffer:
                    yielded_any = True
                    yield text
                llm_buffer = []

        elif kind == "on_chain_end" and event.get("name") == "agent":
            if not yielded_any:
                output = event.get("data", {}).get("output", {})
                if isinstance(output, dict) and output.get("output"):
                    yield output["output"]

    logger.debug(f"Agent 流式完成")
