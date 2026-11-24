"""模块注册中心：统一收集各域 router 并挂载到 /api/v1。

模块清单（20 个域，符合任务书要求）：
auth, users, rbac, merchants, stores, catalog, inventory, cart, orders,
payments, logistics, points, cms, aid, green, finance, notifications,
audit, admin, merchant_portal(经各域 merchant_router 聚合实现)
"""
from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    from app.core.config import settings

    from app.modules.admin.router import router as admin_router
    from app.modules.aid.router import admin_router as aid_admin_router
    from app.modules.aid.router import consumer_router as aid_router
    from app.modules.audit.admin_router import router as audit_router
    from app.modules.auth.router import router as auth_router
    from app.modules.cart.router import router as cart_router
    from app.modules.catalog.admin_router import router as catalog_admin_router
    from app.modules.catalog.merchant_router import router as catalog_merchant_router
    from app.modules.catalog.router import router as catalog_router
    from app.modules.users.router import router as users_router
    from app.modules.cms.router import admin_router as cms_admin_router
    from app.modules.cms.router import client_router as cms_client_router
    from app.modules.finance.admin_router import router as finance_admin_router
    from app.modules.finance.merchant_router import router as finance_merchant_router
    from app.modules.green.router import admin_router as green_admin_router
    from app.modules.green.router import consumer_router as green_router
    from app.modules.green.router import merchant_router as green_merchant_router
    from app.modules.inventory.merchant_router import router as inventory_merchant_router
    from app.modules.logistics.router import router as logistics_router
    from app.modules.merchants.admin_router import router as merchants_admin_router
    from app.modules.merchants.router import router as merchants_router
    from app.modules.notifications.router import router as notifications_router
    from app.modules.orders.admin_router import router as orders_admin_router
    from app.modules.orders.merchant_router import router as orders_merchant_router
    from app.modules.orders.router import router as orders_router
    from app.modules.payments.router import router as payments_router
    from app.modules.points.admin_router import router as points_admin_router
    from app.modules.points.router import router as points_router
    from app.modules.rbac.admin_router import router as rbac_admin_router
    from app.modules.stores.admin_router import router as stores_admin_router
    from app.modules.stores.merchant_router import router as stores_merchant_router

    prefix = settings.API_V1_PREFIX
    for r in (
        # 消费者端
        auth_router,
        users_router,
        catalog_router,
        cart_router,
        orders_router,
        payments_router,
        points_router,
        logistics_router,
        notifications_router,
        aid_router,
        green_router,
        cms_client_router,
        # 商家端
        merchants_router,
        stores_merchant_router,
        catalog_merchant_router,
        orders_merchant_router,
        finance_merchant_router,
        green_merchant_router,
        inventory_merchant_router,
        # 管理端
        admin_router,
        audit_router,
        rbac_admin_router,
        merchants_admin_router,
        stores_admin_router,
        catalog_admin_router,
        orders_admin_router,
        finance_admin_router,
        points_admin_router,
        aid_admin_router,
        green_admin_router,
        cms_admin_router,
    ):
        app.include_router(r, prefix=prefix)
