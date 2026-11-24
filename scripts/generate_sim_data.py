# -*- coding: utf-8 -*-
"""
碳惠陇原 · 仿真测试数据生成器（幂等）
=====================================
按后端真实模型字段写入 SQLite，覆盖全业务状态，供消费者端/管理端测试。

特性：
- 所有生成实体带 'SIM' 标记（公司名/标题/单号前缀），重复运行会先清理旧的仿真数据，幂等。
- 只追加仿真数据，不改动 seed 原有的 2 商家/7 商品/分类等基础数据。
- 字段严格按 schema；UUID 主键；日期格式与后端一致。
- 覆盖：4 商家状态、6 商品状态、7 订单状态、3 退款状态、3 公告状态、3 消费者、积分/通知。

用法：python generate_sim_data.py
"""
import sqlite3
import uuid
import json
import sys
from datetime import datetime, timedelta

BACKEND_DIR = r"C:\Users\85046\Desktop\碳惠陇原统一后端-tanhui-backend\tanhui-backend"
sys.path.insert(0, BACKEND_DIR)
from app.core.security import hash_password  # 与后端一致的 Argon2

DB = BACKEND_DIR + r"\tanhui_dev.db"
conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys=OFF")
cur = conn.cursor()

NOW = datetime.now()
def iso(dt): return dt.strftime("%Y-%m-%d %H:%M:%S.%f")
def ago(days, hour=10, minute=0):
    d = NOW - timedelta(days=days)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)
def uid(): return str(uuid.uuid4())
def money(v): return f"{v:.2f}"

ADMIN = cur.execute("SELECT id FROM users WHERE email='admin@tanhui.example.com'").fetchone()[0]
BUYER = cur.execute("SELECT id FROM users WHERE email='buyer@tanhui.example.com'").fetchone()[0]
STORE1 = cur.execute("SELECT id FROM stores WHERE name='陇原甄选旗舰店'").fetchone()[0]
STORE2 = cur.execute("SELECT id FROM stores WHERE name='百合源生态农场'").fetchone()[0]
MERCHANT1 = cur.execute("SELECT id FROM merchants WHERE company_name='甘肃陇原甄选农业科技有限公司'").fetchone()[0]
CAT_FRUIT = cur.execute("SELECT id FROM categories WHERE name='水果生鲜' AND parent_id IS NULL").fetchone()[0]
CAT_GRAIN = cur.execute("SELECT id FROM categories WHERE name='粮油杂粮' AND parent_id IS NULL").fetchone()[0]
CAT_HERB = cur.execute("SELECT id FROM categories WHERE name='中药材' AND parent_id IS NULL").fetchone()[0]
CAT_SPECIAL = cur.execute("SELECT id FROM categories WHERE name='甘肃特产' AND parent_id IS NULL").fetchone()[0]
IMG_APPLE = "/uploads/demo/products/jingning-apple-1.webp"
IMG_POTATO = "/uploads/demo/products/dingxi-potato-1.webp"
IMG_GOJI = "/uploads/demo/products/gansu-goji-1.webp"
IMG_LILY = "/uploads/demo/products/lanzhou-lily-1.webp"

# ---------------- 幂等：先清理旧仿真数据 ----------------
def in_clause(ids):
    return ",".join("?" * len(ids)) if ids else "''"

def cleanup():
    sim_mids = [r[0] for r in cur.execute("SELECT id FROM merchants WHERE company_name LIKE ?", ("SIM-%",))]
    sim_stores = [r[0] for r in cur.execute(f"SELECT id FROM stores WHERE name LIKE ? OR merchant_id IN ({in_clause(sim_mids)})", ["SIM-%"] + sim_mids)]
    sim_pids = [r[0] for r in cur.execute(f"SELECT id FROM products WHERE title LIKE ? OR store_id IN ({in_clause(sim_stores)})", ["SIM-%"] + sim_stores)]
    sim_skus = [r[0] for r in cur.execute(f"SELECT id FROM product_skus WHERE product_id IN ({in_clause(sim_pids)})", sim_pids)]
    sim_oids = [r[0] for r in cur.execute("SELECT id FROM orders WHERE order_no LIKE ?", ("SIM-%",))]
    sim_solds = [r[0] for r in cur.execute(f"SELECT id FROM store_orders WHERE order_id IN ({in_clause(sim_oids)})", sim_oids)]
    sim_ships = [r[0] for r in cur.execute(f"SELECT id FROM shipments WHERE store_order_id IN ({in_clause(sim_solds)})", sim_solds)]
    sim_pays = [r[0] for r in cur.execute(f"SELECT id FROM payment_orders WHERE order_id IN ({in_clause(sim_oids)})", sim_oids)]
    sim_refunds = [r[0] for r in cur.execute(f"SELECT id FROM refunds WHERE refund_no LIKE ? OR order_id IN ({in_clause(sim_oids)})", ["SIM-%"] + sim_oids)]
    sim_uids = [r[0] for r in cur.execute("SELECT id FROM users WHERE email LIKE ?", ("sim%@tanhui.example.com",))]
    deletes = [
        ("shipment_tracks", "shipment_id", sim_ships),
        ("shipments", "id", sim_ships),
        ("refunds", "id", sim_refunds),
        ("payment_transactions", "payment_order_id", sim_pays),
        ("payment_orders", "id", sim_pays),
        ("order_items", "store_order_id", sim_solds),
        ("order_status_logs", "order_id", sim_oids),
        ("store_orders", "id", sim_solds),
        ("orders", "id", sim_oids),
        ("inventory_reservations", "sku_id", sim_skus),
        ("inventories", "sku_id", sim_skus),
        ("product_images", "product_id", sim_pids),
        ("product_green_profiles", "product_id", sim_pids),
        ("product_audit_records", "product_id", sim_pids),
        ("product_skus", "id", sim_skus),
        ("products", "id", sim_pids),
        ("store_members", "store_id", sim_stores),
        ("merchant_users", "merchant_id", sim_mids),
        ("stores", "id", sim_stores),
        ("merchants", "id", sim_mids),
        ("notifications", "user_id", sim_uids),
        ("point_accounts", "user_id", sim_uids),
        ("user_addresses", "user_id", sim_uids),
        ("user_profiles", "user_id", sim_uids),
        ("user_roles", "user_id", sim_uids),
        ("users", "id", sim_uids),
        ("cms_announcements", "id", [r[0] for r in cur.execute("SELECT id FROM cms_announcements WHERE title LIKE 'SIM-%'")]),
    ]
    for tbl, col, ids in deletes:
        if ids:
            cur.execute(f"DELETE FROM {tbl} WHERE {col} IN ({','.join('?'*len(ids))})", ids)
    conn.commit()
    return len(sim_mids), len(sim_pids), len(sim_oids)

removed = cleanup()
print(f"cleaned old sim data: merchants={removed[0]} products={removed[1]} orders={removed[2]}")

# ---------------- 1. 消费者用户 ----------------
def add_user(email, nickname, phone, days_ago):
    user_id = uid(); now = iso(ago(days_ago))
    pwd = hash_password("Passw0rd!123")
    cur.execute("""INSERT INTO users(email,phone,password_hash,is_active,is_email_verified,mfa_enabled,mfa_secret,banned_until,ban_reason,id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (email, phone, pwd, 1, 1, 0, None, None, None, user_id, now, now))
    cur.execute("""INSERT INTO user_profiles(user_id,nickname,avatar_url,gender,birthday,bio,id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (user_id, nickname, None, None, None, "仿真测试用户", uid(), now, now))
    cur.execute("""INSERT INTO user_addresses(user_id,receiver,phone,province,city,district,detail,is_default,id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (user_id, nickname, phone, "甘肃省", "兰州市", "城关区", f"仿真路 {user_id[:4]} 号", 1, uid(), now, now))
    cur.execute("""INSERT INTO point_accounts(user_id,balance,id,created_at,updated_at) VALUES(?,?,?,?,?)""",
                (user_id, 500 + (days_ago % 5) * 100, uid(), now, now))
    return user_id

# 注意：hash_password 需要后端路径在 sys.path，改为在脚本顶部插入路径

BUYERS = [
    add_user("simbuyer1@tanhui.example.com", "仿真买家·赵一", "13900001001", 30),
    add_user("simbuyer2@tanhui.example.com", "仿真买家·钱二", "13900001002", 20),
    add_user("simbuyer3@tanhui.example.com", "仿真买家·孙三", "13900001003", 10),
]
print("created buyers:", len(BUYERS))

# ---------------- 2. 商家（4 种状态）----------------
def add_merchant(company, store_name, status, region, days_ago, reject_reason=None):
    mid = uid(); now = iso(ago(days_ago))
    reviewed = now if status in ("approved", "frozen", "rejected") else None
    cur.execute("""INSERT INTO merchants(status,company_name,license_no,license_url,legal_person,contact_phone,region,initial_store_name,reject_reason,reviewed_by,reviewed_at,id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (status, f"SIM-{company}", f"SIMLIC{uid()[:12]}", None, f"法人{company[:2]}", f"13800{uid()[:6]}",
                 region, store_name, reject_reason, ADMIN if reviewed else None, reviewed, mid, now, now))
    sid = None
    if status in ("approved", "frozen"):
        sid = uid()
        cur.execute("""INSERT INTO stores(merchant_id,name,logo_url,description,region,status,is_closed_temporarily,id,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (mid, f"SIM-{store_name}", None, f"{company} 产地直供（仿真数据）", region,
                     "active" if status == "approved" else "suspended", 0, sid, now, now))
    return mid, sid

MERCHANTS = {}
MERCHANTS['pending1'] = add_merchant("静宁苹果合作社", "静宁苹果直供店", "pending_review", "甘肃省平凉市静宁县", 2)
MERCHANTS['pending2'] = add_merchant("民勤蜜瓜种植大户", "民勤瓜果优选", "pending_review", "甘肃省武威市民勤县", 1)
MERCHANTS['rejected'] = add_merchant("临泽小枣合作社", "临泽枣园", "rejected", "甘肃省张掖市临泽县", 5, "资质图片不清晰，请重新提交")
MERCHANTS['frozen'] = add_merchant("岷县当归合作社", "岷县当归专营店", "frozen", "甘肃省定西市岷县", 15)
MERCHANTS['approved'] = add_merchant("天水花牛苹果合作社", "SIM-花牛苹果旗舰店", "approved", "甘肃省天水市麦积区", 25)
print("created merchants:", len(MERCHANTS))

# 已通过商家的店铺可用于上架商品；额外挂一个 owner 用户便于商家端可见
SIM_STORE = MERCHANTS['approved'][1]
cur.execute("""INSERT INTO merchant_users(merchant_id,user_id,role,id,created_at,updated_at) VALUES(?,?,?,?,?,?)""",
            (MERCHANTS['approved'][0], BUYERS[0], 'owner', uid(), iso(ago(25)), iso(ago(25))))
cur.execute("""INSERT INTO store_members(store_id,user_id,role,invited_by,status,id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)""",
            (SIM_STORE, BUYERS[0], 'owner', None, 'active', uid(), iso(ago(25)), iso(ago(25))))

# ---------------- 3. 商品（6 种状态）----------------
def add_product(title, status, listed, store_id, category_id, price, img, days_ago, audit_reason=None, origin="甘肃省", review="approved"):
    pid = uid(); now = iso(ago(days_ago))
    cur.execute("""INSERT INTO products(store_id,category_id,aid_project_id,title,subtitle,description,status,is_listed,audit_reason,audited_by,audited_at,id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (store_id, category_id, None, f"SIM-{title}", "仿真商品 · 测试用",
                 f"{title}，仿真测试数据，用于功能验证。", status, 1 if listed else 0, audit_reason,
                 ADMIN if status == "approved" else None, now if status == "approved" else None,
                 pid, now, now))
    sku_id = uid()
    cur.execute("""INSERT INTO product_skus(product_id,spec,code,price,is_active,id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)""",
                (pid, "5kg 标准装", f"SIMSKU{uid()[:6]}", money(price), 1, sku_id, now, now))
    cur.execute("""INSERT INTO inventories(sku_id,quantity_total,quantity_reserved,id,created_at,updated_at) VALUES(?,?,?,?,?,?)""",
                (sku_id, 500, 0, uid(), now, now))
    cur.execute("""INSERT INTO product_images(product_id,url,sort,id,created_at,updated_at) VALUES(?,?,?,?,?,?)""",
                (pid, img, 0, uid(), now, now))
    cur.execute("""INSERT INTO product_green_profiles(product_id,origin,planting_mode,certifications,description,status,reviewed_by,id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (pid, origin, "绿色生态种植", json.dumps(["绿色食品认证"], ensure_ascii=False),
                 f"{origin} 产地直供，仿真绿色资料。", review, ADMIN if review == "approved" else None, uid(), now, now))
    cur.execute("""INSERT INTO product_audit_records(product_id,action,reason,operator_id,created_at,id) VALUES(?,?,?,?,?,?)""",
                (pid, "submit", None, None, now, uid()))
    return pid, sku_id

PRODUCTS = {}
PRODUCTS['draft1'] = add_product("草稿·天水花牛苹果", "draft", False, SIM_STORE, CAT_FRUIT, 49.9, IMG_APPLE, 1, origin="甘肃省天水市麦积区", review="draft")
PRODUCTS['draft2'] = add_product("草稿·陇南橄榄油", "draft", False, SIM_STORE, CAT_SPECIAL, 88.0, IMG_LILY, 2, origin="甘肃省陇南市武都区", review="draft")
PRODUCTS['review1'] = add_product("待审·静宁红富士礼盒", "pending_review", False, SIM_STORE, CAT_FRUIT, 99.0, IMG_APPLE, 1, origin="甘肃省平凉市静宁县", review="pending")
PRODUCTS['review2'] = add_product("待审·定西马铃薯精选", "pending_review", False, STORE1, CAT_GRAIN, 39.9, IMG_POTATO, 1, origin="甘肃省定西市", review="pending")
PRODUCTS['review3'] = add_product("待审·甘肃枸杞礼盒", "pending_review", False, SIM_STORE, CAT_HERB, 128.0, IMG_GOJI, 2, origin="甘肃省白银市景泰县", review="pending")
PRODUCTS['rejected'] = add_product("驳回·临泽小枣", "rejected", False, STORE2, CAT_SPECIAL, 45.0, IMG_LILY, 4, audit_reason="产地证明不清晰", origin="甘肃省张掖市临泽县", review="rejected")
PRODUCTS['onsale1'] = add_product("在售·静宁红富士苹果", "approved", True, STORE1, CAT_FRUIT, 59.9, IMG_APPLE, 30)
PRODUCTS['onsale2'] = add_product("在售·定西马铃薯", "approved", True, STORE1, CAT_GRAIN, 29.9, IMG_POTATO, 28)
PRODUCTS['onsale3'] = add_product("在售·兰州百合", "approved", True, STORE2, CAT_SPECIAL, 69.9, IMG_LILY, 26)
PRODUCTS['offline'] = add_product("下架·甘肃枸杞", "approved", False, STORE2, CAT_HERB, 89.9, IMG_GOJI, 20)
print("created products:", len(PRODUCTS))

# ---------------- 4. 订单（7 种状态）----------------
def add_order(buyer, status, days_ago, product_sku, store_id, qty=1, unit_price=59.9, refund_status=None, shipped=False, completed=False):
    oid = uid(); now = iso(ago(days_ago, 9, 30))
    items_total = money(unit_price * qty)
    shipping = "0.00" if items_total >= "99" else "8.00"
    pay = money(float(items_total) + float(shipping))
    paid_at = now if status not in ("pending_payment", "cancelled") else None
    completed_at = iso(ago(days_ago - 2)) if completed or status == "completed" else None
    cancelled_at = now if status == "cancelled" else None
    order_no = f"SIM-TH{now[:10].replace('-','')}{uid()[:6].upper()}"
    cur.execute("""INSERT INTO orders(order_no,user_id,status,receiver_name,receiver_phone,address,items_total,shipping_fee,points_deduct,points_used,pay_amount,currency,remark,cancel_reason,paid_at,completed_at,cancelled_at,idempotency_key,idempotency_payload_hash,id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (order_no, buyer, status, f"仿真买家{uid()[:3]}", "13900001001", "甘肃省兰州市城关区仿真路 1 号",
                 items_total, shipping, "0.00", 0, pay, "CNY", "仿真订单 · 测试用",
                 "仿真取消" if status == "cancelled" else None, paid_at, completed_at, cancelled_at,
                 f"sim-{uid()[:8]}", uid(), oid, now, now))
    soid = uid()
    so_no = f"SIM-TS{now[:10].replace('-','')}{uid()[:6].upper()}"
    cur.execute("""INSERT INTO store_orders(store_order_no,order_id,store_id,status,items_total,shipping_fee,pay_amount,refund_amount,shipped_at,completed_at,id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (so_no, oid, store_id, status, items_total, shipping, pay, "0.00",
                 iso(ago(days_ago - 1)) if shipped or status in ("shipped", "completed", "refunding", "refunded") else None,
                 completed_at, soid, now, now))
    pid = cur.execute("SELECT product_id FROM product_skus WHERE id=?", (product_sku,)).fetchone()[0]
    ptitle = cur.execute("SELECT title FROM products WHERE id=?", (pid,)).fetchone()[0]
    cur.execute("""INSERT INTO order_items(store_order_id,sku_id,product_id,title,spec,image_url,unit_price,quantity,subtotal,id)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (soid, product_sku, pid, ptitle, "5kg 标准装", IMG_APPLE, money(unit_price), qty, items_total, uid()))
    cur.execute("""INSERT INTO order_status_logs(order_id,store_order_id,from_status,to_status,action,operator_id,note,created_at,id)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (oid, None, None, "pending_payment", "create", None, order_no, now, uid()))
    if paid_at:
        cur.execute("""INSERT INTO order_status_logs(order_id,store_order_id,from_status,to_status,action,operator_id,note,created_at,id)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (oid, None, "pending_payment", "paid", "payment_success", None, order_no, paid_at, uid()))
    # 支付单
    if status != "pending_payment":
        cur.execute("""INSERT INTO payment_orders(pay_no,order_id,amount,currency,status,provider,trade_no,expires_at,paid_at,id,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (f"SIM-PAY{uid()[:8].upper()}", oid, pay, "CNY", "success", "mock_sandbox",
                     f"SIMTRADE{uid()[:8].upper()}", iso(ago(days_ago) + timedelta(minutes=30)), paid_at, uid(), now, now))
    # 物流
    if shipped or status in ("shipped", "completed", "refunding", "refunded"):
        ship_id = uid(); ship_at = iso(ago(days_ago - 1))
        cur.execute("""INSERT INTO shipments(store_order_id,carrier,tracking_no,status,shipped_by,shipped_at,delivered_at,id,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (soid, "顺丰速运", f"SIMSF{uid()[:10].upper()}", "delivered" if completed_at else "shipped",
                     BUYERS[0], ship_at, completed_at, ship_id, ship_at, ship_at))
        cur.execute("""INSERT INTO shipment_tracks(shipment_id,status,description,occurred_at,created_at,id) VALUES(?,?,?,?,?,?)""",
                    (ship_id, "shipped", "顺丰速运 已揽收（仿真）", ship_at, ship_at, uid()))
    return oid, soid, pay

ORDERS = {}
ORDERS['pending_payment'] = add_order(BUYERS[0], "pending_payment", 0, PRODUCTS['onsale1'][1], STORE1, 1, 59.9)
ORDERS['paid'] = add_order(BUYERS[0], "paid", 1, PRODUCTS['onsale2'][1], STORE1, 2, 29.9)
ORDERS['shipped'] = add_order(BUYERS[1], "shipped", 3, PRODUCTS['onsale3'][1], STORE2, 1, 69.9, shipped=True)
ORDERS['completed'] = add_order(BUYERS[1], "completed", 10, PRODUCTS['onsale1'][1], STORE1, 1, 59.9, shipped=True, completed=True)
ORDERS['cancelled'] = add_order(BUYERS[2], "cancelled", 5, PRODUCTS['onsale2'][1], STORE1, 1, 29.9)
ORDERS['refunding'] = add_order(BUYERS[0], "refunding", 2, PRODUCTS['onsale3'][1], STORE2, 1, 69.9, shipped=True)
ORDERS['refunded'] = add_order(BUYERS[2], "refunded", 8, PRODUCTS['onsale1'][1], STORE1, 1, 59.9, shipped=True, completed=True)
print("created orders:", len(ORDERS))

# ---------------- 5. 退款（requested / refunded / rejected）----------------
def add_refund(order_key, status, days_ago, reason, result_note=None):
    oid, soid, pay = ORDERS[order_key]
    rid = uid(); now = iso(ago(days_ago))
    handled = now if status != "requested" else None
    cur.execute("""INSERT INTO refunds(refund_no,order_id,store_order_id,amount,reason,status,requested_by,handled_by,handled_at,result_note,id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"SIM-RF{uid()[:8].upper()}", oid, soid, pay, reason, status, BUYERS[0],
                 ADMIN if handled else None, handled, result_note, rid, now, now))
    return rid

add_refund('refunding', 'requested', 1, "仿真：商品与描述不符，申请退款")
add_refund('refunded', 'refunded', 6, "仿真：坏果申请退款", "核实符合退款条件，已原路退回（仿真）")
# 已驳回退款：另造一单
oid, soid, pay = ORDERS['completed']
add_refund('completed', 'rejected', 7, "仿真：无理由退货", "证据不足，维持原处理（仿真）")
print("created refunds: 3")

# ---------------- 6. 公告（published / draft / offline）----------------
for title, status, days_ago in [
    ("SIM-平台公告：仿真数据说明", "published", 1),
    ("SIM-公告草稿：待发布内容", "draft", 2),
    ("SIM-已下线公告：旧规则", "offline", 10),
]:
    now = iso(ago(days_ago))
    cur.execute("""INSERT INTO cms_announcements(title,content,status,published_at,start_at,end_at,id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (title, f"{title}。本公告为仿真测试数据，用于验证公告发布流程。", status,
                 now if status == "published" else None, None, None, uid(), now, now))
print("created announcements: 3")

# ---------------- 7. 通知（给消费者）----------------
for b in BUYERS:
    now = iso(ago(1))
    cur.execute("""INSERT INTO notifications(user_id,type,title,content,read_at,id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)""",
                (b, "system", "SIM-仿真测试通知", "这是用于测试的仿真通知消息。", None, uid(), now, now))
print("created notifications: 3")

conn.commit()
print("\n=== DONE: 仿真数据生成完成 ===")
for t in ['users','merchants','stores','products','orders','store_orders','refunds','cms_announcements']:
    print(f"{t}: {cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
conn.close()
