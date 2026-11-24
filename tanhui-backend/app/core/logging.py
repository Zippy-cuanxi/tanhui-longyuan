"""结构化 JSON 日志 + request_id 上下文中间件。"""
import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# 当前请求的 request_id 上下文（供日志与统一响应体使用）
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return request_id_ctx.get()


class JsonFormatter(logging.Formatter):
    """JSON 行式日志，便于采集与检索。"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": get_request_id(),
        }
        for key in ("path", "method", "status", "duration_ms", "client_ip"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(debug: bool = False) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    # uvicorn 自带 handler 关闭，统一走 root 输出
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = []


class RequestIdMiddleware(BaseHTTPMiddleware):
    """为每个请求生成/透传 request_id，注入响应头，并输出访问日志。"""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_ctx.set(rid)
        request.state.request_id = rid
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            duration = round((time.perf_counter() - start) * 1000, 2)
            if request.url.path not in ("/healthz", "/readyz"):
                logging.getLogger("access").info(
                    "http_request",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "status": status,
                        "duration_ms": duration,
                        "client_ip": request.client.host if request.client else "",
                    },
                )
            request_id_ctx.reset(token)
