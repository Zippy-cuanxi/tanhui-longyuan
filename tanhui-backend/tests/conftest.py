"""测试基础设施：函数级独立数据库 + 通用业务脚手架。

说明：
- 每个测试用例使用全新 schema（drop_all/create_all），互不干扰；
- RBAC 角色种子随库重建自动播种；
- 业务脚手架（商家/店铺/商品/库存）直接走 service 层，速度更快。
"""
import os
import threading
import uuid
from decimal import Decimal

# 必须在导入 app 之前设置测试环境
_TEST_DB = os.path.abspath("test_tanhui.db")
os.environ["TANHUI_DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["TANHUI_RATE_LIMIT_PER_MINUTE"] = "100000"  # 测试关闭限流影响
os.environ["TANHUI_CELERY_BROKER_URL"] = ""
os.environ["TANHUI_DEBUG"] = "false"  # 降低日志级别，减少测试输出噪声

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.base import Base  # noqa: E402
from app.core.database import SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.catalog import service as catalog_service  # noqa: E402
from app.modules.catalog.schemas import ProductCreateIn, SkuIn  # noqa: E402
from app.modules.inventory import service as inventory_service  # noqa: E402
from app.modules.merchants import service as merchant_service  # noqa: E402
from app.modules.merchants.schemas import MerchantApplyIn  # noqa: E402
from app.modules.points import service as points_service  # noqa: E402
from app.modules.rbac import service as rbac_service  # noqa: E402
from app.modules.users import service as users_service  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    """会话级建表（网络盘上重复 DDL 极慢，故只建一次）。"""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def fresh_db(_schema):
    """每用例清空全部表数据（按拓扑逆序删除）并重播种角色/积分规则。"""
    db = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
        rbac_service.seed_role_data(db)
        points_service.ensure_rules_seeded(db)
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------- 认证脚手架 ----------------
def register_user(email: str, password: str = "Passw0rd!123") -> uuid.UUID:
    db = SessionLocal()
    try:
        user = users_service.register_user(db, email, password, None)
        db.commit()
        return user.id
    finally:
        db.close()


def login_headers(client: TestClient, email: str, password: str = "Passw0rd!123") -> dict:
    resp = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client: TestClient, email: str) -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Passw0rd!123", "nickname": email.split("@")[0]},
    )
    assert resp.status_code == 200, resp.text
    return login_headers(client, email)


def make_admin(email: str) -> uuid.UUID:
    """幂等创建超级管理员（已存在则直接返回，确保脚手架可重复调用）。"""
    db = SessionLocal()
    try:
        from sqlalchemy import select as _select

        from app.modules.users.models import User

        existing = db.execute(
            _select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing is not None:
            return existing.id
    finally:
        db.close()
    user_id = register_user(email)
    db = SessionLocal()
    try:
        rbac_service.assign_role(db, user_id, "super_admin", None)
        db.commit()
    finally:
        db.close()
    return user_id


def admin_headers(client: TestClient, email: str) -> dict:
    make_admin(email)
    return login_headers(client, email)


# ---------------- 商家/店铺/商品脚手架 ----------------
def create_store_with_owner(owner_email: str, store_name: str) -> tuple[uuid.UUID, uuid.UUID]:
    """入驻→审核通过→默认店铺；返回 (store_id, owner_user_id)。"""
    owner_id = register_user(owner_email)
    db = SessionLocal()
    try:
        merchant = merchant_service.apply(
            db,
            owner_id,
            MerchantApplyIn(
                company_name=f"{store_name}公司",
                license_no=f"LIC{uuid.uuid4().hex[:8]}",
                legal_person="张三",
                contact_phone="13800000000",
                store_name=store_name,
            ),
        )
        merchant_service.review(db, merchant.id, "approve", None, owner_id)
        db.commit()
        from app.modules.stores.models import Store

        store = (
            db.query(Store).filter(Store.merchant_id == merchant.id).one()
        )
        return store.id, owner_id
    finally:
        db.close()


def create_category(name: str) -> uuid.UUID:
    db = SessionLocal()
    try:
        from app.modules.catalog.models import Category

        c = Category(name=name)
        db.add(c)
        db.commit()
        return c.id
    finally:
        db.close()


def create_approved_product(
    store_id: uuid.UUID,
    title: str,
    price: str = "19.90",
    stock: int = 100,
    category_id: uuid.UUID | None = None,
    admin_user_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """创建商品（草稿）→ 提交 → 管理员审核通过 → 上架；返回 SKU ID。

    注意：admin 与 category 均先于商品写会话准备，避免
    "外层事务持锁 + 内层新连接写库" 的 SQLite 锁死。
    """
    admin_id = admin_user_id or make_admin("auditor@example.com")
    if category_id is None:
        category_id = create_category("默认分类")
    db = SessionLocal()
    try:
        payload = ProductCreateIn(
            title=title,
            subtitle=f"{title}·甘肃直发",
            description="仿真商品描述【simulation】",
            category_id=category_id,
            skus=[SkuIn(spec="500g*2袋", price=Decimal(price), initial_stock=stock)],
        )
        product = catalog_service.create_product(db, store_id, payload)
        catalog_service.submit_for_review(db, store_id, product.id)
        catalog_service.audit_product(db, product.id, "approve", None, admin_id)
        catalog_service.toggle_listing(db, store_id, product.id, True)
        db.commit()
        from app.modules.catalog.models import ProductSku

        sku = (
            db.query(ProductSku).filter(ProductSku.product_id == product.id).one()
        )
        return sku.id
    finally:
        db.close()


# ---------------- 并发工具 ----------------
def run_threads(target, count: int):
    threads = [threading.Thread(target=target) for _ in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
