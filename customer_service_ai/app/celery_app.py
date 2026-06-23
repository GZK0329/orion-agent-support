"""
Celery 异步任务队列
用于 _generate_summary、ingest 等后台任务
Redis 不可用时静默降级，不影响主流程
"""
import logging

from app.config import settings

if settings.redis_url:
    from celery import Celery

    celery_app = Celery(
        "agent_support",
        broker=settings.redis_url,
        backend=settings.redis_url,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Shanghai",
        enable_utc=False,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_soft_time_limit=120,
        task_time_limit=180,
        task_reject_on_worker_lost=True,
        task_acks_on_failure_or_timeout=True,
    )
else:
    celery_app = None
    logging.getLogger(__name__).warning("REDIS_URL 未配置，Celery 任务队列已禁用")
