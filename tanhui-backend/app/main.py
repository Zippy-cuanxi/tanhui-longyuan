"""应用入口。

启动（开发）：
    uvicorn app.main:app --reload --port 8000
启动（生产）：见 Dockerfile / docker-compose.yml
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.errors import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.core.ratelimit import RateLimitMiddleware
from app.modules import register_routers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 开发环境挂载本地上传目录静态服务【仿真存储】；生产使用对象存储 CDN
    # 旧开发库自愈：补齐消费者端镜像表并把存量已审核商品对齐到消费者库，
    # 避免上线同步机制后原有商品在消费者端"消失"。
    from app.core.database import SessionLocal
    from app.modules.catalog import sync_service

    try:
        # 生产环境以 alembic 迁移为准；SQLite 开发库做 checkfirst 自愈
        if engine.dialect.name == "sqlite":
            sync_service.ensure_sync_tables(engine)
        db = SessionLocal()
        try:
            sync_service.backfill_consumer_catalog(db)
            db.commit()
        finally:
            db.close()
    except Exception:  # noqa: BLE001 - 启动自愈失败不阻断服务
        import logging

        logging.getLogger("startup").exception("consumer catalog backfill skipped")
    yield
    engine.dispose()


def create_app() -> FastAPI:
    configure_logging(settings.DEBUG)
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "碳惠陇原统一后端 API（/api/v1）。\n\n"
            "**说明**：所有业务策略参数（佣金/运费/积分/支付等）当前均为**仿真配置**，"
            "见 `.env.example` 与 `docs/pending-decisions.md`；支付渠道为 SANDBOX Mock，"
            "未接入真实渠道。"
        ),
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    # 中间件（后添加者先执行）：CORS 最外层 → request_id → 限流 → 应用
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "ETag"],
    )
    register_exception_handlers(app)
    register_routers(app)

    # 本地上传目录静态服务【仿真存储】
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

    @app.get("/healthz", tags=["meta"], summary="存活探针")
    def healthz():
        return {"status": "ok"}

    @app.get("/readyz", tags=["meta"], summary="就绪探针（检查数据库）")
    def readyz():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}

    return app


app = create_app()
