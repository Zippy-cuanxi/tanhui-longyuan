"""支付回调与退款测试：验签、金额核对、幂等、状态机、积分冲正、台账。"""


def _paid_order(client, email="pay@example.com"):
    """脚手架：下单 → Mock 支付成功 → 返回 (headers, order)。"""
    from tests.conftest import (
        create_approved_product,
        create_store_with_owner,
        register_and_login,
    )
    from tests.test_orders import _buy_headers_and_address

    headers, addr_id = _buy_headers_and_address(client, email)
    store_id, _ = create_store_with_owner("paystore@example.com", "支付测试店")
    sku = create_approved_product(store_id, "陇南橄榄油", price="99.00", stock=20)

    resp = client.post(
        "/api/v1/orders",
        json={
            "address_id": addr_id,
            "items": [{"sku_id": str(sku), "quantity": 1, "expected_unit_price": "99.00"}],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    order = resp.json()["data"]
    resp = client.post(f"/api/v1/payments/{order['id']}/init", headers=headers)
    assert resp.status_code == 200, resp.text
    pay_no = resp.json()["data"]["pay_no"]
    resp = client.post(
        "/api/v1/payments/mock/pay", json={"pay_no": pay_no}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    return headers, order["id"], pay_no


def test_mock_callback_bad_signature_rejected(client):
    headers, order_id, pay_no = _paid_order(client)
    # 已经 mock_pay 成功；构造一个坏签名的重复回调
    from app.core.database import SessionLocal
    from app.modules.payments.models import PaymentOrder

    db = SessionLocal()
    po = db.query(PaymentOrder).filter(PaymentOrder.pay_no == pay_no).one()
    db.close()

    resp = client.post(
        "/api/v1/payments/callback/mock",
        json={
            "pay_no": pay_no,
            "merchant_no": "MOCK8880001",
            "trade_no": "FAKE123",
            "amount": "99.00",
            "currency": "CNY",
            "status": "SUCCESS",
            "timestamp": "1700000000",
            "sign": "0000bad-signature",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "PAYMENT_SIGNATURE_INVALID"


def test_callback_amount_mismatch_rejected(client):
    from app.core.database import SessionLocal
    from app.modules.payments.providers import MockSandboxProvider

    headers, order_id, pay_no = _paid_order(client, "mismatch@example.com")
    provider = MockSandboxProvider()
    payload = {
        "pay_no": pay_no,
        "merchant_no": "MOCK8880001",
        "trade_no": "TAMPER001",
        "amount": "0.01",  # 篡改金额
        "currency": "CNY",
        "status": "SUCCESS",
        "timestamp": "1700000000",
    }
    resp = client.post(
        "/api/v1/payments/callback/mock",
        json={**payload, "sign": provider.sign(payload)},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "PAYMENT_AMOUNT_MISMATCH"


def test_duplicate_callback_idempotent(client):
    """同一回调重复投递：订单状态不重复流转、只入账一次。"""
    headers, order_id, pay_no = _paid_order(client, "dupcb@example.com")
    provider = __import__(
        "app.modules.payments.providers", fromlist=["MockSandboxProvider"]
    ).MockSandboxProvider()
    payload = {
        "pay_no": pay_no,
        "merchant_no": "MOCK8880001",
        "trade_no": "DUP001",
        "amount": "99.00",
        "currency": "CNY",
        "status": "SUCCESS",
        "timestamp": "1700000000",
    }
    r1 = client.post(
        "/api/v1/payments/callback/mock", json={**payload, "sign": provider.sign(payload)}
    )
    # 已成功的支付单收到重复回调 → 幂等返回 processed
    assert r1.status_code == 200
    assert r1.json().get("result") in ("processed", "duplicate")

    from app.core.database import SessionLocal
    from app.modules.finance.models import PlatformLedger
    from app.modules.orders.models import Order

    db = SessionLocal()
    order = db.get(Order, __import__("uuid").UUID(order_id))
    assert order.status == "paid"
    payment_count = (
        db.query(PlatformLedger)
        .filter(PlatformLedger.order_id == order.id, PlatformLedger.entry_type == "payment")
        .count()
    )
    assert payment_count == 1  # 只入账一次
    db.close()


def test_full_refund_flow_with_points_reversal(client):
    """完整链路：支付 → 确认收货 → 发放绿豆 → 全额退款 → 绿豆冲正 + 状态 refunded。"""
    from tests.conftest import admin_headers, register_and_login

    headers, order_id, pay_no = _paid_order(client, "refund@example.com")
    admin = admin_headers(client, "refund-admin@example.com")

    # 商家发货
    from app.core.database import SessionLocal
    from app.modules.orders import service as order_service
    from app.modules.orders.models import StoreOrder
    from app.modules.stores import service as store_service
    from tests.conftest import login_headers

    store_headers = login_headers(client, "paystore@example.com")
    db = SessionLocal()
    so = db.query(StoreOrder).filter(StoreOrder.order_id == __import__("uuid").UUID(order_id)).one()
    so_id = so.id
    db.close()
    resp = client.post(
        f"/api/v1/merchant/orders/{so_id}/ship",
        json={"carrier": "顺丰速运", "tracking_no": "SF123456789"},
        headers=store_headers,
    )
    assert resp.status_code == 200, resp.text

    # 支付成功后绿色积分即到账（确认收货不会重复发放）
    resp = client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["points_estimate"] == 99
    assert resp.json()["data"]["points_earned"] == 99

    # 确认收货 → 订单完成；幂等，不会重复发放积分
    resp = client.post(f"/api/v1/orders/{order_id}/confirm-receipt", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "completed"
    assert resp.json()["data"]["points_earned"] == 99

    resp = client.get("/api/v1/points/account", headers=headers)
    assert resp.json()["data"]["balance"] == 99

    # 申请退款
    resp = client.post(
        f"/api/v1/orders/{order_id}/refunds",
        json={"reason": "质量问题"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    refund_id = resp.json()["data"]["id"]

    # 管理员批准退款（Mock 原路退回）
    resp = client.post(
        f"/api/v1/admin/refunds/{refund_id}/handle",
        json={"action": "approve", "note": "核实无误"},
        headers=admin,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "refunded"

    # 订单状态 refunded，绿豆已冲正
    resp = client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert resp.json()["data"]["status"] == "refunded"
    resp = client.get("/api/v1/points/account", headers=headers)
    assert resp.json()["data"]["balance"] == 0

    # 平台账有退款与佣金记录
    from app.modules.finance.models import PlatformLedger

    db = SessionLocal()
    entries = (
        db.query(PlatformLedger)
        .filter(PlatformLedger.order_id == __import__("uuid").UUID(order_id))
        .all()
    )
    types = {e.entry_type for e in entries}
    assert {"payment", "commission", "refund"} <= types
    db.close()
