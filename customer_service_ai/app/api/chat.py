"""
对话 API
提供 /chat（同步） 和 /chat/stream（流式） 接口
"""
import asyncio
import json

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.agent_service import chat as agent_chat
from app.config import settings
from app.memory.session_store import session_store
from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["智能客服对话"])


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
        history = session_store.get_history(
            session_id, max_tokens=settings.context_max_tokens
        )
        answer = agent_chat(request.question, chat_history=history)
        session_store.add_messages(session_id, [
            HumanMessage(content=request.question),
            AIMessage(content=answer),
        ], client_id=client_id)
    except Exception as e:
        session_store.add_error_log(
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
    """流式问答接口"""
    session_id = request.session_id
    client_id = request.client_id

    async def event_stream():
        try:
            history = session_store.get_history(
                session_id, max_tokens=settings.context_max_tokens
            )
            loop = asyncio.get_event_loop()

            # 在独立线程中运行 agent（避免阻塞事件循环）
            answer = await loop.run_in_executor(
                None, agent_chat, request.question, history,
            )

            # 逐字输出
            for char in answer:
                yield f"data: {json.dumps({'token': char})}\n\n"
                await asyncio.sleep(0.008)

            yield f"data: {json.dumps({'done': True})}\n\n"

            # 流式完成后记录会话
            session_store.add_messages(session_id, [
                HumanMessage(content=request.question),
                AIMessage(content=answer),
            ], client_id=client_id)

        except Exception as e:
            session_store.add_error_log(
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
