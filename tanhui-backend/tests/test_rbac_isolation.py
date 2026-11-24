"""RBAC 与商家数据隔离测试（IDOR 防护核心）。"""
import uuid

from tests.conftest import (
    admin_headers,
    create_approved_product,
    create_store_with_owner,
    login_headers,
    register_and_login,
)


def _merchant_headers(client, email, store_id=None):
    # 用户已由 create_store_with_owner 直接创建，这里仅登录
    return login_headers(client, email)


def test_consumer_cannot_access_admin_api(client):
    headers = register_and_login(client, "consumer@example.com")
    resp = client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_merchant_cannot_access_admin_api(client):
    store_id, owner_id = create_store_with_owner("m1@example.com", "陇原一号店")
    headers = _merchant_headers(client, "m1@example.com")
    resp = client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403


def test_store_isolation_idor(client):
    """商家 A 不能读/改商家 B 的商品、库存、订单（直接拿对方 ID 访问）。"""
    store_a, _ = create_store_with_owner("owner-a@example.com", "A 店")
    store_b, _ = create_store_with_owner("owner-b@example.com", "B 店")
    sku_b = create_approved_product(store_b, "B店静宁苹果")

    headers_a = login_headers(client, "owner-a@example.com")
    # A（仅有一个店铺）访问 B 的库存：sku 不属于 A 店铺 → 404/403
    resp = client.post(
        "/api/v1/merchant/inventory/adjust",
        json={"sku_id": str(sku_b), "delta": 999, "reason": "越权尝试"},
        headers=headers_a,
    )
    assert resp.status_code in (403, 404)

    # A 尝试列出 B 店订单（store_id=B）→ FORBIDDEN
    resp = client.get(
        "/api/v1/merchant/orders", params={"store_id": str(store_b)}, headers=headers_a
    )
    assert resp.status_code == 403


def test_multi_store_member_must_pick_store(client):
    """多店铺成员：不指定 store_id 报 STORE_REQUIRED；指定后按该店角色行权。"""
    store_a, owner_a = create_store_with_owner("multi@example.com", "多店主的A店")
    store_b, _ = create_store_with_owner("owner-b2@example.com", "B2 店")

    # 把多店主加入 B 店作 viewer（只读角色）
    from app.core.database import SessionLocal
    from app.modules.stores import service as store_service

    db = SessionLocal()
    try:
        store_service.add_employee(db, store_b, "multi@example.com", "viewer", owner_a)
        db.commit()
    finally:
        db.close()

    headers = login_headers(client, "multi@example.com")
    # 未指定店铺 → STORE_REQUIRED
    resp = client.get("/api/v1/merchant/products", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "STORE_REQUIRED"

    # 指定 B 店（viewer 只读）→ 可读商品
    resp = client.get(
        "/api/v1/merchant/products", params={"store_id": str(store_b)}, headers=headers
    )
    assert resp.status_code == 200

    # viewer 角色不能改库存（inventory:manage 缺失）
    resp = client.post(
        "/api/v1/merchant/inventory/adjust",
        params={"store_id": str(store_b)},
        json={"sku_id": str(uuid.uuid4()), "delta": 1, "reason": "越权尝试"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_admin_permission_granularity(client):
    """商品审核员（非超管）可以审核商品，但不能管理 RBAC。"""
    from app.core.database import SessionLocal
    from app.modules.rbac import service as rbac_service
    from tests.conftest import register_user, login_headers

    auditor_id = register_user("auditor2@example.com")
    db = SessionLocal()
    try:
        rbac_service.assign_role(db, auditor_id, "product_auditor", None)
        db.commit()
    finally:
        db.close()
    headers = login_headers(client, "auditor2@example.com")

    resp = client.get("/api/v1/admin/products", headers=headers)
    assert resp.status_code == 200  # 有 product:read

    resp = client.get("/api/v1/admin/rbac/roles", headers=headers)
    assert resp.status_code == 403  # 无 rbac:manage


def test_super_admin_can_access_all(client):
    headers = admin_headers(client, "root@example.com")
    resp = client.get("/api/v1/admin/dashboard/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "users_total" in data and "gmv_week" in data
