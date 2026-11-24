# 页面 → API → DTO 对照表

> 契约来源：`tanhui-backend/docs/openapi.yaml`（134 接口）与后端实际实现。
> 所有金额字段均为服务端两位小数字符串；前端只格式化展示，不做权威计算。

| 页面 / 路由 | 调用接口 | 关键 DTO / 字段 | 说明 |
|---|---|---|---|
| 首页 `/` | `GET /client/config/home` | `CmsConfig { page, sections[] }`；`section_type/config/sort/enabled` | 裸 JSON（不包 `ApiResponse`）；ETag 缓存；未知组件安全跳过 |
| 首页 精选 | `GET /products?page_size=100` | `PageData<Product>`：`id/title/subtitle/min_price/cover_url/store_name/aid_project_id` | CMS `product_grid.product_ids` 按 ID 映射；避免 `GET /products/{id}` 未回填 `min_price/cover_url` 的缺口 |
| 首页 分类 | `GET /categories` | `Category[]`：`id/name/parent_id/icon_url/sort` | 前端筛选设计稿 6 个一级分类 |
| 全部商品 `/products` | `GET /products?category_id&store_id&keyword&sort&page&page_size` | `PageData<Product>`；`Pagination {page,page_size,total,total_pages}` | `sort` 仅 `created_desc/price_asc`；销量排序后端无字段，置灰；顶部 5 分类 + 左产地 + 右网格 |
| 全部商品 分类 | `GET /categories` | `Category[]` | 顶部 5 个分类胶囊与后端分类 ID 映射 |
| 全部商品 甘肃产地 | `GET /green/products/{id}` | `GreenDetail.profile.origin` | 左栏产地名；无绿色资料回退店铺名，不新增字段 |
| 全部商品 精选好评 | 无评价接口 | 本地 Mock：商品 ID 稳定哈希生成 4.6–5.0 演示分 | 页面显示「Mock 演示」「演示好评」，不代表真实评价 |
| 商品详情 `/products/:id` | `GET /products/{id}` | `ProductDetail`：`skus[]/images[]/description/store_name/status` | 仅审核通过且上架可见，否则 404 |
| 商品详情 绿色 | `GET /green/products/{id}` | `{ profile, carbon_assessment }`；`profile.origin/planting_mode/status`；`carbon.verified` | 404 → 隐藏绿色资料；未核验必须标注 |
| 商品详情 关联 | `GET /products?store_id=...&page_size=8` | `PageData<Product>` | 同店关联商品；排除当前商品 |
| 商品详情 助农 | `GET /aid/projects/{id}` | `AidProject` | 商品有 `aid_project_id` 时展示项目链接 |
| 购物车 `/cart` | `GET /cart` | `Cart { items[], total_quantity, checked_subtotal }`；`CartItem.current_price/stock_available` | 价格/库存实时服务端 |
| 购物车 改量/勾选 | `PATCH /cart/items/{id}` | `{ quantity?, checked? }` → `CartItem` | 单条更新后刷新整车 |
| 购物车 删除 | `DELETE /cart/items/{id}` | `null` | 二次确认 |
| 确认订单 `/checkout` | `GET /users/me/addresses` | `Address[]` | 默认地址优先 |
| 确认订单 预览 | `POST /orders/preview` | `Preview { items_total, shipping_fee, points_deduct, points_used, pay_amount, stores[] }` | 服务端计价；积分开关触发重算 |
| 确认订单 提交 | `POST /orders` | `CreateOrderIn { address_id, items[], use_points, remark, idempotency_key }` → `Order` | `expected_unit_price` 来自预览；幂等键 `crypto.randomUUID()` |
| 确认订单 地址 | `POST /users/me/addresses` | `AddressIn` → `Address` | 结算页内新增地址 |
| 确认订单 积分 | `GET /points/account` | `{ balance }` | 显示可用绿豆 |
| 订单支付 `/pay/:orderId` | `GET /orders/{id}` | `Order`：`status/pay_amount/store_orders[]` | 待支付才发起支付 |
| 订单支付 发起 | `POST /payments/{order_id}/init` | `Payment { pay_no, amount, status, expires_at, pay_url }` | 返回支付单 |
| 订单支付 沙箱 | `POST /payments/mock/pay` | `{ pay_no }` → `{ return_code, result }` | 明确 Mock 沙箱；成功后刷新订单 |
| 登录 `/login` | `POST /auth/login` | `LoginIn { email,password,mfa_code? }` → `TokenPair { access_token, refresh_token, expires_in }` | `MFA_REQUIRED` 时显示验证码输入 |
| 注册 `/register` | `POST /auth/register` | `RegisterIn { email,password,nickname? }` → `User` | 注册后自动登录 |
| 当前用户 | `GET /users/me` | `Me { user, profile }` | 401 静默刷新 |
| 退出 | `POST /auth/logout` | `null` | 撤销当前会话 |
| 个人中心 `/account` | `GET /orders?page_size=3`；`GET /orders?status=...&page_size=1`；`GET /points/account` | `PageData<Order>`、`Pagination.total`、`{ balance }` | 订单状态计数 |
| 我的订单 `/account/orders` | `GET /orders?status&page&page_size` | `PageData<Order>`；`Order.store_orders[].items[]` | 退款售后标签前端聚合 `refunding/refunded/partially_refunded` |
| 取消订单 | `POST /orders/{id}/cancel` | `{ reason? }` → `Order` | 二次确认 |
| 确认收货 | `POST /orders/{id}/confirm-receipt` | `Order` | 二次确认；完成发积分 |
| 订单详情 `/account/orders/:id` | `GET /orders/{id}`；`GET /orders/{id}/refunds` | `Order`、`Refund[]` | 状态时间线、父子单、金额、退款记录 |
| 物流 `/account/orders/:id/logistics` | `GET /logistics/{order_id}` | `Shipment[] { carrier,tracking_no,status,tracks[],mock }` | 轨迹为 Mock，页面标注 |
| 申请退款 `/account/orders/:id/refund` | `GET /orders/{id}`；`GET /orders/{id}/refunds`；`POST /orders/{id}/refunds` | `RefundRequestIn { reason, amount?, store_order_id? }` → `Refund` | 按店铺子单；金额/状态以服务端为准 |
| 收货地址 `/account/addresses` | `GET/POST /users/me/addresses`；`PUT/DELETE /users/me/addresses/{id}` | `AddressIn/AddressOut` | 表单校验；默认地址 |
| 绿色积分 `/account/points` | `GET /points/account`；`GET /points/transactions?type_&page&page_size`；`GET /points/redemption-catalog`；`POST /points/redemptions` | `AccountOut`、`PageData<TransactionOut>`、`Redemption[]`、`RedeemOut { voucher_code, mock }` | 兑换权益为 Mock；流水类型 `earn/spend/reverse/adjust` |
| 个人资料 `/account/profile` | `GET /users/me`；`PATCH /users/me` | `ProfileUpdateIn { nickname,avatar_url,gender,birthday,bio }` → `Profile` | 无头像上传接口，仅支持图片 URL |
| 消息通知 `/account/notifications` | `GET /notifications?unread_only`；`POST /notifications/{id}/read`；`POST /notifications/read-all` | `NotificationOut[]` | 站内通知 |
| 甘肃产地 `/origin` | `GET /products?page_size=12`；`GET /categories` | `PageData<Product>` | 静态产区导航 + 商品 |
| 品牌故事 `/brand` | `GET /products?page_size=4` | `PageData<Product>` | 静态品牌叙事 + 品牌好物商品卡 |
| 助农项目 `/aid` | `GET /aid/projects?page&page_size` | `PageData<ProjectOut>`：`goal_amount/raised_amount/published_at` | 金额为字符串；演示数据声明 |
| 助农项目详情 `/aid/:id` | `GET /aid/projects/{id}` | `ProjectOut` | 演示数据声明 |
| 绿色消费专区 `/green` | `GET /products?page_size=20`；`GET /green/products/{id}`（逐品） | `Product` + `GreenDetail` | 无绿色资料的商品标注“待补充” |
| 平台公告 `/notices` | `GET /client/notices` | `Notice[] { id,title,content,published_at }` | 裸 JSON |
| 公告详情 `/notices/:id` | 同上（前端按 id 查找） | `Notice` | 无单独详情接口 |
| 帮助中心 `/help` | 无业务接口 | — | 静态 FAQ |
| 404 | 无 | — | 前端兜底 |

## 通用错误分支

| 错误码 | HTTP | 前端表现 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 展示 `data.errors[0].message` 或表单错误 |
| `UNAUTHENTICATED` / `TOKEN_EXPIRED` | 401 | 静默刷新重放；失败清理会话并跳登录 |
| `FORBIDDEN` / `ACCOUNT_DISABLED` | 403 | Toast 提示；受保护页面由路由守卫兜底 |
| `INSUFFICIENT_STOCK` | 409 | 提示库存不足并重新预览 |
| `PRICE_CHANGED` | 409 | 提示价格变化并重新预览 |
| `ORDER_STATE_INVALID` | 409 | 提示订单状态已变化并刷新 |
| `REFUND_NOT_ALLOWED` / `REFUND_EXCEED_LIMIT` | 409 | 退款页提示并保留表单 |
| `POINTS_INSUFFICIENT` | 409 | 积分兑换提示余额不足 |
| `RATE_LIMITED` | 429 | Toast 提示稍后重试 |
| `INTERNAL_ERROR` | 500 | Toast 提示；带 `request_id` 可复制 |

## 前端请求层约定

- `src/api/http.ts`：统一 `request`（信封解析、401 刷新、错误码、request_id）。
- `requestRaw`：用于 `/client/*` 裸 JSON 与 ETag。
- `getCmsConfig`：localStorage 缓存 + `If-None-Match` + 304 回退。
- `assetUrl`：`/uploads` 走后端/代理，`/assets` 走前端静态资源。
