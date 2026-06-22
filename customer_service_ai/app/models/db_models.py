"""
SQLAlchemy 数据库模型
会话表 + 消息表
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DBSession(Base):
    """会话表"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True)
    client_id = Column(String(36), nullable=False, index=True, server_default="anonymous")
    title = Column(String(100), default="新对话")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DBMessage(Base):
    """消息表"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36),
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)  # 'human' | 'ai'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class MessageFeedback(Base):
    """用户反馈表 — 对 AI 回答的 👍/👎"""
    __tablename__ = "message_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    feedback = Column(String(10), nullable=False)  # 'like' | 'dislike'
    comment = Column(Text, nullable=True)
    source = Column(String(20), nullable=True)  # 来源标识
    created_at = Column(DateTime, server_default=func.now())


class ErrorLog(Base):
    """错误日志表 — 记录模型调用失败"""
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, index=True)
    client_id = Column(String(36), nullable=False, default="anonymous")
    question = Column(Text, nullable=False)
    error_message = Column(Text, nullable=False)
    source = Column(String(20), nullable=True)  # 'chat_stream' | 'chat_sync'
    created_at = Column(DateTime, server_default=func.now())
