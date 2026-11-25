"""验证审核通过 + 消费者同步的事务原子性。

场景：管理员审核通过时，消费者端同步失败 → 整个审核事务必须回滚，
商品仍保持 pending_review，且不会留下 consumer_products 镜像。

运行（在 tanhui-backend 目录）：python scripts/verify_audit_atomicity.py
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.modules.catalog import service, sync_service  # noqa: E402
from app.modules.catalog.models import Category, Product, ProductAuditRecord, ProductSku  # noqa: E402
from app.modules.catalog.sync_models import ConsumerProduct  # noqa: E402
from app.modules.stores.models import Store  # noqa: E402
from app.modules.users.models import User  # noqa: E402

failures: list[str] = []
passed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed
    if condition:
        passed += 1
        print(f"PASS  {name}")
    else:
        failures.append(f"{name}{('：' + detail) if detail else ''}")
        print(f"FAIL  {name}{('：' + detail) if detail else ''}")


def main() -> None:
    db = SessionLocal()
    store = db.query(Store).first()
    category = db.query(Category).first()
    admin = db.query(User).filter(User.email == "admin@tanhui.example.com").first()
    if store is None or admin is None:
        raise SystemExit("缺少基础演示数据（店铺或管理员），请先执行 seed")

    product = Product(
        store_id=store.id,
        category_id=category.id if category else None,
        title=f"事务原子性测试-{uuid.uuid4().hex[:6]}",
        subtitle="同步失败应回滚审核",
        description="自动化测试商品",
        status="pending_review",
    )
    db.add(product)
    db.flush()
    sku = ProductSku(product_id=product.id, spec="500g", price="9.90")
    db.add(sku)
    db.add(
        ProductAuditRecord(
            product_id=product.id,
            action="submit",
            operator_id=None,
        )
    )
    db.commit()
    product_id = product.id

    original_sync = sync_service.sync_product

    def fake_failed_sync(*args, **kwargs):  # noqa: ANN002, ANN003
        target = args[1] if len(args) > 1 else kwargs.get("product_id")
        return sync_service.SyncOutcome(
            product_id=target,
            success=False,
            attempts=3,
            max_attempts=3,
            duration_ms=1,
            error="模拟消费者端同步失败",
            message="商品审核已生效，但同步消费者端失败",
        )

    sync_service.sync_product = fake_failed_sync  # type: ignore[assignment]
    try:
        try:
            service.audit_product(db, product_id, "approve", None, admin.id)
            raised = False
        except AppError:
            raised = True
        check("同步失败时审核接口抛错", raised)
    finally:
        sync_service.sync_product = original_sync  # type: ignore[assignment]
        db.rollback()

    verify = SessionLocal()
    try:
        saved = verify.get(Product, product_id)
        mirror = verify.get(ConsumerProduct, product_id)
        check("同步失败后商品仍为待审核", saved is not None and saved.status == "pending_review")
        check("同步失败后未产生消费者镜像", mirror is None)
        check(
            "同步失败后未写入审核通过记录",
            verify.query(ProductAuditRecord)
            .filter(
                ProductAuditRecord.product_id == product_id,
                ProductAuditRecord.action == "approve",
            )
            .count()
            == 0,
        )
    finally:
        # 清理测试数据
        verify.query(ProductAuditRecord).filter(
            ProductAuditRecord.product_id == product_id
        ).delete()
        verify.query(ProductSku).filter(ProductSku.product_id == product_id).delete()
        verify.query(Product).filter(Product.id == product_id).delete()
        verify.commit()
        verify.close()
    db.close()

    print(f"\n结果：{passed} 项通过，{len(failures)} 项失败")
    if failures:
        print("\n".join(f" - {item}" for item in failures))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
