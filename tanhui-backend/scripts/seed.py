"""初始化仿真数据【SIMULATION DATA】。

用法：
    python -m scripts.seed              # 幂等写入全部仿真数据
    python -m scripts.seed --reset      # 危险：清空后重建（仅开发库）

【仿真声明】本脚本所有数据均为开发/演示用仿真数据：
- 管理员密码为随机生成并打印到控制台（不落盘）；
- 商品价格/库存/助农项目/合作社信息均为虚构；
- 修改数据请直接编辑下方 DATA 区。
"""
import argparse
import secrets
import uuid
from decimal import Decimal

from app.core.base import Base
from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.modules.catalog import service as catalog_service
from app.modules.catalog.schemas import ProductCreateIn, SkuIn
from app.modules.cms import service as cms_service
from app.modules.cms.schemas import PageCreateIn, SectionIn
from app.modules.merchants import service as merchant_service
from app.modules.merchants.schemas import MerchantApplyIn
from app.modules.points import service as points_service
from app.modules.rbac import service as rbac_service
from app.modules.users import service as users_service
from app.modules.users.models import User

# ==================== DATA 区（仿真数据，可自由修改）====================

ADMIN_ACCOUNTS = [
    # (邮箱, 角色)
    ("admin@tanhui.example.com", "super_admin"),      # 超级管理员
    ("ops@tanhui.example.com", "ops_admin"),          # 运营管理员
    ("auditor@tanhui.example.com", "product_auditor"),  # 商品审核员
    ("finance@tanhui.example.com", "finance_admin"),  # 财务管理员
    ("cs@tanhui.example.com", "cs_admin"),            # 客服管理员
]

CONSUMER_ACCOUNT = ("buyer@tanhui.example.com", "Passw0rd!123")  # 【仿真账号】演示用

CATEGORIES = [
    ("新鲜果蔬", None), ("粮油副食", None), ("中药材", None),
    ("牛羊肉禽", None), ("乳品烘焙", None),
    ("静宁苹果", "新鲜果蔬"), ("定西马铃薯", "粮油副食"), ("兰州百合", "新鲜果蔬"),
]

MERCHANTS = [
    {
        "email": "merchant1@tanhui.example.com",
        "password": "Passw0rd!123",  # 【仿真账号】
        "apply": MerchantApplyIn(
            company_name="甘肃陇原甄选农业科技有限公司",  # 【仿真执照信息】
            license_no="91620000MA000SIM01",
            legal_person="王陇原",
            contact_phone="13800000001",
            region="甘肃省兰州市",
            store_name="陇原甄选旗舰店",
        ),
        "products": [
            ("静宁红富士苹果", "高原红富士·脆甜多汁", "新鲜果蔬", "静宁苹果", [
                SkuIn(spec="5kg 精选装", price=Decimal("68.00"), initial_stock=500),
                SkuIn(spec="10kg 家庭装", price=Decimal("128.00"), initial_stock=200),
            ]),
            ("定西黄心马铃薯", "沙壤土豆·粉糯香甜", "粮油副食", "定西马铃薯", [
                SkuIn(spec="10kg 装", price=Decimal("39.90"), initial_stock=800),
            ]),
        ],
    },
    {
        "email": "merchant2@tanhui.example.com",
        "password": "Passw0rd!123",  # 【仿真账号】
        "apply": MerchantApplyIn(
            company_name="兰州百合源生态农业合作社",  # 【仿真执照信息】
            license_no="91620000MA000SIM02",
            legal_person="李百合",
            contact_phone="13800000002",
            region="甘肃省兰州市七里河区",
            store_name="百合源生态农场",
        ),
        "products": [
            ("兰州九年生百合干", "无硫熏·肉厚甜糯", "粮油副食", "兰州百合", [
                SkuIn(spec="250g 特级", price=Decimal("88.00"), initial_stock=300),
                SkuIn(spec="500g 特级", price=Decimal("158.00"), initial_stock=150),
            ]),
        ],
    },
]

COOPERATIVES = [
    ("定西薯都合作社", "甘肃省定西市", "马铃薯标准化种植合作社（仿真）"),
    ("陇南橄榄油合作社", "甘肃省陇南市", "油橄榄种植与初加工（仿真）"),
]

AID_PROJECTS = [
    # (合作社, 标题, 描述, 目标金额)
    ("定西薯都合作社", "定西马铃薯助农增收计划",
     "帮助定西薯农对接平台销售渠道，提升收购价（仿真项目）", Decimal("100000.00")),
    ("陇南橄榄油合作社", "陇南油橄榄产业帮扶",
     "支持油橄榄低产园改造，带动农户增收（仿真项目）", Decimal("50000.00")),
]

# ==================== 种子逻辑 ====================


def seed(print_passwords: bool = True) -> None:
    # 开发便利：空库时自动建表（正式部署请使用 alembic upgrade head）
    import app.modules.models_registry  # noqa: F401  注册全部模型
    from sqlalchemy import inspect

    if not inspect(engine).has_table("users"):
        Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        # 1) RBAC 角色/权限 + 积分规则版本（幂等）
        rbac_service.seed_role_data(db)
        points_service.ensure_rules_seeded(db)

        # 2) 管理员账号（密码随机生成，仅打印）
        created_admins = []
        for email, role_code in ADMIN_ACCOUNTS:
            exists = db.query(User).filter(User.email == email).one_or_none()
            if exists:
                continue
            pwd = secrets.token_urlsafe(12)
            user = users_service.register_user(db, email, pwd, None)
            rbac_service.assign_role(db, user.id, role_code, None)
            created_admins.append((email, role_code, pwd))

        # 3) 演示消费者
        consumer_email, consumer_pwd = CONSUMER_ACCOUNT
        if db.query(User).filter(User.email == consumer_email).one_or_none() is None:
            users_service.register_user(db, consumer_email, consumer_pwd, "体验用户")

        # 4) 分类
        cat_ids = {}
        for name, pname in CATEGORIES:
            cat = catalog_service.create_category(
                db, name, cat_ids.get(pname) if pname else None
            )
            cat_ids[name] = cat.id

        # 5) 商家入驻（自动审核通过）+ 商品（自动审核通过并上架）
        seeded_product_ids = []
        for m in MERCHANTS:
            if db.query(User).filter(User.email == m["email"]).one_or_none() is None:
                owner = users_service.register_user(db, m["email"], m["password"], None)
                merchant = merchant_service.apply(db, owner.id, m["apply"])
                merchant_service.review(db, merchant.id, "approve", None, None)
                for title, subtitle, cat, sub, skus in m["products"]:
                    payload = ProductCreateIn(
                        title=title, subtitle=subtitle,
                        description=f"{title}——甘肃产地直发【仿真商品描述】",
                        category_id=cat_ids.get(sub) or cat_ids.get(cat),
                        skus=skus,
                    )
                    # 入驻审核时已创建默认店铺，取商家下第一家店
                    from app.modules.stores.models import Store
                    from sqlalchemy import select
                    store = db.execute(
                        select(Store).where(Store.merchant_id == merchant.id)
                    ).scalars().first()
                    product = catalog_service.create_product(db, store.id, payload)
                    seeded_product_ids.append(str(product.id))
                    catalog_service.submit_for_review(db, store.id, product.id)
                    catalog_service.audit_product(db, product.id, "approve", None, None)
                    catalog_service.toggle_listing(db, store.id, product.id, True)

        # 6) 助农合作社 + 项目（自动发布）
        from app.modules.aid.models import AidProject, Cooperative
        coop_ids = {}
        for name, region, desc in COOPERATIVES:
            if db.query(Cooperative).filter(Cooperative.name == name).one_or_none() is None:
                c = Cooperative(name=name, region=region, description=desc)
                db.add(c)
                db.flush()
            coop_ids[name] = db.query(Cooperative).filter(Cooperative.name == name).one().id
        for coop, title, desc, goal in AID_PROJECTS:
            if db.query(AidProject).filter(AidProject.title == title).one_or_none() is None:
                db.add(AidProject(
                    cooperative_id=coop_ids[coop], title=title,
                    description=desc, goal_amount=goal,
                    status="published",
                ))

        # 7) CMS 首页（草稿 → 发布，含白名单组件）
        if db.query(cms_service.CmsPage).filter(
            cms_service.CmsPage.page_key == "home"
        ).one_or_none() is None:
            admin_id = db.query(User.id).filter(
                User.email == ADMIN_ACCOUNTS[0][0]
            ).scalar()
            page = cms_service.create_page(
                db, PageCreateIn(page_key="home", title="首页配置"), admin_id
            )
            cms_service.replace_section(db, page.id, None, SectionIn(
                section_type="banner",
                config={"title": "碳惠陇原·甘肃好物", "image_url": "https://example.com/banner.jpg",
                        "link_type": "internal", "link_url": "/products"}))
            cms_service.replace_section(db, page.id, None, SectionIn(
                section_type="product_grid",
                config={"title": "产地直供", "product_ids": seeded_product_ids[:6]}))
            # 助农项目卡片需真实 project_id，此处用富文本占位【仿真】
            cms_service.replace_section(db, page.id, None, SectionIn(
                section_type="rich_text",
                config={"title": "助农在行动", "text": "携手甘肃合作社，让好产出山（仿真文案）"}))
            cms_service.publish(db, page.id, admin_id)

        # 8) 公告
        from app.modules.cms.models import CmsAnnouncement
        if db.query(CmsAnnouncement).count() == 0:
            a = CmsAnnouncement(
                title="平台试运营公告", status="published",
                content="碳惠陇原平台当前为沙箱试运营阶段，所有交易与支付均为仿真数据。",
            )
            a.published_at = __import__("app.core.base", fromlist=["utcnow"]).utcnow()
            db.add(a)

        db.commit()
        print("✅ 仿真数据初始化完成（幂等）")
        if created_admins and print_passwords:
            print("\n=== 新建管理员账号（密码仅本次显示，请立即保存）===")
            for email, role, pwd in created_admins:
                print(f"  {role:16s} {email}  密码: {pwd}")
            print("=== 演示消费者: %s / %s ===" % CONSUMER_ACCOUNT)
            print("=== 演示商家: merchant1@tanhui.example.com / Passw0rd!123 ===")
    finally:
        db.close()


def reset() -> None:
    """清空重建（仅开发库）。"""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("⚠️  已清空并重建全部表")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="清空后重建（危险，仅开发）")
    args = parser.parse_args()
    if args.reset:
        reset()
    seed()
