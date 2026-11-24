"""管理端 → 消费者端商品同步服务。

能力：
1. 全量同步商品名称、描述、SKU/价格、库存关联信息、主图与详情图、分类层级与排序；
2. 每次同步在 SAVEPOINT 内完成，失败整体回滚，杜绝"部分字段写入 / 分类归属异常"；
3. 同步后重新读取消费者镜像并计算 SHA-256，与源端快照哈希比对；
4. 校验或写入失败自动重试，最多 3 次；仍失败则写入审计日志并返回明确错误信息；
5. 所有同步（成功/失败）均写入 product_sync_logs，支持审计追溯；
6. 提供一致性校验与手动重同步，支持两端数据漂移修复。
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, inspect, select
from sqlalchemy.orm import Session

from app.core.base import utcnow
from app.core.types import q2
from app.modules.catalog.models import (
    Category,
    Product,
    ProductAuditRecord,
    ProductImage,
    ProductSku,
)
from app.modules.catalog.sync_models import (
    ConsumerCategory,
    ConsumerProduct,
    ConsumerProductImage,
    ConsumerProductSku,
    ProductSyncLog,
)
from app.modules.inventory.models import Inventory

MAX_ATTEMPTS = 3
_TABLES_READY = False
SYNC_TABLES = (
    ConsumerCategory.__table__,
    ConsumerProduct.__table__,
    ConsumerProductSku.__table__,
    ConsumerProductImage.__table__,
    ProductSyncLog.__table__,
)


class SyncVerificationError(RuntimeError):
    """两端哈希不一致。"""


@dataclass
class SyncOutcome:
    """同步结果（供接口层拼装管理员提示）。"""

    product_id: uuid.UUID
    success: bool
    attempts: int
    max_attempts: int
    duration_ms: int
    target_category_id: uuid.UUID | None = None
    source_hash: str | None = None
    target_hash: str | None = None
    error: str | None = None
    log_id: uuid.UUID | None = None
    message: str = ""

    def as_dict(self) -> dict:
        return {
            "success": self.success,
            "status": "success" if self.success else "failed",
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "duration_ms": self.duration_ms,
            "target_category_id": self.target_category_id,
            "source_hash": self.source_hash,
            "target_hash": self.target_hash,
            "error": self.error,
            "log_id": self.log_id,
            "message": self.message,
        }


# ---------------- 表结构自愈（开发库/旧库兼容）----------------
def ensure_sync_tables(bind) -> None:
    """仅为同步相关表做 checkfirst 建表，避免旧开发库缺少镜像表导致页面不可用。

    生产环境仍以 `alembic upgrade head` 为准。
    """
    existing = set(inspect(bind).get_table_names())
    for table in SYNC_TABLES:
        if table.name not in existing:
            table.create(bind=bind, checkfirst=True)


def _ensure_tables_once(db: Session) -> None:
    """SQLite 开发库/种子脚本自愈；PostgreSQL 生产库交由 Alembic 管理。"""
    global _TABLES_READY
    if _TABLES_READY:
        return
    bind = db.get_bind()
    if bind.dialect.name == "sqlite":
        ensure_sync_tables(bind)
    _TABLES_READY = True


# ---------------- 快照与哈希 ----------------
def _sid(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _money(value: Decimal | None) -> str | None:
    return f"{q2(value):.2f}" if value is not None else None


def _category_chain(db: Session, model, category_id: uuid.UUID | None) -> list[dict]:
    """自根到叶读取分类链，包含层级、排序与启用状态。"""
    chain: list[dict] = []
    seen: set[uuid.UUID] = set()
    current = category_id
    while current is not None and current not in seen:
        seen.add(current)
        category = db.get(model, current)
        if category is None:
            break
        chain.append(
            {
                "id": str(category.id),
                "parent_id": _sid(category.parent_id),
                "name": category.name,
                "icon_url": category.icon_url,
                "sort": int(category.sort),
                "is_active": bool(category.is_active),
            }
        )
        current = category.parent_id
    chain.reverse()
    return chain


def _product_fields(product) -> dict:
    return {
        "id": str(product.id),
        "store_id": str(product.store_id),
        "category_id": _sid(product.category_id),
        "aid_project_id": _sid(product.aid_project_id),
        "title": product.title,
        "subtitle": product.subtitle,
        "description": product.description,
        "status": product.status,
        "is_listed": bool(product.is_listed),
        "audit_reason": product.audit_reason,
        "audited_by": _sid(product.audited_by),
        "audited_at": _dt(product.audited_at),
        "created_at": _dt(product.created_at),
    }


def _sku_fields(sku) -> dict:
    return {
        "id": str(sku.id),
        "spec": sku.spec,
        "code": sku.code,
        "price": _money(sku.price),
        "is_active": bool(sku.is_active),
    }


def _image_fields(image) -> dict:
    return {"id": str(image.id), "url": image.url, "sort": int(image.sort)}


def _hash(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def source_snapshot(db: Session, product: Product) -> dict:
    skus = list(
        db.execute(
            select(ProductSku).where(ProductSku.product_id == product.id)
        ).scalars()
    )
    images = list(
        db.execute(
            select(ProductImage).where(ProductImage.product_id == product.id)
        ).scalars()
    )
    skus.sort(key=lambda item: str(item.id))
    images.sort(key=lambda item: (int(item.sort), item.url, str(item.id)))
    return {
        "product": _product_fields(product),
        "category_path": _category_chain(db, Category, product.category_id),
        "skus": [_sku_fields(item) for item in skus],
        "images": [_image_fields(item) for item in images],
    }


def target_snapshot(db: Session, product_id: uuid.UUID) -> dict | None:
    product = db.get(ConsumerProduct, product_id)
    if product is None:
        return None
    skus = list(
        db.execute(
            select(ConsumerProductSku).where(ConsumerProductSku.product_id == product_id)
        ).scalars()
    )
    images = list(
        db.execute(
            select(ConsumerProductImage).where(
                ConsumerProductImage.product_id == product_id
            )
        ).scalars()
    )
    skus.sort(key=lambda item: str(item.id))
    images.sort(key=lambda item: (int(item.sort), item.url, str(item.id)))
    return {
        "product": _product_fields(product),
        "category_path": _category_chain(db, ConsumerCategory, product.category_id),
        "skus": [_sku_fields(item) for item in skus],
        "images": [_image_fields(item) for item in images],
    }


def compute_source_hash(db: Session, product: Product) -> str:
    return _hash(source_snapshot(db, product))


def compute_target_hash(db: Session, product_id: uuid.UUID) -> str | None:
    snapshot = target_snapshot(db, product_id)
    return _hash(snapshot) if snapshot is not None else None


# ---------------- 镜像写入（SAVEPOINT 内调用）----------------
def _ensure_category_chain(db: Session, category_id: uuid.UUID | None) -> None:
    """按管理端分类链逐级写入消费者端，保持层级与排序完全一致。"""
    _ensure_category_node(db, category_id, set())


def _ensure_category_node(
    db: Session, category_id: uuid.UUID | None, seen: set[uuid.UUID]
) -> None:
    if category_id is None or category_id in seen:
        return
    seen.add(category_id)
    source = db.get(Category, category_id)
    if source is None:
        return
    if source.parent_id is not None:
        _ensure_category_node(db, source.parent_id, seen)
    mirror = db.get(ConsumerCategory, source.id)
    if mirror is None:
        mirror = ConsumerCategory(id=source.id)
        db.add(mirror)
    mirror.parent_id = source.parent_id
    mirror.name = source.name
    mirror.icon_url = source.icon_url
    mirror.sort = source.sort
    mirror.is_active = source.is_active
    mirror.synced_at = utcnow()
    # 立即 flush，保证同一次同步内的下一级分类可通过 get 命中
    db.flush()


def _apply_mirror(db: Session, product: Product, expected_hash: str) -> None:
    """全量写入消费者镜像；调用方负责 SAVEPOINT 与异常回滚。"""
    _ensure_category_chain(db, product.category_id)

    mirror = db.get(ConsumerProduct, product.id)
    if mirror is None:
        mirror = ConsumerProduct(id=product.id, created_at=product.created_at)
        db.add(mirror)
    mirror.store_id = product.store_id
    mirror.category_id = product.category_id
    mirror.aid_project_id = product.aid_project_id
    mirror.title = product.title
    mirror.subtitle = product.subtitle
    mirror.description = product.description
    mirror.status = product.status
    mirror.is_listed = product.is_listed
    mirror.audit_reason = product.audit_reason
    mirror.audited_by = product.audited_by
    mirror.audited_at = product.audited_at
    mirror.created_at = product.created_at
    mirror.sync_version = (mirror.sync_version or 0) + 1
    mirror.source_hash = expected_hash
    mirror.synced_at = utcnow()

    source_skus = {
        sku.id: sku
        for sku in db.execute(
            select(ProductSku).where(ProductSku.product_id == product.id)
        ).scalars()
    }
    stocks = {
        inv.sku_id: max(0, int(inv.quantity_total) - int(inv.quantity_reserved))
        for inv in db.execute(
            select(Inventory).where(Inventory.sku_id.in_(list(source_skus)))
        ).scalars()
    }
    mirror_skus = {
        sku.id: sku
        for sku in db.execute(
            select(ConsumerProductSku).where(
                ConsumerProductSku.product_id == product.id
            )
        ).scalars()
    }
    for sku_id, sku in source_skus.items():
        target = mirror_skus.get(sku_id)
        if target is None:
            target = ConsumerProductSku(id=sku.id, product_id=product.id)
            db.add(target)
        target.spec = sku.spec
        target.code = sku.code
        target.price = sku.price
        target.is_active = sku.is_active
        target.stock = stocks.get(sku_id, 0)
    stale_sku_ids = set(mirror_skus) - set(source_skus)
    if stale_sku_ids:
        db.execute(
            delete(ConsumerProductSku).where(ConsumerProductSku.id.in_(stale_sku_ids))
        )

    source_images = {
        image.id: image
        for image in db.execute(
            select(ProductImage).where(ProductImage.product_id == product.id)
        ).scalars()
    }
    mirror_images = {
        image.id: image
        for image in db.execute(
            select(ConsumerProductImage).where(
                ConsumerProductImage.product_id == product.id
            )
        ).scalars()
    }
    for image_id, image in source_images.items():
        target = mirror_images.get(image_id)
        if target is None:
            target = ConsumerProductImage(id=image.id, product_id=product.id)
            db.add(target)
        target.url = image.url
        target.sort = image.sort
    stale_image_ids = set(mirror_images) - set(source_images)
    if stale_image_ids:
        db.execute(
            delete(ConsumerProductImage).where(
                ConsumerProductImage.id.in_(stale_image_ids)
            )
        )

    db.flush()


def _write_log(
    db: Session,
    *,
    product_id: uuid.UUID,
    operator_id: uuid.UUID | None,
    trigger_type: str,
    target_category_id: uuid.UUID | None,
    status: str,
    attempts: int,
    max_attempts: int,
    duration_ms: int,
    source_hash: str | None,
    target_hash: str | None,
    error: str | None,
) -> ProductSyncLog:
    log = ProductSyncLog(
        product_id=product_id,
        operator_id=operator_id,
        trigger_type=trigger_type,
        target_category_id=target_category_id,
        status=status,
        attempts=attempts,
        max_attempts=max_attempts,
        duration_ms=duration_ms,
        source_hash=source_hash,
        target_hash=target_hash,
        error_message=error,
    )
    db.add(log)
    db.flush()
    return log


# ---------------- 对外主入口 ----------------
def sync_product(
    db: Session,
    product_id: uuid.UUID,
    operator_id: uuid.UUID | None = None,
    trigger_type: str = "manual",
    max_attempts: int = MAX_ATTEMPTS,
) -> SyncOutcome:
    """同步单个商品到消费者端。

    - 每次尝试在 SAVEPOINT 内全量写入并回读校验哈希，失败则整体回滚；
    - 最多重试 max_attempts 次；全部失败返回 success=False 且必定留下失败日志；
    - 不向外抛异常，调用方（审核接口）可继续提交审核结果并向管理员展示同步失败提示。
    """
    started = time.perf_counter()
    attempts_limit = max(1, int(max_attempts))
    _ensure_tables_once(db)

    product = db.get(Product, product_id)
    if product is None:
        duration_ms = int((time.perf_counter() - started) * 1000)
        log = _write_log(
            db,
            product_id=product_id,
            operator_id=operator_id,
            trigger_type=trigger_type,
            target_category_id=None,
            status="failed",
            attempts=0,
            max_attempts=attempts_limit,
            duration_ms=duration_ms,
            source_hash=None,
            target_hash=None,
            error="商品不存在",
        )
        return SyncOutcome(
            product_id=product_id,
            success=False,
            attempts=0,
            max_attempts=attempts_limit,
            duration_ms=duration_ms,
            error="商品不存在",
            log_id=log.id,
            message="商品不存在，无法同步至消费者端",
        )

    db.flush()
    source_hash = compute_source_hash(db, product)
    target_hash: str | None = None
    last_error: str | None = None
    attempts = 0

    for attempt in range(1, attempts_limit + 1):
        attempts = attempt
        try:
            with db.begin_nested():
                _apply_mirror(db, product, source_hash)
                db.flush()
                target_hash = compute_target_hash(db, product.id)
                if target_hash is None:
                    raise SyncVerificationError("消费者端未生成商品镜像")
                if target_hash != source_hash:
                    raise SyncVerificationError(
                        f"两端数据哈希不一致（源 {source_hash[:12]}… / 目标 {target_hash[:12]}…）"
                    )
            duration_ms = int((time.perf_counter() - started) * 1000)
            log = _write_log(
                db,
                product_id=product.id,
                operator_id=operator_id,
                trigger_type=trigger_type,
                target_category_id=product.category_id,
                status="success",
                attempts=attempts,
                max_attempts=attempts_limit,
                duration_ms=duration_ms,
                source_hash=source_hash,
                target_hash=target_hash,
                error=None,
            )
            return SyncOutcome(
                product_id=product.id,
                success=True,
                attempts=attempts,
                max_attempts=attempts_limit,
                duration_ms=duration_ms,
                target_category_id=product.category_id,
                source_hash=source_hash,
                target_hash=target_hash,
                log_id=log.id,
                message="同步成功",
            )
        except Exception as exc:  # noqa: BLE001 - 同步失败必须转为可审计结果
            last_error = f"{type(exc).__name__}: {exc}"
            db.expire_all()
            if attempt < attempts_limit:
                time.sleep(0.02 * attempt)

    duration_ms = int((time.perf_counter() - started) * 1000)
    log = _write_log(
        db,
        product_id=product.id,
        operator_id=operator_id,
        trigger_type=trigger_type,
        target_category_id=product.category_id,
        status="failed",
        attempts=attempts,
        max_attempts=attempts_limit,
        duration_ms=duration_ms,
        source_hash=source_hash,
        target_hash=target_hash,
        error=last_error,
    )
    return SyncOutcome(
        product_id=product.id,
        success=False,
        attempts=attempts,
        max_attempts=attempts_limit,
        duration_ms=duration_ms,
        target_category_id=product.category_id,
        source_hash=source_hash,
        target_hash=target_hash,
        error=last_error,
        log_id=log.id,
        message=(
            f"商品审核已生效，但同步消费者端失败（已重试 {attempts} 次）：{last_error}"
        ),
    )


def consistency_report(db: Session, product_id: uuid.UUID) -> dict:
    """比对两端哈希，用于同步状态校验/审计追溯。"""
    _ensure_tables_once(db)
    product = db.get(Product, product_id)
    mirror = db.get(ConsumerProduct, product_id)
    source_hash = compute_source_hash(db, product) if product is not None else None
    target_hash = compute_target_hash(db, product_id) if mirror is not None else None
    consistent = bool(source_hash and target_hash and source_hash == target_hash)
    latest_log = db.execute(
        select(ProductSyncLog)
        .where(ProductSyncLog.product_id == product_id)
        .order_by(ProductSyncLog.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return {
        "product_id": str(product_id),
        "source_exists": product is not None,
        "consumer_exists": mirror is not None,
        "consistent": consistent,
        "source_hash": source_hash,
        "consumer_hash": target_hash,
        "consumer_synced_at": mirror.synced_at if mirror is not None else None,
        "last_log_id": latest_log.id if latest_log is not None else None,
        "last_log_status": latest_log.status if latest_log is not None else None,
    }


def backfill_consumer_catalog(
    db: Session, trigger_type: str = "startup_reconcile"
) -> list[SyncOutcome]:
    """启动时对齐存量已审核商品与消费者镜像（仅处理缺失/漂移项）。"""
    outcomes: list[SyncOutcome] = []
    products = list(
        db.execute(select(Product).where(Product.status == "approved")).scalars()
    )
    repaired = False
    for product in products:
        # 存量修复：历史审核通过但从未主动下架的商品，补齐为已上架，
        # 否则消费者端「全部商品」看不到（仅在无 delist 记录时修复）。
        if not product.is_listed:
            delisted = db.execute(
                select(ProductAuditRecord.id)
                .where(
                    ProductAuditRecord.product_id == product.id,
                    ProductAuditRecord.action == "delist",
                )
                .limit(1)
            ).first()
            if delisted is None:
                product.is_listed = True
                repaired = True
    if repaired:
        db.flush()
    for product in products:
        try:
            report = consistency_report(db, product.id)
        except Exception:  # noqa: BLE001 - 单条异常不应阻断启动
            report = {"consistent": False}
        if report.get("consistent"):
            continue
        outcomes.append(sync_product(db, product.id, None, trigger_type))
    return outcomes


def delete_consumer_product(db: Session, product_id: uuid.UUID) -> None:
    """源商品被物理删除时清理镜像（当前仅草稿可删，保留接口以防未来策略变化）。"""
    db.execute(
        delete(ConsumerProductSku).where(ConsumerProductSku.product_id == product_id)
    )
    db.execute(
        delete(ConsumerProductImage).where(ConsumerProductImage.product_id == product_id)
    )
    mirror = db.get(ConsumerProduct, product_id)
    if mirror is not None:
        db.delete(mirror)
    db.flush()
