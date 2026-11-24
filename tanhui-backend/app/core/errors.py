"""统一错误码与异常处理。

规范：
- 所有错误响应统一为 ApiResponse 结构：{code, message, data, request_id}
- code 为稳定字符串错误码，前端据此分支处理；message 为中文可读提示
"""
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


@dataclass(frozen=True)
class ErrorDef:
    code: str
    http_status: int
    message: str


ERRORS: dict[str, ErrorDef] = {
    # ---------- 通用 ----------
    "VALIDATION_ERROR": ErrorDef("VALIDATION_ERROR", 422, "参数校验失败"),
    "UNAUTHENTICATED": ErrorDef("UNAUTHENTICATED", 401, "未登录或凭证无效"),
    "TOKEN_EXPIRED": ErrorDef("TOKEN_EXPIRED", 401, "凭证已过期，请刷新"),
    "FORBIDDEN": ErrorDef("FORBIDDEN", 403, "无权限执行该操作"),
    "NOT_FOUND": ErrorDef("NOT_FOUND", 404, "资源不存在"),
    "METHOD_NOT_ALLOWED": ErrorDef("METHOD_NOT_ALLOWED", 405, "HTTP 方法不允许"),
    "CONFLICT": ErrorDef("CONFLICT", 409, "资源状态冲突"),
    "RATE_LIMITED": ErrorDef("RATE_LIMITED", 429, "请求过于频繁，请稍后重试"),
    "INTERNAL_ERROR": ErrorDef("INTERNAL_ERROR", 500, "服务器内部错误"),
    # ---------- 认证与账号 ----------
    "BAD_CREDENTIALS": ErrorDef("BAD_CREDENTIALS", 401, "账号或密码错误"),
    "ACCOUNT_DISABLED": ErrorDef("ACCOUNT_DISABLED", 403, "账号已被禁用"),
    "EMAIL_TAKEN": ErrorDef("EMAIL_TAKEN", 409, "邮箱已被注册"),
    "MFA_REQUIRED": ErrorDef("MFA_REQUIRED", 401, "需要二次验证码"),
    "MFA_INVALID": ErrorDef("MFA_INVALID", 401, "二次验证码错误"),
    "REFRESH_TOKEN_INVALID": ErrorDef("REFRESH_TOKEN_INVALID", 401, "刷新凭证无效"),
    # ---------- 商品与库存 ----------
    "INSUFFICIENT_STOCK": ErrorDef("INSUFFICIENT_STOCK", 409, "库存不足"),
    "PRODUCT_NOT_PURCHASABLE": ErrorDef("PRODUCT_NOT_PURCHASABLE", 409, "商品当前不可购买"),
    "FILE_TYPE_INVALID": ErrorDef("FILE_TYPE_INVALID", 422, "文件类型不允许"),
    "FILE_TOO_LARGE": ErrorDef("FILE_TOO_LARGE", 422, "文件大小超限"),
    "FILE_CONTENT_INVALID": ErrorDef("FILE_CONTENT_INVALID", 422, "文件内容校验失败"),
    # ---------- 订单与支付 ----------
    "PRICE_CHANGED": ErrorDef("PRICE_CHANGED", 409, "商品价格已变化，请重新确认"),
    "ORDER_STATE_INVALID": ErrorDef("ORDER_STATE_INVALID", 409, "订单当前状态不允许该操作"),
    "CART_ITEM_INVALID": ErrorDef("CART_ITEM_INVALID", 422, "购物车条目无效"),
    "IDEMPOTENCY_CONFLICT": ErrorDef(
        "IDEMPOTENCY_CONFLICT", 409, "幂等键已被使用且请求内容不同"
    ),
    "PAYMENT_SIGNATURE_INVALID": ErrorDef("PAYMENT_SIGNATURE_INVALID", 400, "支付回调签名无效"),
    "PAYMENT_AMOUNT_MISMATCH": ErrorDef("PAYMENT_AMOUNT_MISMATCH", 400, "支付金额与订单不符"),
    "PAYMENT_MERCHANT_MISMATCH": ErrorDef("PAYMENT_MERCHANT_MISMATCH", 400, "回调商户号不符"),
    "REFUND_NOT_ALLOWED": ErrorDef("REFUND_NOT_ALLOWED", 409, "当前订单不允许申请退款"),
    "REFUND_EXCEED_LIMIT": ErrorDef("REFUND_EXCEED_LIMIT", 409, "退款金额超出可退限额"),
    # ---------- 积分 ----------
    "POINTS_INSUFFICIENT": ErrorDef("POINTS_INSUFFICIENT", 409, "绿色积分余额不足"),
    "POINTS_RULE_INVALID": ErrorDef("POINTS_RULE_INVALID", 409, "积分规则配置无效"),
    # ---------- 商家与店铺 ----------
    "STORE_REQUIRED": ErrorDef("STORE_REQUIRED", 400, "请指定操作的店铺(store_id)"),
    "MERCHANT_STATE_INVALID": ErrorDef("MERCHANT_STATE_INVALID", 409, "商家状态不允许该操作"),
    # ---------- CMS ----------
    "CMS_COMPONENT_UNKNOWN": ErrorDef("CMS_COMPONENT_UNKNOWN", 422, "未知的页面组件类型"),
    "CMS_PAGE_NOT_PUBLISHED": ErrorDef("CMS_PAGE_NOT_PUBLISHED", 404, "页面未发布"),
    "CMS_STATE_INVALID": ErrorDef("CMS_STATE_INVALID", 409, "页面状态不允许该操作"),
}


class AppError(Exception):
    """业务异常：service 层抛出，由统一处理器包装为标准错误响应。"""

    def __init__(self, code: str, message: str | None = None, *, data=None):
        self.defn = ERRORS.get(code, ERRORS["INTERNAL_ERROR"])
        self.code = self.defn.code
        self.http_status = self.defn.http_status
        self.message = message or self.defn.message
        self.data = data
        super().__init__(self.message)


# 未显式映射的 HTTP 状态码回退错误码
_STATUS_FALLBACK = {
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
}


def error_body(code: str, message: str, data=None) -> dict:
    """构造统一错误响应体（供异常处理器与中间件复用）。"""
    from app.core.logging import get_request_id

    return {"code": code, "message": message, "data": data, "request_id": get_request_id()}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.http_status,
            content=error_body(exc.code, exc.message, exc.data),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        errors = [
            {
                "field": ".".join(str(x) for x in e["loc"][1:]) or str(e["loc"][0]),
                "message": e["msg"],
            }
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_body("VALIDATION_ERROR", "参数校验失败", {"errors": errors}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException):
        if exc.status_code >= 500:
            code = "INTERNAL_ERROR"
        else:
            code = _STATUS_FALLBACK.get(exc.status_code, "CONFLICT")
        return JSONResponse(
            status_code=exc.status_code, content=error_body(code, str(exc.detail))
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        import logging

        logging.getLogger("error").exception("unhandled exception")
        return JSONResponse(
            status_code=500, content=error_body("INTERNAL_ERROR", "服务器内部错误")
        )
