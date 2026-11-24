"""支付 Provider 抽象 + Mock 沙箱实现。

【SANDBOX/仿真声明】MockProvider 未连接任何真实支付渠道：
- mock_pay 工具接口模拟"用户完成支付"，生成 HMAC-SHA256 签名回调；
- 回调处理逻辑（验签/金额核对/幂等）与真实渠道完全一致，可直接复用。
接入真实渠道时实现 PaymentProvider 接口即可，业务代码零改动。
"""
import hashlib
import hmac
import secrets
import uuid
from decimal import Decimal

from app.core.config import settings


class PaymentProvider:
    """支付渠道接口（真实渠道按此实现）。"""

    name: str = "base"

    def create_payment_url(self, pay_no: str, amount: Decimal, currency: str) -> str:
        raise NotImplementedError

    def verify_callback(self, payload: dict, signature: str) -> bool:
        raise NotImplementedError


class MockSandboxProvider(PaymentProvider):
    """Mock 沙箱渠道【仿真】。"""

    name = "mock_sandbox"

    def create_payment_url(self, pay_no: str, amount: Decimal, currency: str) -> str:
        # 仿真收银台地址（前端可据此展示"去支付(MOCK)"按钮）
        return f"mock://sandbox-pay/{pay_no}?amount={amount}&currency={currency}"

    @staticmethod
    def canonical_payload(payload: dict) -> str:
        """签名串：按 key 排序的 k=v& 拼接（与真实渠道做法保持一致）。"""
        items = sorted((k, str(v)) for k, v in payload.items() if v is not None)
        return "&".join(f"{k}={v}" for k, v in items)

    def sign(self, payload: dict) -> str:
        secret = settings.MOCK_PAYMENT_SECRET  # 【仿真值】
        return hmac.new(
            secret.encode("utf-8"),
            self.canonical_payload(payload).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def verify_callback(self, payload: dict, signature: str) -> bool:
        return hmac.compare_digest(self.sign(payload), signature or "")

    @staticmethod
    def generate_trade_no() -> str:
        return f"MOCK{secrets.token_hex(8).upper()}"


def get_provider() -> PaymentProvider:
    """按配置返回支付渠道实现【仿真默认 mock_sandbox】。"""
    if settings.PAYMENT_PROVIDER == "mock_sandbox":
        return MockSandboxProvider()
    raise ValueError(f"未知支付渠道: {settings.PAYMENT_PROVIDER}")
