"""全部模型集中注册（供 Alembic autogenerate 与测试使用）。

新增模块后在此追加 import，保证 Base.metadata 完整。
"""
# noqa: F401
from app.modules.admin.models import SystemSetting
from app.modules.aid.models import AidProject, AidRecord, Cooperative
from app.modules.audit.models import LoginLog, OperationLog, SecurityEvent
from app.modules.auth.models import AuthSession
from app.modules.cart.models import Cart, CartItem
from app.modules.catalog.models import (
    Category,
    Product,
    ProductAuditRecord,
    ProductImage,
    ProductSku,
)
from app.modules.finance.models import (
    MerchantSettlement,
    PlatformLedger,
    SettlementItem,
)
from app.modules.green.models import (
    CarbonAssessment,
    ProductGreenProfile,
    VerificationRecord,
)
from app.modules.inventory.models import Inventory, InventoryLog, InventoryReservation
from app.modules.logistics.models import Shipment, ShipmentTrack
from app.modules.merchants.models import Merchant, MerchantUser
from app.modules.notifications.models import Notification
from app.modules.orders.models import Order, OrderItem, OrderStatusLog, StoreOrder
from app.modules.payments.models import (
    PaymentCallback,
    PaymentOrder,
    PaymentTransaction,
    Refund,
)
from app.modules.points.models import (
    PointAccount,
    PointRule,
    PointRuleVersion,
    PointTransaction,
)
from app.modules.rbac.models import DataScope, Permission, Role, RolePermission, UserRole
from app.modules.stores.models import Store, StoreMember
from app.modules.users.models import User, UserAddress, UserProfile
from app.modules.cms.models import (
    CmsAnnouncement,
    CmsBanner,
    CmsPage,
    CmsPageVersion,
    CmsPublishRecord,
    CmsSection,
)

ALL_TABLES = sorted(
    t for t in __import__("app.core.base", fromlist=["Base"]).Base.metadata.tables
)
