"""
数据库连接管理
使用 SQLAlchemy，开发时 SQLite 零配置，部署后可换 PostgreSQL
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = scoped_session(sessionmaker(bind=engine))


def init_db() -> None:
    """启动时初始化表结构 + 兼容迁移"""
    from app.models.db_models import Base
    Base.metadata.create_all(bind=engine)

    # 兼容迁移：为已有表添加 client_id 列（SQLite safe）
    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("sessions")}
    if "client_id" not in cols:
        with engine.connect() as conn:
            conn.exec_driver_sql(
                "ALTER TABLE sessions ADD COLUMN client_id VARCHAR(36) NOT NULL DEFAULT 'anonymous'"
            )
            conn.commit()
