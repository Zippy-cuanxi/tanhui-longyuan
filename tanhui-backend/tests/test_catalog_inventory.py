"""商品生命周期 + 库存并发防超卖测试。"""
import uuid

from app.core.database import SessionLocal
from app.modules.inventory import service as inventory_service
from app.modules.inventory.models import Inventory
from tests.conftest import (
    admin_headers,
    create_approved_product,
    create_store_with_owner,
    login_headers,
    run_threads,
)


def test_product_lifecycle_and_visibility(client):
    store_id, _ = create_store_with_owner("pm@example.com", "生命周期测试店")
    headers = login_headers(client, "pm@example.com")
    admin = admin_headers(client, "admin-pl@example.com")

    # 1) 商家创建草稿（含 SKU 初始库存）
    resp = client.post(
        "/api/v1/merchant/products",
        json={
            "title": "兰州百合干",
            "subtitle": "七年生·特级",
            "category_id": None,
            "skus": [{"spec": "250g", "price": "58.00", "initial_stock": 50}],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    product_id = resp.json()["data"]["id"]

    # 2) 草稿期消费者不可见
    resp = client.get(f"/api/v1/products/{product_id}")
    assert resp.status_code == 404

    # 3) 提交审核 → 管理员驳回 → 重新提交 → 通过 → 上架
    resp = client.post(f"/api/v1/merchant/products/{product_id}/submit", headers=headers)
    assert resp.status_code == 200
    resp = client.post(
        f"/api/v1/admin/products/{product_id}/audit",
        json={"action": "reject", "reason": "资质图片缺失"},
        headers=admin,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "rejected"

    client.post(f"/api/v1/merchant/products/{product_id}/submit", headers=headers)
    resp = client.post(
        f"/api/v1/admin/products/{product_id}/audit",
        json={"action": "approve"},
        headers=admin,
    )
    assert resp.status_code == 200

    # 未上架前仍不可见
    resp = client.get(f"/api/v1/products/{product_id}")
    assert resp.status_code == 404

    resp = client.post(
        f"/api/v1/merchant/products/{product_id}/list", headers=headers
    )
    assert resp.status_code == 200

    # 4) 上架后可见，价格来自服务端
    resp = client.get(f"/api/v1/products/{product_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["skus"][0]["price"] == "58.00"


def test_concurrent_reservation_no_oversell():
    """并发防超卖：库存 10，20 个线程各预占 1，成功数必须 ≤ 10。"""
    store_id, _ = create_store_with_owner("conc@example.com", "并发测试店")
    sku_id = create_approved_product(store_id, "定西马铃薯", price="9.90", stock=10)

    # 预占需挂在真实店铺子单上（FK 约束），这里造一条最小订单链
    from app.core.base import gen_order_no
    from app.modules.orders.models import Order, StoreOrder
    from app.modules.users import service as users_service

    db = SessionLocal()
    try:
        buyer = users_service.register_user(db, "conc-buyer@example.com", "Passw0rd!123", None)
        order = Order(
            order_no=gen_order_no("TH"),
            user_id=buyer.id,
            status="pending_payment",
            receiver_name="测试",
            receiver_phone="13000000000",
            address="甘肃省兰州市测试地址",
            items_total=0,
            shipping_fee=0,
            points_deduct=0,
            pay_amount=0,
        )
        db.add(order)
        db.flush()
        so = StoreOrder(
            order_id=order.id,
            store_id=store_id,
            store_order_no=gen_order_no("SO"),
            status="pending_payment",
            items_total=0,
            shipping_fee=0,
            pay_amount=0,
        )
        db.add(so)
        db.commit()
        store_order_id = so.id
    finally:
        db.close()

    results = []
    lock = __import__("threading").Lock()

    def try_reserve():
        db = SessionLocal()
        try:
            reservation = inventory_service.reserve(
                db, sku_id, 1, store_order_id
            )
            db.commit()
            with lock:
                results.append("ok")
        except Exception:
            db.rollback()
            with lock:
                results.append("fail")
        finally:
            db.close()

    run_threads(try_reserve, 20)

    assert results.count("ok") == 10, f"成功数应为 10，实际 {results.count('ok')}"
    assert results.count("fail") == 10

    db = SessionLocal()
    try:
        inv = db.query(Inventory).filter(Inventory.sku_id == sku_id).one()
        assert inv.quantity_reserved == 10
        assert inv.quantity_total == 10
    finally:
        db.close()


def test_inventory_adjust_writes_log(client):
    store_id, owner = create_store_with_owner("adj@example.com", "库存调整店")
    sku_id = create_approved_product(store_id, "岷县当归", stock=100)
    headers = login_headers(client, "adj@example.com")

    resp = client.post(
        "/api/v1/merchant/inventory/adjust",
        json={"sku_id": str(sku_id), "delta": 50, "reason": "补货入库"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["quantity_total"] == 150

    # 超卖库存不能减少到负数
    resp = client.post(
        "/api/v1/merchant/inventory/adjust",
        json={"sku_id": str(sku_id), "delta": -999, "reason": "恶意扣减"},
        headers=headers,
    )
    assert resp.status_code == 409

    # 流水可查
    resp = client.get("/api/v1/merchant/inventory/logs", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["pagination"]["total"] >= 2
