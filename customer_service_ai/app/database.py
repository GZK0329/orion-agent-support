"""
数据库连接管理
使用 SQLAlchemy，开发时 SQLite 零配置，部署后可换 PostgreSQL
提供同步和异步两套引擎，异步引擎供 FastAPI 接口使用，避免阻塞事件循环
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from app.config import settings

IS_SQLITE = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    pool_pre_ping=True,
)

SessionLocal = scoped_session(sessionmaker(bind=engine))

_async_url = (
    settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if IS_SQLITE
    else settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
)

async_engine = create_async_engine(
    _async_url,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def init_db() -> None:
    """启动时初始化表结构 + 兼容迁移"""
    from app.models.db_models import Base
    Base.metadata.create_all(bind=engine)

    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("sessions")}

    if "client_id" not in cols:
        with engine.connect() as conn:
            conn.exec_driver_sql(
                "ALTER TABLE sessions ADD COLUMN client_id VARCHAR(36) NOT NULL DEFAULT 'anonymous'"
            )
            conn.commit()

    if "summary" not in cols:
        with engine.connect() as conn:
            conn.exec_driver_sql(
                "ALTER TABLE sessions ADD COLUMN summary TEXT DEFAULT ''"
            )
            conn.commit()
