"""积分与 OpenAPI 一致性测试 + Alembic 迁移有效性验证。"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_admin_adjust_and_redemption(client):
    from tests.conftest import admin_headers, login_headers, register_user

    uid = register_user("pts@example.com")
    headers = login_headers(client, "pts@example.com")
    admin = admin_headers(client, "pts-admin@example.com")

    # 管理员调整（带原因）→ 成功
    resp = client.post(
        "/api/v1/admin/points/adjust",
        json={"user_id": str(uid), "delta": 600, "reason": "测试发放"},
        headers=admin,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["balance_after"] == 600

    # 查询余额与流水
    resp = client.get("/api/v1/points/account", headers=headers)
    assert resp.json()["data"]["balance"] == 600
    resp = client.get("/api/v1/points/transactions", headers=headers)
    assert resp.json()["data"]["pagination"]["total"] == 1

    # 兑换目录 + 兑换
    resp = client.get("/api/v1/points/redemption-catalog", headers=headers)
    assert resp.status_code == 200
    resp = client.post(
        "/api/v1/points/redemptions", json={"reward_code": "coupon_5"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["points_spent"] == 500
    assert resp.json()["data"]["mock"] is True

    resp = client.get("/api/v1/points/account", headers=headers)
    assert resp.json()["data"]["balance"] == 100

    # 余额不足兑换 → 409
    resp = client.post(
        "/api/v1/points/redemptions", json={"reward_code": "coupon_10"}, headers=headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "POINTS_INSUFFICIENT"


def test_admin_adjust_requires_reason(client):
    from tests.conftest import admin_headers, register_user

    uid = register_user("noreason@example.com")
    admin = admin_headers(client, "adj-admin@example.com")

    # 缺 reason → 422
    resp = client.post(
        "/api/v1/admin/points/adjust",
        json={"user_id": str(uid), "delta": 10},
        headers=admin,
    )
    assert resp.status_code == 422

    # reason 全空格 → 422（业务规则：调整必须说明原因）
    resp = client.post(
        "/api/v1/admin/points/adjust",
        json={"user_id": str(uid), "delta": 10, "reason": "   "},
        headers=admin,
    )
    assert resp.status_code == 422


def test_points_rules_seeded(client):
    from app.core.database import SessionLocal
    from app.modules.points.models import PointRule

    db = SessionLocal()
    try:
        codes = {r.code for r in db.query(PointRule).all()}
        assert {"order_earn", "deduct", "refund_reverse"} <= codes
    finally:
        db.close()


def test_aid_donation_awards_points_and_returns_balance(client):
    """助农资助：按 1 元 = 3 积分发放，响应返回所得积分与最新余额。"""
    from decimal import Decimal

    from app.core.base import utcnow
    from app.core.database import SessionLocal
    from app.modules.aid.models import AidProject, Cooperative
    from tests.conftest import login_headers, register_user

    register_user("aid-donor@example.com")
    headers = login_headers(client, "aid-donor@example.com")

    db = SessionLocal()
    try:
        coop = Cooperative(name="积分测试合作社", region="甘肃省定西市")
        db.add(coop)
        db.flush()
        project = AidProject(
            cooperative_id=coop.id,
            title="积分测试助农项目",
            description="仿真项目",
            goal_amount=Decimal("10000.00"),
            raised_amount=Decimal("0.00"),
            status="published",
            published_at=utcnow(),
        )
        db.add(project)
        db.commit()
        project_id = project.id
    finally:
        db.close()

    resp = client.post(
        f"/api/v1/aid/projects/{project_id}/donations",
        json={"amount": "50.00", "display_mode": "anonymous"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["points_earned"] == 150
    assert data["balance"] == 150
    assert data["amount"] == "50.00"

    # 个人中心余额实时反映
    resp = client.get("/api/v1/points/account", headers=headers)
    assert resp.json()["data"]["balance"] == 150

    # 积分流水记录本次资助
    resp = client.get("/api/v1/points/transactions", headers=headers)
    page = resp.json()["data"]
    assert page["pagination"]["total"] == 1
    assert page["items"][0]["amount"] == 150
    assert page["items"][0]["source_type"] == "aid_donation"

    # 我的资助记录返回获得积分
    resp = client.get("/api/v1/aid/donations/me", headers=headers)
    records = resp.json()["data"]
    assert records and records[0]["points_earned"] == 150


def test_openapi_generated_and_consistent(client):
    """OpenAPI 契约生成且包含统一响应结构。"""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert spec["info"]["title"]
    assert spec["openapi"].startswith("3.")
    # 关键接口在契约中
    paths = spec["paths"]
    for expected in (
        "/api/v1/auth/login",
        "/api/v1/orders",
        "/api/v1/orders/preview",
        "/api/v1/payments/callback/mock",
        "/api/v1/client/config/{page_key}",
        "/api/v1/admin/dashboard/stats",
    ):
        assert expected in paths, f"契约缺少 {expected}"
    # 统一错误响应组件存在
    schemas = spec.get("components", {}).get("schemas", {})
    assert any(k.startswith("ApiResponse") for k in schemas), "契约缺少统一响应结构"


def test_alembic_migration_creates_all_tables(tmp_path):
    """在全新库上执行 alembic upgrade head，校验关键表全部创建。"""
    env = dict(os.environ)
    db_file = tmp_path / "mig.db"
    env["TANHUI_DATABASE_URL"] = f"sqlite:///{db_file}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout

    import sqlite3

    conn = sqlite3.connect(db_file)
    try:
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for expected in (
            "users",
            "roles",
            "merchants",
            "stores",
            "products",
            "inventories",
            "orders",
            "store_orders",
            "payment_orders",
            "refunds",
            "point_accounts",
            "cms_pages",
            "platform_ledger",
        ):
            assert expected in tables, f"迁移缺少表 {expected}"
    finally:
        conn.close()
