"""应用配置（所有可调参数集中于此）。

说明：
- 标注【仿真参数】的均为业务尚未最终确认的策略值，当前使用仿真默认值，
  可直接修改此处默认值，或通过环境变量 / .env 文件覆盖（见 .env.example）。
- 敏感项（SECRET_KEY、数据库、Redis 等）生产环境务必通过环境变量注入，
  不要提交真实凭证到仓库。
"""
from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 统一 TANHUI_ 前缀，避免与宿主环境变量（如系统 DATABASE_URL）冲突
    model_config = SettingsConfigDict(
        env_prefix="TANHUI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ==================== 基础 ====================
    APP_NAME: str = "碳惠陇原统一后端"
    APP_VERSION: str = "0.1.0"
    ENV: str = "dev"  # dev / test / sandbox / prod
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # JWT 签名密钥【仿真值】生产必须更换并仅从环境变量注入
    SECRET_KEY: str = "dev-only-secret-key-change-me-0001"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # 数据库连接【仿真环境使用 SQLite】
    # 生产示例：postgresql+psycopg://tanhui:密码@db:5432/tanhui
    DATABASE_URL: str = "sqlite:///./tanhui_dev.db"

    # Redis 连接；留空则使用进程内存后备（仅适用于开发/测试/单实例）
    REDIS_URL: str = ""

    # CORS 白名单【仿真值】正式域名确定后修改
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:5175"
    )

    # 全局限流：每 IP 每分钟请求上限【仿真参数】
    RATE_LIMIT_PER_MINUTE: int = 300

    # ==================== 支付（SANDBOX 仿真）====================
    # 【重要】当前为 Mock 沙箱适配器，未接入任何真实支付渠道。
    # 接入真实渠道时：在 app/modules/payments/providers/ 实现新 Provider，
    # 并修改 PAYMENT_PROVIDER 即可，业务层无需改动。
    PAYMENT_PROVIDER: str = "mock_sandbox"
    MOCK_PAYMENT_SECRET: str = "dev-mock-payment-secret"  # 【仿真值】回调签名密钥
    MOCK_PAYMENT_MERCHANT_NO: str = "MOCK8880001"  # 【仿真值】商户号
    ORDER_PAY_EXPIRE_MINUTES: int = 30  # 订单支付有效期(分钟)，超时释放库存

    # ==================== 运费规则【仿真参数：业务未定】====================
    SHIPPING_FLAT_FEE: str = "8.00"  # 单店铺基础运费(元)
    SHIPPING_FREE_THRESHOLD: str = "99.00"  # 单店铺包邮门槛(元)

    # ==================== 佣金与结算【仿真参数：业务未定】====================
    COMMISSION_RATE: str = "0.05"  # 平台佣金比例（按店铺子单实付金额）
    SETTLEMENT_PERIOD_DAYS: int = 15  # 结算周期(天)

    # ==================== 绿豆积分规则【仿真参数：业务未定】====================
    POINTS_EARN_ENABLED: bool = True  # 订单完成后是否发放绿豆
    POINTS_EARN_RATE: str = "1"  # 每消费 1 元发放绿豆数（向下取整）
    POINTS_DEDUCTION_ENABLED: bool = True  # 下单是否可用绿豆抵扣
    POINTS_DEDUCT_RATE: str = "100"  # 每多少绿豆抵扣 1 元
    POINTS_DEDUCT_MAX_PERCENT: str = "0.50"  # 绿豆最多抵扣应付金额的比例
    POINTS_REFUND_REVERSE_ENABLED: bool = True  # 退款时是否冲正已发放绿豆
    POINTS_DONATION_RATE: str = "3"  # 每 1 元助农资助发放绿色积分数

    # ==================== 管理员 MFA【仿真模式】====================
    MFA_REQUIRED_FOR_ADMIN_LOGIN: bool = False  # 生产建议改为 true
    MFA_STRICT_HIGH_RISK: bool = False  # 高风险管理操作强制二次验证
    MOCK_MFA_CODE: str = "123456"  # 【仿真值】未绑定真实 TOTP 时接受的固定码；置空禁用

    # ==================== 分页 ====================
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ==================== 文件上传【仿真：本地存储】====================
    # 生产环境切换 S3 兼容对象存储（见 app/modules/catalog/storage.py 适配层）
    UPLOAD_DIR: str = "./uploads"
    UPLOAD_MAX_SIZE_MB: int = 5

    # ==================== Celery 异步任务 ====================
    # 开发环境可留空：任务将以同步方式在请求内执行（见 app/worker/dispatch.py）
    CELERY_BROKER_URL: str = ""

    # ---------------- 派生属性 ----------------
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def decimal(self, field: str) -> Decimal:
        """按名称读取 Decimal 类型配置（仿真参数多以字符串声明便于修改）。"""
        return Decimal(str(getattr(self, field)))


from functools import lru_cache  # noqa: E402


@lru_cache
def get_settings() -> Settings:
    """读取配置（进程级缓存；测试中可用 get_settings.cache_clear() 重置）。"""
    return Settings()


settings = get_settings()
