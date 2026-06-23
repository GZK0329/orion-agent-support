"""
对话 API
提供 /chat（同步） 和 /chat/stream（流式） 接口
支持会话摘要记忆：对话结束时 Celery 任务生成摘要，回头客自动恢复上下文
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
from app.middleware.rate_limit import limiter
from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["智能客服对话"])


async def _get_history_with_summary(session_id: str) -> list:
    """获取历史消息，如果有摘要则注入到最前面"""
    history = await session_store.get_history(
        session_id, max_tokens=settings.context_max_tokens
    )
    summary = await session_store.get_summary(session_id)
    if summary and history:
        history.insert(0, SystemMessage(content=f"之前的对话摘要：{summary}"))
    return history


def _dispatch_summary(session_id: str) -> None:
    """异步派发摘要生成任务（Celery Worker 执行，不阻塞 HTTP 响应）"""
    from app.celery_app import celery_app
    if celery_app is None:
        return
    try:
        from app.tasks.summary_task import generate_summary
        generate_summary.delay(session_id)
        logger.debug(f"摘要任务已派发: {session_id[:8]}")
    except Exception as e:
        logger.warning(f"摘要任务派发失败（不影响主流程）: {e}")


@router.post(
    "/",
    response_model=ChatResponse,
    summary="客服问答（同步）",
)
@limiter.limit(settings.rate_limit_chat)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    """同步问答接口"""
    session_id = body.session_id
    client_id = body.client_id
    try:
        history = await _get_history_with_summary(session_id)
        loop = asyncio.get_running_loop()
        answer = await loop.run_in_executor(
            None, agent_chat, body.question, history,
        )
        await session_store.add_messages(session_id, [
            HumanMessage(content=body.question),
            AIMessage(content=answer),
        ], client_id=client_id)
        _dispatch_summary(session_id)
    except Exception as e:
        logger.opt(exception=True).error(f"chat 同步失败: {e}")
        await session_store.add_error_log(
            session_id=session_id,
            client_id=client_id,
            question=body.question,
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
@limiter.limit(settings.rate_limit_chat_stream)
async def chat_stream(body: ChatRequest, request: Request):
    """流式问答接口 — 真正的 LLM token-by-token 流式"""
    session_id = body.session_id
    client_id = body.client_id

    async def event_stream():
        full_answer: list[str] = []
        try:
            history = await _get_history_with_summary(session_id)

            async for token in agent_chat_stream(body.question, history):
                full_answer.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

            answer = "".join(full_answer)
            await session_store.add_messages(session_id, [
                HumanMessage(content=body.question),
                AIMessage(content=answer),
            ], client_id=client_id)
            _dispatch_summary(session_id)

        except Exception as e:
            logger.opt(exception=True).error(f"chat stream 失败: {e}")
            await session_store.add_error_log(
                session_id=session_id,
                client_id=client_id,
                question=body.question,
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
