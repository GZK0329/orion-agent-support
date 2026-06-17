"""
会话记忆存储
基于 SQLAlchemy 数据库实现，支持并发和安全持久化
"""
from typing import List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.db_models import DBMessage, DBSession


def _now() -> int:
    import time
    return int(time.time() * 1000)


class SessionStore:
    """数据库持久化的会话记忆存储"""

    # ---- 读取 ----

    def get_history(self, session_id: str) -> List[BaseMessage]:
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
            return result
        finally:
            db.close()

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
                    "created_at": int(s.created_at.timestamp() * 1000) if s.created_at else 0,
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


session_store = SessionStore()
