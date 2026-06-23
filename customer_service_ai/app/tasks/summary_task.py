"""
对话摘要生成任务
由 Celery Worker 执行，不阻塞 ASGI 事件循环
"""
from celery.utils.log import get_task_logger
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import scoped_session, sessionmaker

from app.celery_app import celery_app
from app.config import settings

logger = get_task_logger(__name__)

_sync_engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SyncSession = scoped_session(sessionmaker(bind=_sync_engine))

SUMMARY_PROMPT = "请用一句话概括以下对话的核心主题和关键结论（30字以内，不要编造）：\n\n{dialog}"


def _get_messages(session_id: str) -> list:
    from app.models.db_models import DBMessage
    db = SyncSession()
    try:
        result = db.execute(
            select(DBMessage).where(DBMessage.session_id == session_id)
            .order_by(DBMessage.created_at)
        )
        return result.scalars().all()
    finally:
        db.close()


def _update_summary(session_id: str, summary: str) -> None:
    from app.models.db_models import DBSession
    db = SyncSession()
    try:
        result = db.execute(
            select(DBSession).where(DBSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.summary = summary[:500]
            db.commit()
    finally:
        db.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
    name="generate_summary",
)
def generate_summary(self, session_id: str) -> None:
    try:
        messages = _get_messages(session_id)
        if len(messages) < 2:
            return

        dialog = "\n".join(
            f"{'用户' if m.role == 'human' else 'AI'}: {m.content[:200]}"
            for m in messages[-6:]
        )

        llm = ChatOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            temperature=0.3,
            max_retries=2,
            request_timeout=30,
        )
        prompt = SystemMessage(content=SUMMARY_PROMPT.format(dialog=dialog))
        result = llm.invoke([prompt])
        summary = result.content.strip() if hasattr(result, "content") else str(result).strip()

        if summary:
            _update_summary(session_id, summary)
            logger.info(f"会话 {session_id[:8]} 摘要已更新: {summary[:40]}")
    except Exception as exc:
        logger.warning(f"会话 {session_id[:8]} 摘要生成失败: {exc}")
        raise self.retry(exc=exc)
