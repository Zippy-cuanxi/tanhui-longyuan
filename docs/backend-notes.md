# 后端衔接说明与已知差异

## 1. 已修复的后端契约缺陷

### 1.1 助农项目 500

- 文件：`碳惠陇原统一后端-tanhui-backend/tanhui-backend/app/modules/aid/router.py`
- 现象：`GET /api/v1/aid/projects` 返回 `INTERNAL_ERROR` 500。
- 原因：`ProjectOut.goal_amount/raised_amount` 声明为 `str`，ORM 实际为 `Decimal`，Pydantic 校验失败。
- 修复：改为 `MoneyOut`（`Annotated[Decimal, PlainSerializer(lambda v: f"{v:.2f}", return_type=str)]`），与 OpenAPI 的“金额字符串两位小数”一致。
- 影响：仅修复序列化，不改变路径、字段、枚举或业务规则。
- **注意**：修复已写入当前 8000 运行目录；`--reload` 会加载。

### 1.2 商品详情缺少列表字段

- `GET /api/v1/products/{id}` 返回的 `ProductDetailOut` 未回填 `min_price`、`cover_url`（列表接口 `_decorate` 才回填）。
- 前端处理：
  - 首页 CMS `product_grid` 改用 `GET /products?page_size=100` 按 ID 映射，获取 `min_price/cover_url`。
  - 详情页价格使用 `skus[].price`，图片使用 `images[]`，不受影响。
- 建议后端后续在 `get_product` 中补齐这两个字段，前端已做兼容。

### 1.3 价格排序未生效

- 文件：`碳惠陇原统一后端-tanhui-backend/tanhui-backend/app/modules/catalog/service.py`
- 现象：`GET /products?sort=price_asc` 返回顺序仍按 `created_at DESC`。
- 原因：基础查询先 `.order_by(Product.created_at.desc())`，随后 `.order_by(min_price.asc())` 只是追加排序，默认排序仍然优先。
- 修复：先不追加默认排序；`price_asc` 时只按最低 SKU 价升序，否则按 `created_at DESC`。
- 影响：只修复排序实现，不改变 `sort` 枚举或接口字段。

## 2. CMS 裸 JSON

`/api/v1/client/config/{page_key}`、`/api/v1/client/notices`、`/api/v1/client/banners` 直接返回业务 JSON，不包 `{code,message,data,request_id}`。前端 `requestRaw` 单独处理；ETag 缓存与 304 回退在 `getCmsConfig` 中实现。

## 3. 当前联调后端（8000）

- 实际运行目录：`C:\Users\85046\Desktop\碳惠陇原统一后端-tanhui-backend\tanhui-backend`。
- 已备份其开发库：`tanhui_dev.db.bak-20261124`。
- 已应用助农 `MoneyOut` 修复与 `price_asc` 排序修复，并把演示素材复制到其 `uploads/demo`。
- 已用 `TANHUI_BACKEND_DIR` 指向该目录执行 `scripts/seed_demo.py`，写入设计稿数据。
- 前端 `.env.local` 指向 `http://127.0.0.1:8000`；8001 仅作为备用实例。

## 4. 演示数据

`scripts/seed_demo.py` 通过后端 ORM 写入（不改后端接口代码），支持 `TANHUI_BACKEND_DIR` 指定任意后端目录；当前运行环境请使用 8000 目录：

- 分类：水果生鲜、粮油杂粮、特色食品、中药材、甘肃特产、文创礼品（保留后端原有分类，前端按设计稿白名单展示）。
- 商品：静宁红富士苹果、定西马铃薯、民勤蜜瓜、甘肃枸杞、临泽小枣、兰州百合、岷县当归；含 SKU、库存、4 张详情图、绿色资料（approved，不虚构认证）。
- CMS 首页：Banner + 精选 4 商品；`rich_text` 置为 disabled，避免设计稿外模块。
- 助农项目：4 个（含目标/已筹/封面），全部 `published`，封面为裁切后的卡片图。
- 买家：演示地址 1 条、绿色积分 1280 初始 + 订单完成奖励；3 笔示例订单（待付款/待支付/已完成）。
- 脚本幂等：按标题/规格/分类/页面 key 查找更新；示例订单仅在订单数为 0 时创建。

所有商品、价格、产地、项目、金额均为演示数据，不代表真实商品、认证或募捐。

## 5. 业务策略

运费、佣金、积分获取/抵扣比例、退款时限、结算周期等均以后端仿真配置与 `docs/pending-decisions.md` 为准。前端不写死比例；结算页只展示服务端预览结果，并注明“以平台配置为准”。

## 6. 账号

- 消费者：`buyer@tanhui.example.com / Passw0rd!123`。
- 商家：`merchant1@tanhui.example.com / Passw0rd!123`（消费者端不使用）。
- 管理员：后端 seed 随机生成且仅打印一次；本轮不做管理端，未使用。

## 7. 接口使用边界

- 消费者端未调用任何 `/admin/*` 或 `/merchant/*` 接口。
- 未使用未实现的业务能力（评价、优惠券、收藏、发票、客服、真实物流推送）。
- 支付、退款、物流、兑换均明确标注 Mock/仿真。
