"""
对话 API
提供 /chat（同步） 和 /chat/stream（流式） 接口
支持会话摘要记忆：对话结束时异步生成摘要，回头客自动恢复上下文
"""
import asyncio
import json

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger

from app.agent.agent_service import chat as agent_chat
from app.agent.agent_service import chat_stream as agent_chat_stream
from app.config import settings
from app.memory.session_store import session_store
from app.models.schemas import ChatRequest, ChatResponse
from app.services.llm_service import get_llm

router = APIRouter(prefix="/chat", tags=["智能客服对话"])

SUMMARY_PROMPT = "请用一句话概括以下对话的核心主题和关键结论（30字以内，不要编造）：\n\n{dialog}"


async def _generate_summary(session_id: str) -> None:
    """异步生成对话摘要并存入 DB"""
    try:
        history = await session_store.get_history(session_id, max_tokens=4000)
        if len(history) < 2:
            return

        dialog = "\n".join(
            f"{'用户' if isinstance(m, HumanMessage) else 'AI'}: {m.content[:200]}"
            for m in history[-6:]
        )

        llm = get_llm()
        result = await llm.ainvoke(SUMMARY_PROMPT.format(dialog=dialog))
        summary = result.content.strip() if hasattr(result, "content") else str(result).strip()

        if summary:
            await session_store.update_summary(session_id, summary)
            logger.debug(f"会话 {session_id[:8]} 摘要已更新: {summary[:40]}")
    except Exception as e:
        logger.warning(f"生成摘要失败（不影响主流程）: {e}")


async def _get_history_with_summary(session_id: str) -> list:
    """获取历史消息，如果有摘要则注入到最前面"""
    history = await session_store.get_history(
        session_id, max_tokens=settings.context_max_tokens
    )
    summary = await session_store.get_summary(session_id)
    if summary and history:
        history.insert(0, SystemMessage(content=f"之前的对话摘要：{summary}"))
    return history


@router.post(
    "/",
    response_model=ChatResponse,
    summary="客服问答（同步）",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """同步问答接口"""
    session_id = request.session_id
    client_id = request.client_id
    try:
        history = await _get_history_with_summary(session_id)
        loop = asyncio.get_running_loop()
        answer = await loop.run_in_executor(
            None, agent_chat, request.question, history,
        )
        await session_store.add_messages(session_id, [
            HumanMessage(content=request.question),
            AIMessage(content=answer),
        ], client_id=client_id)
        asyncio.create_task(_generate_summary(session_id))
    except Exception as e:
        logger.opt(exception=True).error(f"chat 同步失败: {e}")
        await session_store.add_error_log(
            session_id=session_id,
            client_id=client_id,
            question=request.question,
            error_message=str(e),
            source="chat_sync",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"模型调用失败: {str(e)}",
        )
    return ChatResponse(answer=answer, session_id=session_id)


@router.post(
    "/stream",
    summary="客服问答（流式）",
    description="SSE 流式返回回答，适用于前端渐进显示",
)
async def chat_stream(request: ChatRequest):
    """流式问答接口 — 真正的 LLM token-by-token 流式"""
    session_id = request.session_id
    client_id = request.client_id

    async def event_stream():
        full_answer: list[str] = []
        try:
            history = await _get_history_with_summary(session_id)

            async for token in agent_chat_stream(request.question, history):
                full_answer.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

            answer = "".join(full_answer)
            await session_store.add_messages(session_id, [
                HumanMessage(content=request.question),
                AIMessage(content=answer),
            ], client_id=client_id)
            asyncio.create_task(_generate_summary(session_id))

        except Exception as e:
            logger.opt(exception=True).error(f"chat stream 失败: {e}")
            await session_store.add_error_log(
                session_id=session_id,
                client_id=client_id,
                question=request.question,
                error_message=str(e),
                source="chat_stream",
            )
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
