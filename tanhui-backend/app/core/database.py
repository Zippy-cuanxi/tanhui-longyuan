"""数据库引擎与会话管理。

事务约定：
- 请求级会话由 get_db 依赖提供；service 层完成业务写入后可显式 commit；
- get_db 在请求正常结束时做一次兜底 commit，异常时 rollback；
- 高并发库存扣减使用"条件 UPDATE"（见 inventory/service.py），不依赖长事务。
"""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite 需要允许跨线程使用连接（FastAPI 线程池）
    _connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=_connect_args,
    # 生产 PostgreSQL 建议配置：pool_size=10, max_overflow=20
)

if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def _sqlite_pragma(dbapi_conn, _):  # SQLite 默认不启用外键约束
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        # 【性能】开发环境（尤其网络盘）关闭同步落盘提速。
        # 注意：WAL 模式在网络文件系统上不可靠（SQLite 已知限制），
        # 故保留默认 DELETE 日志模式，仅关 fsync + 加锁等待。
        # 生产使用 PostgreSQL，不受此影响。
        cur.execute("PRAGMA synchronous=OFF")
        cur.execute("PRAGMA busy_timeout=15000")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
