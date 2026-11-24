# 通用约定（契约冻结基线）

## 统一响应结构

成功：`{ "code": "OK", "message": "success", "data": <T|null>, "request_id": "..." }`
失败：HTTP 状态码语义化 + 同结构错误体，`code` 为稳定字符串错误码。

## 错误码注册表

| code | HTTP | 说明 |
|---|---|---|
| VALIDATION_ERROR | 422 | 参数校验失败（data.errors 为字段明细） |
| UNAUTHENTICATED | 401 | 未登录/凭证无效 |
| TOKEN_EXPIRED | 401 | 令牌过期（应刷新） |
| REFRESH_TOKEN_INVALID | 401 | 刷新凭证无效/复用（须重新登录） |
| BAD_CREDENTIALS | 401 | 账号或密码错误 |
| MFA_REQUIRED / MFA_INVALID | 401 | 需要二次验证 / 验证码错误 |
| FORBIDDEN | 403 | 无权限（含跨店铺越权） |
| ACCOUNT_DISABLED | 403 | 账号被禁用 |
| NOT_FOUND | 404 | 资源不存在 |
| METHOD_NOT_ALLOWED | 405 | — |
| CONFLICT | 409 | 资源状态冲突 |
| EMAIL_TAKEN | 409 | 邮箱已注册 |
| INSUFFICIENT_STOCK | 409 | 库存不足（含并发预占失败） |
| PRICE_CHANGED | 409 | 服务端价格与 expected_unit_price 不一致 |
| ORDER_STATE_INVALID | 409 | 订单状态机非法迁移 |
| IDEMPOTENCY_CONFLICT | 409 | 幂等键重复且请求内容不同 |
| REFUND_NOT_ALLOWED / REFUND_EXCEED_LIMIT | 409 | 不可退款 / 超出可退限额 |
| POINTS_INSUFFICIENT | 409 | 绿豆余额不足 |
| MERCHANT_STATE_INVALID / STORE_REQUIRED | 409/400 | 商家状态非法 / 需指定店铺 |
| PAYMENT_SIGNATURE_INVALID | 400 | 回调验签失败 |
| PAYMENT_AMOUNT_MISMATCH | 400 | 回调金额/币种不符 |
| PAYMENT_MERCHANT_MISMATCH | 400 | 回调商户号不符 |
| CMS_COMPONENT_UNKNOWN | 422 | 非白名单组件 |
| CMS_PAGE_NOT_PUBLISHED | 404 | 页面未发布 |
| FILE_TYPE_INVALID / FILE_TOO_LARGE / FILE_CONTENT_INVALID | 422 | 上传校验失败 |
| RATE_LIMITED | 429 | 限流 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

## 分页

- 请求：`?page=1&page_size=20`（page ≥ 1，page_size ≤ 100）
- 响应：`data.items[]` + `data.pagination{page, page_size, total, total_pages}`

## 时间 / 金额 / ID

- 时间：ISO 8601 UTC（`2026-11-23T12:00:00+00:00`），数据库统一 timestamptz
- 金额：**字符串两位小数**（`"99.00"`），数据库 NUMERIC(12,2)，服务端 Decimal 计算，禁止浮点
- ID：UUID v4（字符串形式），所有主键与对外引用一致
- 单号：`TH`/`SO`/`PAY`/`RF` 前缀 + 时间戳 + 随机串

## 认证

- `Authorization: Bearer <access_token>`（30 分钟）
- 刷新：`POST /auth/refresh`，**即轮换**；检测到旧令牌复用 → 撤销整条会话链（安全事件记录）
- 管理员 MFA：未绑定 TOTP 时接受 `MOCK_MFA_CODE`（仿真，默认 123456，置空禁用）

## 商家数据范围（防 IDOR）

- 店铺角色权限映射：`app/core/deps.py STORE_ROLE_PERMISSIONS`
- 一个用户可加入多个店铺（业务已确认），每次成员关系独立限权：
  owner > manager > staff > viewer；跨店访问必须显式 `store_id` 且校验成员身份

## 幂等

- 下单：`Idempotency-Key`（orders 表 user+key 唯一；同 key 不同载荷 → IDEMPOTENCY_CONFLICT）
- 支付回调：trade_no 唯一 + 已成功单据幂等应答 duplicate
- 积分：point_transactions.idempotency_key 唯一约束
