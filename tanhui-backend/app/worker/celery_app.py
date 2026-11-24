"""Celery 异步任务【仿真：默认同步执行】。

说明：
- 未配置 CELERY_BROKER_URL 时（开发/测试），任务通过 dispatch_task 直接同步执行；
- 生产配置 broker（如 redis://redis:6379/1）后，同一份任务代码由 Celery worker 执行：
    celery -A app.worker.celery_app worker -B --loglevel=info
- -B 参数启用内建 beat（周期任务），也可独立部署 beat。
"""
from app.core.config import settings

celery_app = None
if settings.CELERY_BROKER_URL:
    from celery import Celery

    celery_app = Celery(
        "tanhui",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_BROKER_URL,
    )
    celery_app.conf.update(
        task_serializer="json",
        timezone="UTC",
        beat_schedule={
            "release-expired-reservations": {
                "task": "app.worker.tasks.release_expired_reservations",
                "schedule": 60.0,  # 每分钟
            },
            "close-expired-orders": {
                "task": "app.worker.tasks.close_expired_orders",
                "schedule": 120.0,  # 每两分钟
            },
        },
    )
