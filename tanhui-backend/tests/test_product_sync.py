"""商品审核 → 消费者端同步：全场景测试。

覆盖：
1. 审核通过触发全量同步（名称/描述/价格/SKU/主图/详情图/分类层级与排序）；
2. 分类归属与排序一致性；
3. 哈希一致性校验与漂移修复（双向对账）；
4. 失败自动重试（最多 3 次）与重试成功；
5. 重试耗尽后的管理员提示、失败日志与事务原子性（无部分字段残留）；
6. 同步日志查询（审计追溯）。
"""
import uuid
from decimal import Decimal

from app.core.database import SessionLocal
from app.modules.catalog import service as catalog_service
from app.modules.catalog import sync_service
from app.modules.catalog.models import Category, Product, ProductSku
from app.modules.catalog.schemas import ProductCreateIn, SkuIn
from app.modules.catalog.sync_models import (
    ConsumerCategory,
    ConsumerProduct,
    ConsumerProductImage,
    ConsumerProductSku,
    ProductSyncLog,
)
from tests.conftest import (
    admin_headers,
    create_store_with_owner,
    login_headers,
    make_admin,
)

ADMIN_EMAIL = "sync-admin@example.com"


def _create_category(name: str, parent_id: uuid.UUID | None = None, sort: int = 0) -> uuid.UUID:
    db = SessionLocal()
    try:
        category = Category(name=name, parent_id=parent_id, sort=sort)
        db.add(category)
        db.commit()
        return category.id
    finally:
        db.close()


def _create_pending_product(
    store_id: uuid.UUID,
    category_id: uuid.UUID | None,
    *,
    title: str = "静宁红富士苹果",
    price: str = "68.00",
    stock: int = 500,
    images: tuple[str, ...] = ("/uploads/demo/products/jingning-apple.webp",),
) -> tuple[uuid.UUID, uuid.UUID]:
    """创建商品 + 图片 → 提交审核，返回 (product_id, sku_id)。"""
    db = SessionLocal()
    try:
        product = catalog_service.create_product(
            db,
            store_id,
            ProductCreateIn(
                title=title,
                subtitle="高原红富士·脆甜多汁",
                description="甘肃静宁产地直发，全程冷链（仿真描述）",
                category_id=category_id,
                skus=[SkuIn(spec="5kg 精选装", price=Decimal(price), initial_stock=stock)],
            ),
        )
        for url in images:
            catalog_service.add_image(db, store_id, product.id, url)
        catalog_service.submit_for_review(db, store_id, product.id)
        db.commit()
        sku_id = db.query(ProductSku).filter_by(product_id=product.id).one().id
        return product.id, sku_id
    finally:
        db.close()


def _approve(client, product_id: uuid.UUID, headers: dict) -> dict:
    resp = client.post(
        f"/api/v1/admin/products/{product_id}/audit",
        json={"action": "approve"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_approve_triggers_full_sync_and_category_mapping(client):
    store_id, _ = create_store_with_owner("sync-owner@example.com", "同步测试店")
    parent_id = _create_category("新鲜果蔬", sort=30)
    child_id = _create_category("静宁苹果", parent_id=parent_id, sort=5)
    product_id, sku_id = _create_pending_product(
        store_id,
        child_id,
        images=(
            "/uploads/demo/products/jingning-apple-1.webp",
            "/uploads/demo/products/jingning-apple-2.webp",
        ),
    )
    admin_id = make_admin(ADMIN_EMAIL)
    headers = admin_headers(client, ADMIN_EMAIL)

    data = _approve(client, product_id, headers)

    # 审核响应明确回传同步结果与哈希
    assert data["status"] == "approved"
    assert data["sync_status"] == "success", data.get("sync_error")
    assert data["sync_attempts"] == 1
    assert data["source_hash"] and data["source_hash"] == data["consumer_hash"]
    assert data["sync_error"] is None
    assert data["sync_log_id"]

    db = SessionLocal()
    try:
        source = db.get(Product, product_id)
        mirror = db.get(ConsumerProduct, product_id)
        assert mirror is not None
        # 全量字段一致
        for field in (
            "store_id",
            "category_id",
            "title",
            "subtitle",
            "description",
            "status",
            "is_listed",
            "aid_project_id",
        ):
            assert getattr(mirror, field) == getattr(source, field), field
        assert mirror.sync_version == 1
        assert mirror.source_hash == data["source_hash"]

        # SKU / 图片全量且主键保持一致
        mirror_skus = (
            db.query(ConsumerProductSku).filter_by(product_id=product_id).all()
        )
        assert [s.id for s in mirror_skus] == [sku_id]
        assert mirror_skus[0].spec == "5kg 精选装"
        assert f"{mirror_skus[0].price:.2f}" == "68.00"
        assert mirror_skus[0].stock == 500

        mirror_images = (
            db.query(ConsumerProductImage)
            .filter_by(product_id=product_id)
            .order_by(ConsumerProductImage.sort)
            .all()
        )
        assert [i.url for i in mirror_images] == [
            "/uploads/demo/products/jingning-apple-1.webp",
            "/uploads/demo/products/jingning-apple-2.webp",
        ]

        # 分类层级 / 排序完全一致
        child = db.get(ConsumerCategory, child_id)
        parent = db.get(ConsumerCategory, parent_id)
        assert child is not None and parent is not None
        assert child.name == "静宁苹果" and child.parent_id == parent_id and child.sort == 5
        assert parent.name == "新鲜果蔬" and parent.parent_id is None and parent.sort == 30

        # 同步日志：触发时间、操作管理员、商品 ID、目标分类、结果、耗时
        log = (
            db.query(ProductSyncLog)
            .filter_by(product_id=product_id, trigger_type="audit_approve")
            .one()
        )
        assert log.status == "success"
        assert log.operator_id == admin_id
        assert log.target_category_id == child_id
        assert log.attempts == 1 and log.max_attempts == 3
        assert log.duration_ms >= 0
        assert log.source_hash == log.target_hash == data["source_hash"]
        assert log.created_at is not None
    finally:
        db.close()

    # 审核通过即上架 → 消费者端「全部商品」与详情立即可见
    resp = client.get(f"/api/v1/products/{product_id}")
    assert resp.status_code == 200, resp.text
    detail = resp.json()["data"]
    assert detail["title"] == "静宁红富士苹果"
    assert detail["description"].startswith("甘肃静宁产地直发")
    assert detail["category_id"] == str(child_id)
    assert detail["store_name"] == "同步测试店"
    assert [sku["spec"] for sku in detail["skus"]] == ["5kg 精选装"]
    assert detail["skus"][0]["stock"] == 500
    assert len(detail["images"]) == 2

    resp = client.get(
        "/api/v1/products", params={"category_id": str(child_id), "page_size": 20}
    )
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["data"]["items"]]
    assert str(product_id) in ids


def test_sync_retries_then_succeeds(client, monkeypatch):
    store_id, _ = create_store_with_owner("retry-owner@example.com", "重试测试店")
    category_id = _create_category("测试分类", sort=1)
    product_id, _ = _create_pending_product(store_id, category_id, title="重试商品")
    headers = admin_headers(client, ADMIN_EMAIL)

    original = sync_service._apply_mirror
    calls = {"count": 0}

    def flaky(db, product, expected_hash):
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("模拟同步通道抖动")
        return original(db, product, expected_hash)

    monkeypatch.setattr(sync_service, "_apply_mirror", flaky)

    data = _approve(client, product_id, headers)
    assert data["sync_status"] == "success"
    assert data["sync_attempts"] == 3
    assert calls["count"] == 3

    db = SessionLocal()
    try:
        log = (
            db.query(ProductSyncLog)
            .filter_by(product_id=product_id, trigger_type="audit_approve")
            .one()
        )
        assert log.status == "success" and log.attempts == 3
        assert db.get(ConsumerProduct, product_id) is not None
    finally:
        db.close()


def test_sync_failure_exhausts_retries_logs_and_rolls_back(client, monkeypatch):
    store_id, _ = create_store_with_owner("fail-owner@example.com", "失败测试店")
    category_id = _create_category("失败分类", sort=2)
    product_id, _ = _create_pending_product(
        store_id, category_id, title="同步失败商品", images=("/a.webp", "/b.webp")
    )
    headers = admin_headers(client, ADMIN_EMAIL)

    original = sync_service._apply_mirror
    calls = {"count": 0}

    def partial_then_fail(db, product, expected_hash):
        # 先真实写入产品/SKU/图片，再抛错：用于验证 SAVEPOINT 整体回滚
        calls["count"] += 1
        original(db, product, expected_hash)
        raise RuntimeError("模拟写后哈希校验失败")

    monkeypatch.setattr(sync_service, "_apply_mirror", partial_then_fail)

    data = _approve(client, product_id, headers)
    assert data["status"] == "approved"  # 审核结果保留，管理员可据提示重试
    assert data["sync_status"] == "failed"
    assert data["sync_attempts"] == 3
    assert "同步消费者端失败" in (data["sync_message"] or "")
    assert "已重试 3 次" in (data["sync_message"] or "")
    assert calls["count"] == 3

    db = SessionLocal()
    try:
        # 事务原子性：失败后消费者端没有任何半成品数据
        assert db.get(ConsumerProduct, product_id) is None
        assert (
            db.query(ConsumerProductSku).filter_by(product_id=product_id).count() == 0
        )
        assert (
            db.query(ConsumerProductImage).filter_by(product_id=product_id).count() == 0
        )
        # 失败日志必须落盘，支持审计
        log = (
            db.query(ProductSyncLog)
            .filter_by(product_id=product_id, trigger_type="audit_approve")
            .one()
        )
        assert log.status == "failed"
        assert log.attempts == 3 and log.max_attempts == 3
        assert log.error_message and "模拟写后哈希校验失败" in log.error_message
        assert log.target_category_id == category_id
    finally:
        db.close()


def test_hash_drift_detection_and_manual_resync(client):
    store_id, _ = create_store_with_owner("drift-owner@example.com", "漂移测试店")
    category_id = _create_category("漂移分类", sort=3)
    product_id, _ = _create_pending_product(store_id, category_id, title="漂移校验商品")
    headers = admin_headers(client, ADMIN_EMAIL)
    _approve(client, product_id, headers)

    # 直接篡改消费者镜像，模拟两端漂移
    db = SessionLocal()
    try:
        mirror = db.get(ConsumerProduct, product_id)
        mirror.title = "被篡改的标题"
        db.commit()
    finally:
        db.close()

    resp = client.get(f"/api/v1/admin/products/{product_id}/sync-status", headers=headers)
    assert resp.status_code == 200, resp.text
    report = resp.json()["data"]
    assert report["source_exists"] is True
    assert report["consumer_exists"] is True
    assert report["consistent"] is False
    assert report["source_hash"] != report["consumer_hash"]

    resp = client.post(f"/api/v1/admin/products/{product_id}/sync", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "success"

    resp = client.get(f"/api/v1/admin/products/{product_id}/sync-status", headers=headers)
    report = resp.json()["data"]
    assert report["consistent"] is True
    assert report["source_hash"] == report["consumer_hash"]

    db = SessionLocal()
    try:
        assert db.get(ConsumerProduct, product_id).title == "漂移校验商品"
    finally:
        db.close()


def test_sync_logs_support_audit_query(client):
    store_id, _ = create_store_with_owner("log-owner@example.com", "日志测试店")
    category_id = _create_category("日志分类", sort=4)
    product_id, _ = _create_pending_product(store_id, category_id, title="日志商品")
    headers = admin_headers(client, ADMIN_EMAIL)
    _approve(client, product_id, headers)

    # 上架会再产生一条 listing_change 日志
    merchant_headers = login_headers(client, "log-owner@example.com")
    client.post(f"/api/v1/merchant/products/{product_id}/list", headers=merchant_headers)

    resp = client.get(
        "/api/v1/admin/product-sync-logs",
        params={"product_id": str(product_id), "page_size": 20},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    page = resp.json()["data"]
    assert page["pagination"]["total"] >= 2
    triggers = {item["trigger_type"] for item in page["items"]}
    assert {"audit_approve", "listing_change"} <= triggers
    assert all(item["product_id"] == str(product_id) for item in page["items"])

    resp = client.get(
        "/api/v1/admin/product-sync-logs",
        params={"product_id": str(product_id), "status": "success"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["pagination"]["total"] >= 2

    # 商品维度日志接口同样可用
    resp = client.get(
        f"/api/v1/admin/products/{product_id}/sync-logs", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["pagination"]["total"] >= 2


def test_reject_does_not_publish_to_consumer(client):
    store_id, _ = create_store_with_owner("reject-owner@example.com", "驳回测试店")
    category_id = _create_category("驳回分类", sort=5)
    product_id, _ = _create_pending_product(store_id, category_id, title="驳回商品")
    headers = admin_headers(client, ADMIN_EMAIL)

    resp = client.post(
        f"/api/v1/admin/products/{product_id}/audit",
        json={"action": "reject", "reason": "资质不全"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "rejected"
    assert resp.json()["data"]["sync_status"] is None

    db = SessionLocal()
    try:
        assert db.get(ConsumerProduct, product_id) is None
        assert db.query(ProductSyncLog).filter_by(product_id=product_id).count() == 0
    finally:
        db.close()
