# -*- coding: utf-8 -*-
"""从后端 SQLite 导出静态演示数据快照到 public/demo-data.json。
供 GitHub Pages 静态部署时前端请求层读取，无需后端即可展示与交互。"""
import sqlite3
import json
import os
from datetime import datetime

BACKEND_DIR = r"C:\Users\85046\Desktop\碳惠陇原统一后端-tanhui-backend\tanhui-backend"
DB = BACKEND_DIR + r"\tanhui_dev.db"
OUT = r"C:\Users\85046\Desktop\碳惠陇原\public\demo-data.json"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def rows(sql, params=()):
    return [dict(r) for r in cur.execute(sql, params)]

def num(v):
    return float(v) if v is not None else 0.0

def static_url(url):
    """后端 /uploads/... 路径重写为静态站点 public/ 下已有的 /images/... 路径。"""
    if not url:
        return url
    u = str(url)
    if '/uploads/demo/products/' in u:
        u = u.replace('/uploads/demo/products/', '/images/products/')
    elif '/uploads/demo/banners/' in u:
        u = u.replace('/uploads/demo/banners/', '/images/banners/')
    elif '/uploads/demo/categories/' in u:
        # 分类图标在静态站点里位于 public/assets/categories/
        u = u.replace('/uploads/demo/categories/', '/assets/categories/')
    elif '/uploads/' in u:
        u = u.replace('/uploads/', '/images/')
    return u

# --- 分类 ---
categories = rows("SELECT id,name,parent_id,icon_url,sort,is_active FROM categories WHERE is_active=1 ORDER BY sort")

# --- 商家/店铺（仅 approved）---
stores = rows("""SELECT s.id,s.name,s.description,s.region,s.logo_url,s.merchant_id,
                        m.company_name
                 FROM stores s JOIN merchants m ON m.id=s.merchant_id
                 WHERE s.status='active' AND m.status='approved'""")

# --- 商品（消费者可见：approved + listed）---
products = []
for p in rows("""SELECT id,store_id,category_id,title,subtitle,description,status,created_at
                 FROM products WHERE status='approved' AND is_listed=1 ORDER BY created_at DESC"""):
    item = dict(p)
    item['skus'] = rows("SELECT id,spec,code,price,is_active FROM product_skus WHERE product_id=? AND is_active=1", (p['id'],))
    item['images'] = rows("SELECT id,url,sort FROM product_images WHERE product_id=? ORDER BY sort", (p['id'],))
    for img in item['images']:
        img['url'] = static_url(img['url'])
    green = rows("SELECT origin,planting_mode,description,status FROM product_green_profiles WHERE product_id=?", (p['id'],))
    item['green'] = green[0] if green else None
    # 管理端字段：min_price / cover / store_name / sales
    prices = [num(s['price']) for s in item['skus']]
    item['min_price'] = min(prices) if prices else 0.0
    item['cover_url'] = static_url(item['images'][0]['url']) if item['images'] else None
    store = next((s for s in stores if s['id'] == p['store_id']), None)
    item['store_name'] = store['name'] if store else ''
    products.append(item)

# --- 公告（已发布）---
notices = rows("""SELECT id,title,content,status,published_at FROM cms_announcements
                  WHERE status='published' ORDER BY published_at DESC""")

# --- Banner ---
try:
    banners = rows("SELECT id,title,image_url,link_url,sort,status FROM cms_banners WHERE status='active' ORDER BY sort")
except Exception:
    banners = []

# --- 助农项目 ---
aid_projects = rows("""SELECT id,title,cover_url,description,goal_amount,raised_amount,status,published_at
                       FROM aid_projects WHERE status='published' ORDER BY published_at DESC""")

# --- 积分规则/兑换目录（模拟）---
point_catalog = [
    {"id": "p1", "name": "5元无门槛券", "points": 500, "stock": 100},
    {"id": "p2", "name": "10元农产品券", "points": 900, "stock": 50},
    {"id": "p3", "name": "定制帆布袋", "points": 1200, "stock": 30}
]

# --- 消费者用户（供 demo 登录）---
users = rows("""SELECT u.id,u.email,u.phone,p.nickname FROM users u
                LEFT JOIN user_profiles p ON p.user_id=u.id
                WHERE u.email LIKE 'buyer%' OR u.email LIKE 'simbuyer%'""")
addresses = rows("""SELECT a.id,a.user_id,a.receiver,a.phone,a.province,a.city,a.district,a.detail,a.is_default
                    FROM user_addresses a""")
point_accounts = rows("SELECT user_id,balance FROM point_accounts")

# --- 订单（供 demo 登录后查看）---
orders = []
for o in rows("SELECT * FROM orders ORDER BY created_at DESC"):
    item = dict(o)
    item['store_orders'] = []
    for so in rows("SELECT * FROM store_orders WHERE order_id=?", (o['id'],)):
        so_item = dict(so)
        so_item['items'] = rows("SELECT * FROM order_items WHERE store_order_id=?", (so['id'],))
        so_item['shipments'] = rows("SELECT * FROM shipments WHERE store_order_id=?", (so['id'],))
        item['store_orders'].append(so_item)
    orders.append(item)
refunds = rows("SELECT * FROM refunds ORDER BY created_at DESC")

# --- CMS 配置 ---
try:
    cms_config = {r['key']: r['value'] for r in rows("SELECT key,value FROM system_settings")}
except Exception:
    cms_config = {}

snapshot = {
    "generated_at": datetime.now().isoformat(),
    "source": "tanhui_dev.db (含仿真测试数据)",
    "categories": categories,
    "stores": stores,
    "products": products,
    "notices": notices,
    "banners": banners,
    "aid_projects": aid_projects,
    "point_catalog": point_catalog,
    "users": users,
    "addresses": addresses,
    "point_accounts": point_accounts,
    "orders": orders,
    "refunds": refunds,
    "cms_config": cms_config,
}

# --- 统一重写剩余 URL 字段（banners / aid / stores / categories / order_items）---
# 必须在写盘之前执行，否则快照里仍残留后端 /uploads/... 路径，静态站点会 404
URL_FIELDS = ('image_url', 'cover_url', 'icon_url', 'logo_url', 'url')
def rewrite_urls(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in URL_FIELDS and isinstance(v, str):
                obj[k] = static_url(v)
            else:
                rewrite_urls(v)
    elif isinstance(obj, list):
        for item in obj:
            rewrite_urls(item)
rewrite_urls(snapshot)

# --- 校验：快照里引用的 /images/... 必须在 public/ 下真实存在 ---
PUBLIC_DIR = r"C:\Users\85046\Desktop\碳惠陇原\public"
missing = []

def check_assets(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in URL_FIELDS and isinstance(v, str):
                if v.startswith('/images/') or v.startswith('/assets/'):
                    local = os.path.join(PUBLIC_DIR, v.lstrip('/').replace('/', os.sep))
                    if not os.path.exists(local):
                        missing.append(v)
            else:
                check_assets(v)
    elif isinstance(obj, list):
        for item in obj:
            check_assets(item)

check_assets(snapshot)
if missing:
    for m in sorted(set(missing)):
        print(f"[warn] 快照引用的本地文件不存在: {m}")
else:
    print("[ok] 快照引用的图片均存在")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(snapshot, f, ensure_ascii=False, indent=2)

size = os.path.getsize(OUT)
print(f"snapshot written: {OUT} ({size/1024:.1f} KB)")
print(f"products={len(products)} notices={len(notices)} categories={len(categories)} orders={len(orders)} aid={len(aid_projects)}")
conn.close()
