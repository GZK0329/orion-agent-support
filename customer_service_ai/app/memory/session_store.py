"""
会话记忆存储
基于 SQLAlchemy 异步实现，避免阻塞 FastAPI 事件循环
"""
from datetime import timezone
from typing import List, Optional

import tiktoken
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from loguru import logger
from sqlalchemy import desc, func, select

from app.database import AsyncSessionLocal
from app.models.db_models import DBMessage, DBSession, ErrorLog, MessageFeedback


def _to_epoch_ms(dt) -> int:
    """将 SQLite 存储的 UTC 时间（naive datetime）转为 epoch 毫秒"""
    if dt is None:
        return 0
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


class SessionStore:
    """数据库持久化的会话记忆存储（异步版本）"""

    # ---- 读取 ----

    async def get_history(
        self, session_id: str, max_tokens: Optional[int] = None
    ) -> List[BaseMessage]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(DBMessage)
                .where(DBMessage.session_id == session_id)
                .order_by(DBMessage.id)
            )
            rows = result.scalars().all()
            messages: List[BaseMessage] = []
            for row in rows:
                if row.role == "human":
                    messages.append(HumanMessage(content=row.content))
                else:
                    messages.append(AIMessage(content=row.content))
            if max_tokens is not None:
                messages = self._truncate_by_tokens(messages, max_tokens)
            return messages

    @staticmethod
    def _truncate_by_tokens(
        messages: List[BaseMessage], max_tokens: int
    ) -> List[BaseMessage]:
        """从最旧消息开始截断，直到总 token 数不超过 max_tokens（至少保留最近一条）"""
        enc = tiktoken.get_encoding("cl100k_base")
        total = 0
        keep: set[int] = set()
        for i in range(len(messages) - 1, -1, -1):
            msg_tokens = len(enc.encode(messages[i].content)) + 4
            if total + msg_tokens > max_tokens and keep:
                break
            total += msg_tokens
            keep.add(i)
        return [m for i, m in enumerate(messages) if i in keep]

    async def list_sessions(self, client_id: Optional[str] = None) -> List[dict]:
        async with AsyncSessionLocal() as db:
            stmt = select(DBSession)
            if client_id:
                stmt = stmt.where(DBSession.client_id == client_id)
            stmt = stmt.order_by(desc(DBSession.created_at))
            result = await db.execute(stmt)
            sessions = result.scalars().all()

            items = []
            for s in sessions:
                count_result = await db.execute(
                    select(func.count()).where(DBMessage.session_id == s.session_id)
                )
                count = count_result.scalar() or 0
                items.append({
                    "session_id": s.session_id,
                    "title": s.title or "新对话",
                    "message_count": count,
                    "created_at": _to_epoch_ms(s.created_at),
                })
            return items

    async def get_raw_messages(self, session_id: str) -> list:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(DBMessage)
                .where(DBMessage.session_id == session_id)
                .order_by(DBMessage.id)
            )
            rows = result.scalars().all()
            return [
                {"type": "human" if r.role == "human" else "ai", "content": r.content}
                for r in rows
            ]

    # ---- 写入 ----

    async def _ensure_session(self, db, session_id: str, client_id: str = "anonymous") -> None:
        result = await db.execute(
            select(DBSession).where(DBSession.session_id == session_id)
        )
        if not result.scalar_one_or_none():
            db.add(DBSession(session_id=session_id, client_id=client_id))
            await db.flush()

    async def add_messages(
        self, session_id: str, messages: List[BaseMessage], client_id: str = "anonymous"
    ) -> None:
        async with AsyncSessionLocal() as db:
            await self._ensure_session(db, session_id, client_id)
            for msg in messages:
                role = "human" if isinstance(msg, HumanMessage) else "ai"
                db.add(DBMessage(session_id=session_id, role=role, content=msg.content))

            result = await db.execute(
                select(DBSession).where(DBSession.session_id == session_id)
            )
            session = result.scalar_one_or_none()
            if session and (not session.title or session.title == "新对话"):
                for msg in messages:
                    if isinstance(msg, HumanMessage) and msg.content.strip():
                        title = msg.content.strip()
                        session.title = title[:30] + "…" if len(title) > 30 else title
                        break

            await db.commit()
            logger.debug(f"会话 {session_id[:8]} 已保存 {len(messages)} 条消息")

    async def update_title(self, session_id: str, title: str) -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(DBSession).where(DBSession.session_id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                session.title = title[:100]
                await db.commit()

    async def delete_session(self, session_id: str, client_id: Optional[str] = None) -> bool:
        async with AsyncSessionLocal() as db:
            stmt = select(DBSession).where(DBSession.session_id == session_id)
            if client_id:
                stmt = stmt.where(DBSession.client_id == client_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            if not session:
                return False
            await db.delete(session)
            await db.commit()
            return True

    async def clear(self, session_id: str) -> None:
        await self.delete_session(session_id)

    # ---- 反馈 ----

    async def add_feedback(
        self,
        session_id: str,
        question: str,
        answer: str,
        feedback: str,
        comment: Optional[str] = None,
        source: Optional[str] = None,
    ) -> int:
        async with AsyncSessionLocal() as db:
            record = MessageFeedback(
                session_id=session_id,
                question=question,
                answer=answer,
                feedback=feedback,
                comment=comment,
                source=source,
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return record.id

    async def list_feedback(self, session_id: Optional[str] = None) -> list[dict]:
        async with AsyncSessionLocal() as db:
            stmt = select(MessageFeedback).order_by(desc(MessageFeedback.created_at))
            if session_id:
                stmt = stmt.where(MessageFeedback.session_id == session_id)
            result = await db.execute(stmt)
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "question": r.question,
                    "answer": r.answer,
                    "feedback": r.feedback,
                    "comment": r.comment,
                    "source": r.source,
                    "created_at": _to_epoch_ms(r.created_at),
                }
                for r in result.scalars().all()
            ]

    # ---- 错误日志 ----

    async def add_error_log(
        self,
        session_id: str,
        client_id: str,
        question: str,
        error_message: str,
        source: Optional[str] = None,
    ) -> int:
        async with AsyncSessionLocal() as db:
            record = ErrorLog(
                session_id=session_id,
                client_id=client_id,
                question=question,
                error_message=error_message,
                source=source,
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return record.id

    async def list_error_logs(self, session_id: Optional[str] = None) -> list[dict]:
        async with AsyncSessionLocal() as db:
            stmt = select(ErrorLog).order_by(desc(ErrorLog.created_at))
            if session_id:
                stmt = stmt.where(ErrorLog.session_id == session_id)
            result = await db.execute(stmt)
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "client_id": r.client_id,
                    "question": r.question,
                    "error_message": r.error_message,
                    "source": r.source,
                    "created_at": _to_epoch_ms(r.created_at),
                }
                for r in result.scalars().all()
            ]


session_store = SessionStore()
