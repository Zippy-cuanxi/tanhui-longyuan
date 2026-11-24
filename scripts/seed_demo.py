"""补齐碳惠陇原消费者商城的演示数据（仅数据，不改后端代码）。

运行方式（后端虚拟环境）：
    cd C:/Users/85046/Desktop/tanhui-backend
    ../tanhui-backend-fixed/.venv/Scripts/python.exe "C:/Users/85046/Desktop/碳惠陇原/scripts/seed_demo.py"

说明：
- 所有商品名称/价格/描述/产地均为演示数据，不对应真实商品或认证；
- 通过后端 ORM 直接写入，走的是与后端一致的数据模型；
- 商品状态置为 approved + is_listed，便于消费者端联调；
- 脚本幂等：按商品标题、规格、分类名、页面 key 查找后更新。
"""
from __future__ import annotations

import os
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT.parent
BACKEND = Path(
    os.environ.get("TANHUI_BACKEND_DIR", str(DESKTOP / "tanhui-backend"))
).resolve()

sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.core.base import utcnow  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.modules.aid.models import AidProject, Cooperative  # noqa: E402
from app.modules.catalog.models import (  # noqa: E402
    Category,
    Product,
    ProductAuditRecord,
    ProductImage,
    ProductSku,
)
from app.modules.cms import service as cms_service  # noqa: E402
from app.modules.cms.models import CmsBanner, CmsPage, CmsSection  # noqa: E402
from app.modules.cms.schemas import PageCreateIn, SectionIn  # noqa: E402
from app.modules.green.models import ProductGreenProfile  # noqa: E402
from app.modules.inventory.models import Inventory  # noqa: E402
from app.modules.orders.models import Order, StoreOrder  # noqa: E402
from app.modules.orders.schemas import CreateOrderIn, OrderItemIn  # noqa: E402
from app.modules.points.models import PointAccount, PointTransaction  # noqa: E402
from app.modules.stores.models import Store, StoreMember  # noqa: E402
from app.modules.users.models import User, UserAddress  # noqa: E402

from app.modules.orders import service as order_service  # noqa: E402
from app.modules.payments import service as payment_service  # noqa: E402

BUYER_EMAIL = "buyer@tanhui.example.com"
MERCHANT1_EMAIL = "merchant1@tanhui.example.com"
ADMIN_EMAIL = "admin@tanhui.example.com"

CATEGORY_DEFS = [
    ("水果生鲜", "fruit", 10),
    ("粮油杂粮", "grains", 20),
    ("特色食品", "food", 30),
    ("中药材", "food", 40),
    ("甘肃特产", "culture", 50),
    ("文创礼品", "culture", 60),
]

PRODUCT_DEFS = [
    {
        "slug": "jingning-apple",
        "titles": ["静宁红富士苹果", "静宁苹果"],
        "title": "静宁红富士苹果",
        "subtitle": "高原红富士 · 脆甜多汁",
        "category": "水果生鲜",
        "store": "store1",
        "description": "产自甘肃静宁的高原果园，日照充足、昼夜温差大。果肉脆甜多汁，果香清亮，适合鲜食与家庭分享。下单后由产地仓发货。",
        "skus": [("5kg 精选装", "59.90", 500), ("10kg 家庭装", "108.00", 200)],
        "green": ("甘肃省平凉市静宁县", "高原梯田果园种植", "静宁高原果园种植，产地直发。"),
        "aid_title": "静宁苹果产业提质计划",
        "minutes_ago": 6,
    },
    {
        "slug": "dingxi-potato",
        "titles": ["定西黄心马铃薯", "定西马铃薯"],
        "title": "定西马铃薯",
        "subtitle": "沙壤土豆 · 粉糯香甜",
        "category": "粮油杂粮",
        "store": "store1",
        "description": "定西沙壤土种植，薯形饱满、口感粉糯。适合蒸煮、炖菜，也可用于制作马铃薯主食。",
        "skus": [("10kg 装", "29.90", 800), ("20kg 家庭装", "49.90", 300)],
        "green": ("甘肃省定西市", "旱作梯田种植", "定西旱作农业区种植，沙壤土质，粉糯口感。"),
        "aid_title": "定西马铃薯助农增收计划",
        "minutes_ago": 12,
    },
    {
        "slug": "minqin-melon",
        "titles": ["民勤蜜瓜"],
        "title": "民勤蜜瓜",
        "subtitle": "绿洲沙地 · 清甜多汁",
        "category": "水果生鲜",
        "store": "store1",
        "description": "民勤绿洲沙地种植，光照充足、昼夜温差大。果肉橙黄，清甜多汁，成熟采摘后发货。",
        "skus": [("5kg 装（2-3 个）", "39.90", 300), ("10kg 装（4-6 个）", "69.90", 150)],
        "green": ("甘肃省武威市民勤县", "绿洲沙地种植", "民勤绿洲沙地种植，光照充足。"),
        "aid_title": "民勤蜜瓜节水种植帮扶",
        "minutes_ago": 18,
    },
    {
        "slug": "gansu-goji",
        "titles": ["甘肃枸杞"],
        "title": "甘肃枸杞",
        "subtitle": "果粒饱满 · 色泽自然",
        "category": "中药材",
        "store": "store1",
        "description": "甘肃产区枸杞，果粒饱满、色泽自然。可用于泡水、煮粥与煲汤，建议密封避光保存。",
        "skus": [("500g 装", "89.90", 400), ("1kg 装", "169.00", 220)],
        "green": ("甘肃省白银市景泰县", "盐碱地生态种植", "甘肃产区枸杞，自然晾晒，果粒饱满。"),
        "aid_title": None,
        "minutes_ago": 24,
    },
    {
        "slug": "linze-jujube",
        "titles": ["临泽小枣"],
        "title": "临泽小枣",
        "subtitle": "绿洲枣园 · 枣香浓郁",
        "category": "甘肃特产",
        "store": "store1",
        "description": "临泽绿洲枣园种植，自然晾晒。枣香浓郁、肉质厚实，适合直接食用或煮粥。",
        "skus": [("1kg 装", "49.90", 350), ("2kg 装", "89.90", 180)],
        "green": ("甘肃省张掖市临泽县", "绿洲枣园种植", "临泽绿洲枣园种植，自然晾晒。"),
        "aid_title": None,
        "minutes_ago": 30,
    },
    {
        "slug": "lanzhou-lily",
        "titles": ["兰州九年生百合干", "兰州百合"],
        "title": "兰州百合",
        "subtitle": "瓣大肉厚 · 清甜粉糯",
        "category": "特色食品",
        "store": "store2",
        "description": "兰州七里河区百合，瓣大肉厚、口感清甜。适合清炒、煲汤与制作甜品。",
        "skus": [("500g 特级", "69.90", 300), ("1kg 特级", "129.00", 150)],
        "green": ("甘肃省兰州市七里河区", "山地百合种植", "兰州七里河区百合种植，瓣大肉厚。"),
        "aid_title": None,
        "minutes_ago": 36,
    },
    {
        "slug": "minxian-danggui",
        "titles": ["岷县当归"],
        "title": "岷县当归",
        "subtitle": "根条完整 · 香气浓郁",
        "category": "中药材",
        "store": "store1",
        "description": "岷县高寒阴湿区种植当归，根条完整、香气浓郁。常用于煲汤与药膳，建议干燥保存。",
        "skus": [("500g 装", "79.90", 260), ("1kg 装", "149.00", 120)],
        "green": ("甘肃省定西市岷县", "高寒阴湿区种植", "岷县高寒阴湿区种植，根条完整。"),
        "aid_title": None,
        "minutes_ago": 42,
    },
]


def ensure_category(db, name: str, icon_slug: str, sort: int) -> Category:
    category = (
        db.query(Category)
        .filter(Category.name == name, Category.parent_id.is_(None))
        .one_or_none()
    )
    if category is None:
        category = Category(name=name, icon_url=f"/uploads/demo/categories/{icon_slug}.webp", sort=sort)
        db.add(category)
        db.flush()
    category.icon_url = f"/uploads/demo/categories/{icon_slug}.webp"
    category.sort = sort
    category.is_active = True
    return category


def ensure_cooperative(db, name: str, region: str, description: str) -> Cooperative:
    coop = db.query(Cooperative).filter(Cooperative.name == name).one_or_none()
    if coop is None:
        coop = Cooperative(name=name, region=region, description=description)
        db.add(coop)
        db.flush()
    return coop


def ensure_project(db, coop: Cooperative, title: str, description: str, goal: str, raised: str, cover: str) -> AidProject:
    project = db.query(AidProject).filter(AidProject.title == title).one_or_none()
    if project is None:
        project = AidProject(cooperative_id=coop.id, title=title)
        db.add(project)
        db.flush()
    project.cooperative_id = coop.id
    project.description = description
    project.goal_amount = Decimal(goal)
    project.raised_amount = Decimal(raised)
    project.cover_url = cover
    project.status = "published"
    project.published_at = project.published_at or utcnow()
    return project


def ensure_product(db, definition: dict, category: Category, store: Store, aid_project: AidProject | None) -> Product:
    product = None
    for title in definition["titles"]:
        product = db.query(Product).filter(Product.title == title).one_or_none()
        if product is not None:
            break
    if product is None:
        product = Product(store_id=store.id, title=definition["title"])
        db.add(product)
        db.flush()
    product.store_id = store.id
    product.category_id = category.id
    product.aid_project_id = aid_project.id if aid_project else None
    product.title = definition["title"]
    product.subtitle = definition["subtitle"]
    product.description = definition["description"]
    product.status = "approved"
    product.is_listed = True
    product.audit_reason = None
    product.audited_at = utcnow()
    product.created_at = utcnow() - timedelta(minutes=definition["minutes_ago"])
    product.updated_at = utcnow()

    # SKU：旧规格停用，目标规格启用/创建
    db.query(ProductSku).filter(ProductSku.product_id == product.id).update(
        {ProductSku.is_active: False}, synchronize_session=False
    )
    db.flush()
    for spec, price, stock in definition["skus"]:
        sku = (
            db.query(ProductSku)
            .filter(ProductSku.product_id == product.id, ProductSku.spec == spec)
            .one_or_none()
        )
        if sku is None:
            sku = ProductSku(product_id=product.id, spec=spec, price=Decimal(price))
            db.add(sku)
            db.flush()
        sku.price = Decimal(price)
        sku.is_active = True
        inventory = db.query(Inventory).filter(Inventory.sku_id == sku.id).one_or_none()
        if inventory is None:
            inventory = Inventory(sku_id=sku.id, quantity_total=stock, quantity_reserved=0)
            db.add(inventory)
        else:
            inventory.quantity_total = max(stock, inventory.quantity_reserved)
        db.flush()

    # 图片：使用设计素材生成的四张详情图
    db.query(ProductImage).filter(ProductImage.product_id == product.id).delete(
        synchronize_session=False
    )
    for index in range(1, 5):
        db.add(
            ProductImage(
                product_id=product.id,
                url=f"/uploads/demo/products/{definition['slug']}-{index}.webp",
                sort=index - 1,
            )
        )

    if not db.query(ProductAuditRecord).filter(ProductAuditRecord.product_id == product.id).first():
        db.add(ProductAuditRecord(product_id=product.id, action="approve", reason="演示数据初始化"))
    db.flush()
    return product


def ensure_green(db, product: Product, green: tuple[str, str, str], reviewer_id) -> None:
    origin, planting_mode, description = green
    profile = (
        db.query(ProductGreenProfile)
        .filter(ProductGreenProfile.product_id == product.id)
        .one_or_none()
    )
    if profile is None:
        profile = ProductGreenProfile(product_id=product.id)
        db.add(profile)
    profile.origin = origin
    profile.planting_mode = planting_mode
    profile.certifications = None  # 不虚构认证
    profile.description = description
    profile.status = "approved"
    profile.reviewed_by = reviewer_id
    db.flush()


def ensure_cms(db, featured_ids: list, admin_id) -> None:
    page = db.query(CmsPage).filter(CmsPage.page_key == "home").one_or_none()
    if page is None:
        page = cms_service.create_page(
            db, PageCreateIn(page_key="home", title="首页配置"), admin_id
        )
    db.query(CmsSection).filter(CmsSection.page_id == page.id).delete(synchronize_session=False)
    db.flush()
    cms_service.replace_section(
        db,
        page.id,
        None,
        SectionIn(
            section_type="banner",
            sort=10,
            config={
                "title": "来自陇原的自然好物",
                "image_url": "/uploads/demo/banners/home-hero.webp",
                "link_type": "internal",
                "link_url": "/products",
            },
        ),
    )
    cms_service.replace_section(
        db,
        page.id,
        None,
        SectionIn(
            section_type="product_grid",
            sort=20,
            config={"title": "精选推荐", "product_ids": featured_ids},
        ),
    )
    cms_service.replace_section(
        db,
        page.id,
        None,
        SectionIn(
            section_type="rich_text",
            sort=30,
            enabled=False,
            config={"title": "绿色生态", "text": "来自陇原的自然好物，产地直供。"},
        ),
    )
    cms_service.publish(db, page.id, admin_id)

    banner_defs = [
        ("首页主视觉", "home-hero.webp", "/products", 10),
        ("商品页横幅", "catalog-hero.webp", "/products", 20),
        ("绿色消费专区", "green-zone.webp", "/green", 30),
    ]
    for title, filename, link, sort in banner_defs:
        banner = db.query(CmsBanner).filter(CmsBanner.title == title).one_or_none()
        if banner is None:
            banner = CmsBanner(title=title, image_url="", link_type="internal", link_url=link)
            db.add(banner)
        banner.image_url = f"/uploads/demo/banners/{filename}"
        banner.link_type = "internal"
        banner.link_url = link
        banner.sort = sort
        banner.enabled = True
    db.flush()


def ensure_points_and_address(db, buyer: User) -> UserAddress:
    account = db.query(PointAccount).filter(PointAccount.user_id == buyer.id).one_or_none()
    if account is None:
        account = PointAccount(user_id=buyer.id, balance=0)
        db.add(account)
        db.flush()
    has_demo_init = (
        db.query(PointTransaction)
        .filter(PointTransaction.user_id == buyer.id, PointTransaction.source_type == "demo_init")
        .first()
    )
    if account.balance == 0 and not has_demo_init:
        account.balance = 1280
        db.add(
            PointTransaction(
                account_id=account.id,
                user_id=buyer.id,
                type="adjust",
                amount=1280,
                balance_after=1280,
                source_type="demo_init",
                note="演示环境初始绿色积分（非真实发放）",
            )
        )
        db.flush()

    address = db.query(UserAddress).filter(UserAddress.user_id == buyer.id).first()
    if address is None:
        address = UserAddress(
            user_id=buyer.id,
            receiver="王小明",
            phone="13800001234",
            province="甘肃省",
            city="兰州市",
            district="城关区",
            detail="张掖路街道 88 号 2 单元 501",
            is_default=True,
        )
        db.add(address)
        db.flush()
    return address


def seed_orders(db, buyer: User, address: UserAddress, products: dict[str, Product], merchant1: User) -> None:
    existing = db.query(Order).filter(Order.user_id == buyer.id).count()
    if existing:
        print(f"orders: 已存在 {existing} 笔，跳过示例订单")
        return

    try:
        def sku_of(slug: str):
            product = products[slug]
            sku = (
                db.query(ProductSku)
                .filter(ProductSku.product_id == product.id, ProductSku.is_active.is_(True))
                .order_by(ProductSku.price.asc())
                .first()
            )
            return sku

        def create(slug: str, quantity: int, remark: str) -> Order:
            sku = sku_of(slug)
            payload = CreateOrderIn(
                address_id=address.id,
                items=[
                    OrderItemIn(
                        sku_id=sku.id,
                        quantity=quantity,
                        expected_unit_price=f"{sku.price:.2f}",
                    )
                ],
                use_points=False,
                remark=remark,
                idempotency_key=None,
            )
            order = order_service.create_order(db, buyer.id, payload)
            db.commit()
            return db.get(Order, order.id)

        def pay(order: Order) -> None:
            payment = payment_service.get_or_create_active_payment(db, order)
            db.commit()
            payment_service.mock_pay(db, buyer.id, payment.pay_no)

        # 1) 已完成订单
        completed = create("jingning-apple", 1, "演示订单：已完成")
        pay(completed)
        completed = db.get(Order, completed.id)
        store_order = db.query(StoreOrder).filter(StoreOrder.order_id == completed.id).first()
        order_service.ship(
            db,
            store_order.store_id,
            store_order.id,
            "顺丰速运",
            "SF1234567890",
            merchant1.id,
        )
        db.commit()
        order_service.confirm_receipt(db, buyer.id, completed.id)
        db.commit()

        # 2) 已支付待发货
        paid = create("dingxi-potato", 2, "演示订单：已支付待发货")
        pay(paid)

        # 3) 待支付
        create("minqin-melon", 1, "演示订单：待支付")
        print("orders: 已创建 3 笔示例订单")
    except Exception as exc:  # 示例订单失败不阻断主数据
        db.rollback()
        print(f"orders: 示例订单创建失败（不影响商品数据）：{exc}")


def main() -> None:
    db = SessionLocal()
    try:
        buyer = db.query(User).filter(User.email == BUYER_EMAIL).one()
        merchant1 = db.query(User).filter(User.email == MERCHANT1_EMAIL).one()
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).one_or_none()

        store1 = (
            db.query(Store)
            .join(StoreMember, StoreMember.store_id == Store.id)
            .filter(StoreMember.user_id == merchant1.id)
            .first()
        )
        store2 = db.query(Store).filter(Store.name == "百合源生态农场").first()
        if store1 is None or store2 is None:
            raise SystemExit("未找到演示店铺，请先运行后端 scripts.seed")

        categories = {}
        for name, icon, sort in CATEGORY_DEFS:
            categories[name] = ensure_category(db, name, icon, sort)
        db.flush()

        coop1 = ensure_cooperative(db, "静宁果业合作社", "甘肃省平凉市静宁县", "静宁苹果种植与产地直供合作社（演示）")
        coop2 = ensure_cooperative(db, "民勤绿洲合作社", "甘肃省武威市民勤县", "民勤蜜瓜种植与节水农业合作社（演示）")
        project_map = {
            "定西马铃薯助农增收计划": ensure_project(
                db,
                ensure_cooperative(db, "定西薯都合作社", "甘肃省定西市", "马铃薯标准化种植合作社（演示）"),
                "定西马铃薯助农增收计划",
                "帮助定西薯农对接平台销售渠道，提升收购价（演示项目）",
                "100000.00",
                "32600.00",
                "/uploads/demo/banners/aid-card-farm.webp",
            ),
            "陇南油橄榄产业帮扶": ensure_project(
                db,
                ensure_cooperative(db, "陇南橄榄油合作社", "甘肃省陇南市", "油橄榄种植与初加工（演示）"),
                "陇南油橄榄产业帮扶",
                "支持油橄榄低产园改造，带动农户增收（演示项目）",
                "50000.00",
                "12800.00",
                "/uploads/demo/banners/aid-card-farm.webp",
            ),
            "静宁苹果产业提质计划": ensure_project(
                db,
                coop1,
                "静宁苹果产业提质计划",
                "支持静宁果园标准化管理与产地冷链建设，帮助好果出山（演示项目）",
                "80000.00",
                "18600.00",
                "/uploads/demo/banners/aid-card-farmer.webp",
            ),
            "民勤蜜瓜节水种植帮扶": ensure_project(
                db,
                coop2,
                "民勤蜜瓜节水种植帮扶",
                "推广绿洲节水种植技术，帮助民勤瓜农稳定增收（演示项目）",
                "60000.00",
                "9200.00",
                "/uploads/demo/banners/aid-card-farm.webp",
            ),
        }
        db.flush()

        products = {}
        for definition in PRODUCT_DEFS:
            store = store1 if definition["store"] == "store1" else store2
            project = project_map.get(definition["aid_title"]) if definition["aid_title"] else None
            product = ensure_product(
                db, definition, categories[definition["category"]], store, project
            )
            ensure_green(db, product, definition["green"], admin.id if admin else None)
            products[definition["slug"]] = product
        db.flush()

        featured = [
            products["jingning-apple"].id,
            products["dingxi-potato"].id,
            products["minqin-melon"].id,
            products["gansu-goji"].id,
        ]
        ensure_cms(db, featured, admin.id if admin else None)
        address = ensure_points_and_address(db, buyer)
        db.commit()

        seed_orders(db, buyer, address, products, merchant1)
        db.commit()

        print("seed_demo: 完成")
        print(f"  分类 {len(categories)} 个，商品 {len(products)} 个")
        print(f"  店铺：{store1.name} / {store2.name}")
        print(f"  买家：{BUYER_EMAIL}")
        print(f"  示例地址：{address.province}{address.city}{address.district}{address.detail}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
