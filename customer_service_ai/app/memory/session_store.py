"""
会话记忆存储
基于 SQLAlchemy 数据库实现，支持并发和安全持久化
"""
from datetime import timezone
from typing import List, Optional

import tiktoken
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.db_models import DBMessage, DBSession, ErrorLog, MessageFeedback


def _now() -> int:
    import time
    return int(time.time() * 1000)


def _to_epoch_ms(dt) -> int:
    """将 SQLite 存储的 UTC 时间（naive datetime）转为 epoch 毫秒"""
    if dt is None:
        return 0
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


class SessionStore:
    """数据库持久化的会话记忆存储"""

    # ---- 读取 ----

    def get_history(
        self, session_id: str, max_tokens: Optional[int] = None
    ) -> List[BaseMessage]:
        db = SessionLocal()
        try:
            rows = (
                db.query(DBMessage)
                .filter(DBMessage.session_id == session_id)
                .order_by(DBMessage.id)
                .all()
            )
            result: List[BaseMessage] = []
            for row in rows:
                if row.role == "human":
                    result.append(HumanMessage(content=row.content))
                else:
                    result.append(AIMessage(content=row.content))
            if max_tokens is not None:
                result = self._truncate_by_tokens(result, max_tokens)
            return result
        finally:
            db.close()

    @staticmethod
    def _truncate_by_tokens(
        messages: List[BaseMessage], max_tokens: int
    ) -> List[BaseMessage]:
        """从最旧消息开始截断，直到总 token 数不超过 max_tokens（至少保留最近一条）"""
        enc = tiktoken.get_encoding("cl100k_base")
        total = 0
        # 从最新到最旧累加 token，标记需要保留的消息
        keep: set[int] = set()
        for i in range(len(messages) - 1, -1, -1):
            msg_tokens = len(enc.encode(messages[i].content)) + 4  # 4 tokens overhead
            if total + msg_tokens > max_tokens and keep:
                break
            total += msg_tokens
            keep.add(i)
        return [m for i, m in enumerate(messages) if i in keep]

    def list_sessions(self, client_id: Optional[str] = None) -> List[dict]:
        db = SessionLocal()
        try:
            q = db.query(DBSession)
            if client_id:
                q = q.filter(DBSession.client_id == client_id)
            rows = q.order_by(desc(DBSession.created_at)).all()
            result = []
            for s in rows:
                count = (
                    db.query(DBMessage)
                    .filter(DBMessage.session_id == s.session_id)
                    .count()
                )
                result.append({
                    "session_id": s.session_id,
                    "title": s.title or "新对话",
                    "message_count": count,
                    "created_at": _to_epoch_ms(s.created_at),
                })
            return result
        finally:
            db.close()

    def get_raw_messages(self, session_id: str) -> list:
        """获取消息列表（dict 格式），供历史 API 返回"""
        db = SessionLocal()
        try:
            rows = (
                db.query(DBMessage)
                .filter(DBMessage.session_id == session_id)
                .order_by(DBMessage.id)
                .all()
            )
            return [
                {"type": "human" if r.role == "human" else "ai", "content": r.content}
                for r in rows
            ]
        finally:
            db.close()

    # ---- 写入 ----

    def _ensure_session(self, db, session_id: str, client_id: str = "anonymous") -> None:
        """确保会话记录存在"""
        exists = db.query(DBSession).filter(DBSession.session_id == session_id).first()
        if not exists:
            db.add(DBSession(session_id=session_id, client_id=client_id))
            db.flush()

    def add_messages(self, session_id: str, messages: List[BaseMessage], client_id: str = "anonymous") -> None:
        db = SessionLocal()
        try:
            self._ensure_session(db, session_id, client_id)
            for msg in messages:
                role = "human" if isinstance(msg, HumanMessage) else "ai"
                db.add(DBMessage(session_id=session_id, role=role, content=msg.content))

            # 更新会话标题（用第一条用户消息）
            session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
            if session and (not session.title or session.title == "新对话"):
                for msg in messages:
                    if isinstance(msg, HumanMessage) and msg.content.strip():
                        title = msg.content.strip()
                        session.title = title[:30] + "…" if len(title) > 30 else title
                        break

            db.commit()
        finally:
            db.close()

    def update_title(self, session_id: str, title: str) -> None:
        db = SessionLocal()
        try:
            db.query(DBSession).filter(DBSession.session_id == session_id).update(
                {"title": title[:100]}
            )
            db.commit()
        finally:
            db.close()

    def delete_session(self, session_id: str, client_id: Optional[str] = None) -> bool:
        db = SessionLocal()
        try:
            q = db.query(DBSession).filter(DBSession.session_id == session_id)
            if client_id:
                q = q.filter(DBSession.client_id == client_id)
            session = q.first()
            if not session:
                return False
            db.delete(session)
            db.commit()
            return True
        finally:
            db.close()

    def clear(self, session_id: str) -> None:
        self.delete_session(session_id)

    # ---- 反馈 ----

    def add_feedback(
        self,
        session_id: str,
        question: str,
        answer: str,
        feedback: str,
        comment: Optional[str] = None,
        source: Optional[str] = None,
    ) -> int:
        db = SessionLocal()
        try:
            record = MessageFeedback(
                session_id=session_id,
                question=question,
                answer=answer,
                feedback=feedback,
                comment=comment,
                source=source,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record.id
        finally:
            db.close()

    def list_feedback(self, session_id: Optional[str] = None) -> list[dict]:
        db = SessionLocal()
        try:
            q = db.query(MessageFeedback).order_by(desc(MessageFeedback.created_at))
            if session_id:
                q = q.filter(MessageFeedback.session_id == session_id)
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
                for r in q.all()
            ]
        finally:
            db.close()

    # ---- 错误日志 ----

    def add_error_log(
        self,
        session_id: str,
        client_id: str,
        question: str,
        error_message: str,
        source: Optional[str] = None,
    ) -> int:
        db = SessionLocal()
        try:
            record = ErrorLog(
                session_id=session_id,
                client_id=client_id,
                question=question,
                error_message=error_message,
                source=source,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record.id
        finally:
            db.close()

    def list_error_logs(self, session_id: Optional[str] = None) -> list[dict]:
        db = SessionLocal()
        try:
            q = db.query(ErrorLog).order_by(desc(ErrorLog.created_at))
            if session_id:
                q = q.filter(ErrorLog.session_id == session_id)
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
                for r in q.all()
            ]
        finally:
            db.close()


session_store = SessionStore()
