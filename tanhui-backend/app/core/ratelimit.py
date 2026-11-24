"""简单固定窗口限流中间件：优先 Redis，未配置时退化为进程内存（开发/测试用）。

【仿真说明】生产多实例部署必须配置 REDIS_URL，否则各实例独立计数限流失效。
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.errors import error_body


class _MemoryStore:
    def __init__(self):
        self._hits: dict[str, tuple[float, int]] = {}

    def hit(self, key: str, window: float) -> bool:
        now = time.monotonic()
        start, count = self._hits.get(key, (now, 0))
        if now - start >= window:
            start, count = now, 0
        count += 1
        self._hits[key] = (start, count)
        return count <= settings.RATE_LIMIT_PER_MINUTE


class _RedisStore:
    def __init__(self, client):
        self._client = client

    def hit(self, key: str, window: float) -> bool:
        redis_key = f"ratelimit:{key}"
        count = self._client.incr(redis_key)
        if count == 1:
            self._client.expire(redis_key, int(window))
        return count <= settings.RATE_LIMIT_PER_MINUTE


def build_store():
    """根据配置选择限流存储。"""
    if settings.REDIS_URL:
        import redis

        return _RedisStore(redis.Redis.from_url(settings.REDIS_URL))
    return _MemoryStore()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """按 IP 限流；健康检查与支付回调不限流。"""

    EXEMPT_PATHS = ("/healthz", "/readyz")

    def __init__(self, app):
        super().__init__(app)
        self._store = build_store()

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(self.EXEMPT_PATHS):
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        if not self._store.hit(ip, 60.0):
            return JSONResponse(
                status_code=429,
                content=error_body("RATE_LIMITED", "请求过于频繁，请稍后重试"),
            )
        return await call_next(request)
