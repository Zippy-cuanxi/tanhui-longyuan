"""订单核心测试：服务端计价、多商家拆单、快照、幂等、防篡改、状态机。"""
from decimal import Decimal

from app.core.database import SessionLocal
from app.modules.orders.models import Order, StoreOrder
from tests.conftest import (
    create_approved_product,
    create_store_with_owner,
    register_and_login,
)


def _buy_headers_and_address(client, email="buyer@example.com"):
    headers = register_and_login(client, email)
    resp = client.post(
        "/api/v1/users/me/addresses",
        json={
            "receiver": "李四",
            "phone": "13900000001",
            "province": "甘肃省",
            "city": "兰州市",
            "district": "城关区",
            "detail": "张掖路 1 号",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    return headers, resp.json()["data"]["id"]


def _two_store_skus():
    store_a, _ = create_store_with_owner("sa@example.com", "多商家A店")
    store_b, _ = create_store_with_owner("sb@example.com", "多商家B店")
    sku_a = create_approved_product(store_a, "静宁苹果", price="29.90", stock=50)
    sku_b = create_approved_product(store_b, "天水花牛苹果", price="39.90", stock=50)
    return sku_a, sku_b


def test_preview_server_side_pricing(client):
    headers, _ = _buy_headers_and_address(client)
    sku_a, sku_b = _two_store_skus()

    resp = client.post(
        "/api/v1/orders/preview",
        json={
            "items": [
                {"sku_id": str(sku_a), "quantity": 1, "expected_unit_price": "29.90"},
                {"sku_id": str(sku_b), "quantity": 2, "expected_unit_price": "39.90"},
            ]
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    # 29.90 + 79.80 = 109.70；两店各未达 99 包邮门槛 → 运费 8*2
    assert data["items_total"] == "109.70"
    assert data["shipping_fee"] == "16.00"
    assert data["pay_amount"] == "125.70"
    assert len(data["stores"]) == 2


def test_create_order_splits_by_store_and_snapshots(client):
    headers, addr_id = _buy_headers_and_address(client)
    sku_a, sku_b = _two_store_skus()

    resp = client.post(
        "/api/v1/orders",
        json={
            "address_id": addr_id,
            "items": [
                {"sku_id": str(sku_a), "quantity": 1, "expected_unit_price": "29.90"},
                {"sku_id": str(sku_b), "quantity": 2, "expected_unit_price": "39.90"},
            ],
            "use_points": False,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    order = resp.json()["data"]
    assert order["status"] == "pending_payment"
    assert len(order["store_orders"]) == 2
    # 快照价格与数量正确（每订单行一条快照记录）
    items = [(i["unit_price"], i["quantity"], i["subtotal"]) for so in order["store_orders"] for i in so["items"]]
    assert sorted(items) == [("29.90", 1, "29.90"), ("39.90", 2, "79.80")]


def test_create_order_price_changed_rejected(client):
    headers, addr_id = _buy_headers_and_address(client, "tamper@example.com")
    sku_a, sku_b = _two_store_skus()

    resp = client.post(
        "/api/v1/orders",
        json={
            "address_id": addr_id,
            "items": [{"sku_id": str(sku_a), "quantity": 1, "expected_unit_price": "0.01"}],
        },
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "PRICE_CHANGED"


def test_create_order_idempotent(client):
    headers, addr_id = _buy_headers_and_address(client, "idem@example.com")
    sku_a, _ = _two_store_skus()
    payload = {
        "address_id": addr_id,
        "items": [{"sku_id": str(sku_a), "quantity": 1, "expected_unit_price": "29.90"}],
        "idempotency_key": "order-key-001",
    }
    resp1 = client.post("/api/v1/orders", json=payload, headers=headers)
    assert resp1.status_code == 200
    resp2 = client.post("/api/v1/orders", json=payload, headers=headers)
    assert resp2.status_code == 200
    assert resp1.json()["data"]["id"] == resp2.json()["data"]["id"]

    # 同 key 不同内容 → IDEMPOTENCY_CONFLICT
    payload["items"][0]["quantity"] = 2
    resp3 = client.post("/api/v1/orders", json=payload, headers=headers)
    assert resp3.status_code == 409
    assert resp3.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_insufficient_stock_rejected(client):
    headers, addr_id = _buy_headers_and_address(client, "nostock@example.com")
    store_id, _ = create_store_with_owner("s3@example.com", "库存不足店")
    sku = create_approved_product(store_id, "临泽红枣", price="12.00", stock=2)

    resp = client.post(
        "/api/v1/orders",
        json={
            "address_id": addr_id,
            "items": [{"sku_id": str(sku), "quantity": 5, "expected_unit_price": "12.00"}],
        },
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "INSUFFICIENT_STOCK"


def test_cancel_order_releases_stock(client):
    headers, addr_id = _buy_headers_and_address(client, "cancel@example.com")
    store_id, _ = create_store_with_owner("s4@example.com", "取消测试店")
    sku = create_approved_product(store_id, "苦水玫瑰", price="15.00", stock=10)

    resp = client.post(
        "/api/v1/orders",
        json={
            "address_id": addr_id,
            "items": [{"sku_id": str(sku), "quantity": 3, "expected_unit_price": "15.00"}],
        },
        headers=headers,
    )
    order_id = resp.json()["data"]["id"]

    # 下单后可用库存 7
    db = SessionLocal()
    from app.modules.inventory.models import Inventory

    inv = db.query(Inventory).filter(Inventory.sku_id == sku).one()
    assert inv.quantity_reserved == 3
    db.close()

    resp = client.post(
        f"/api/v1/orders/{order_id}/cancel", json={"reason": "不想要了"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "cancelled"

    db = SessionLocal()
    inv = db.query(Inventory).filter(Inventory.sku_id == sku).one()
    assert inv.quantity_reserved == 0  # 预占已释放
    db.close()

    # 取消后不能再取消
    resp = client.post(f"/api/v1/orders/{order_id}/cancel", json={}, headers=headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "ORDER_STATE_INVALID"
