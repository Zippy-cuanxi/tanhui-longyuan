"""定时任务：释放超时库存预占、关闭超时订单、自动确认收货（占位）。"""
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.modules.inventory import service as inventory_service
from app.modules.orders import service as order_service


def release_expired_reservations() -> int:
    """释放支付超时的库存预占（幂等，可重复执行）。"""
    db = SessionLocal()
    try:
        return inventory_service.release_expired(db)
    finally:
        db.close()


def close_expired_orders() -> int:
    """关闭支付超时订单（含库存释放与绿豆返还）。"""
    db = SessionLocal()
    try:
        return order_service.close_expired(db)
    finally:
        db.close()


if __name__ == "__main__":
    # 开发环境手动执行：python -m app.worker.tasks
    configure_logging()
    print("released reservations:", release_expired_reservations())
    print("closed orders:", close_expired_orders())


# 注册到 Celery（未配置 broker 时保持 None，任务仅可同步调用）
try:
    from app.worker.celery_app import celery_app

    if celery_app is not None:
        release_expired_reservations = celery_app.task(name="app.worker.tasks.release_expired_reservations")(
            release_expired_reservations
        )
        close_expired_orders = celery_app.task(name="app.worker.tasks.close_expired_orders")(
            close_expired_orders
        )
except ImportError:  # pragma: no cover
    pass
