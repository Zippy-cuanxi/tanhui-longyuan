# API 清单（自动生成，请勿手改）

总接口数：134

## admin

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/admin/dashboard/stats` | 运营概览统计 |
| `GET` | `/api/v1/admin/system-settings` | 系统设置列表 |
| `GET` | `/api/v1/admin/users` | 用户列表 |
| `POST` | `/api/v1/admin/users/{user_id}/ban` | 封禁用户（撤销全部会话） |
| `POST` | `/api/v1/admin/users/{user_id}/unban` | 解封用户 |
| `PUT` | `/api/v1/admin/system-settings` | 写入系统设置（记审计） |

## admin-aid

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/admin/aid/projects` | 全部项目（含草稿） |
| `POST` | `/api/v1/admin/aid/cooperatives` | 创建合作社 |
| `POST` | `/api/v1/admin/aid/projects/{project_id}/review` | 发布/下线项目 |
| `POST` | `/api/v1/admin/aid/projects` | 创建项目（草稿） |

## admin-audit

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/admin/audit/login-logs` | 登录日志 |
| `GET` | `/api/v1/admin/audit/operation-logs` | 操作日志 |
| `GET` | `/api/v1/admin/audit/security-events` | 安全事件 |

## admin-catalog

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/admin/products/{product_id}/audit-records` | 商品审核历史 |
| `GET` | `/api/v1/admin/products` | 全部商品列表（可按状态筛选） |
| `POST` | `/api/v1/admin/products/{product_id}/audit` | 审核商品（通过/驳回/平台下架） |

## admin-finance

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/admin/finance/ledger` | 平台台账流水 |
| `GET` | `/api/v1/admin/finance/settlements` | 结算单列表 |
| `POST` | `/api/v1/admin/finance/settlements/generate` | 生成结算单（仿真佣金规则） |
| `POST` | `/api/v1/admin/finance/settlements/{settlement_id}/confirm` | 确认结算单 |
| `POST` | `/api/v1/admin/finance/settlements/{settlement_id}/mark-paid` | 标记打款（仿真，无真实资金流） |

## admin-green

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/admin/green/profiles` | 绿色资料审核列表 |
| `POST` | `/api/v1/admin/green/assessments/{assessment_id}/verify` | 核验碳评估（pass/fail） |
| `POST` | `/api/v1/admin/green/profiles/{profile_id}/review` | 审核绿色资料 |

## admin-merchants

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/admin/merchants` | 商家列表（可按状态筛选） |
| `POST` | `/api/v1/admin/merchants/{merchant_id}/review` | 审核/冻结/解冻商家 |

## admin-orders

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/admin/orders/{order_id}` | 订单详情 |
| `GET` | `/api/v1/admin/orders` | 全部订单列表 |
| `GET` | `/api/v1/admin/refunds` | 退款单列表 |
| `POST` | `/api/v1/admin/refunds/{refund_id}/handle` | 处理退款（approve=Mock原路退回） |

## admin-points

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/admin/points/rules/{rule_id}/versions` | 规则版本历史 |
| `GET` | `/api/v1/admin/points/rules` | 积分规则列表 |
| `POST` | `/api/v1/admin/points/adjust` | 调整用户绿豆（必填原因，记审计） |
| `PUT` | `/api/v1/admin/points/rules/{code}` | 更新规则（生成新版本） |

## admin-rbac

| 方法 | 路径 | 说明 |
|---|---|---|
| `DELETE` | `/api/v1/admin/rbac/users/{user_id}/roles/{role_code}` | 移除用户角色 |
| `GET` | `/api/v1/admin/rbac/permissions` | 权限目录 |
| `GET` | `/api/v1/admin/rbac/roles` | 角色列表 |
| `GET` | `/api/v1/admin/rbac/user-roles` | 用户角色列表(分页) |
| `POST` | `/api/v1/admin/rbac/users/{user_id}/roles` | 授予用户角色 |

## admin-stores

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/admin/stores` | 店铺列表 |
| `POST` | `/api/v1/admin/stores/{store_id}/status` | 变更店铺状态 |

## aid

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/aid/projects/{project_id}` | 助农项目详情 |
| `GET` | `/api/v1/aid/projects` | 助农项目列表（已发布） |

## auth

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/auth/sessions` | 我的登录会话列表 |
| `POST` | `/api/v1/auth/login` | 登录（管理员可能要求 MFA） |
| `POST` | `/api/v1/auth/logout` | 登出（撤销当前会话） |
| `POST` | `/api/v1/auth/mfa/bind` | 绑定 TOTP MFA（仿真：任意有效 secret） |
| `POST` | `/api/v1/auth/refresh` | 刷新令牌（轮换，旧令牌作废） |
| `POST` | `/api/v1/auth/register` | 注册消费者账号 |
| `POST` | `/api/v1/auth/sessions/revoke-all` | 撤销我的全部会话 |

## cart

| 方法 | 路径 | 说明 |
|---|---|---|
| `DELETE` | `/api/v1/cart/items/{item_id}` | 删除购物车条目 |
| `GET` | `/api/v1/cart` | 我的购物车（价格/库存实时） |
| `PATCH` | `/api/v1/cart/items/{item_id}` | 修改数量/勾选 |
| `POST` | `/api/v1/cart/items` | 加入购物车 |

## catalog

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/categories` | 商品分类（树形/列表） |
| `GET` | `/api/v1/products/{product_id}` | 商品详情（含 SKU） |
| `GET` | `/api/v1/products` | 商品列表（分页/筛选/排序） |

## cms-admin

| 方法 | 路径 | 说明 |
|---|---|---|
| `DELETE` | `/api/v1/cms/pages/{page_id}/sections/{section_id}` | 删除区块 |
| `GET` | `/api/v1/cms/pages/{page_id}/versions` | 版本历史 |
| `GET` | `/api/v1/cms/pages` | 页面列表 |
| `POST` | `/api/v1/cms/announcements/{ann_id}/offline` | 下线公告 |
| `POST` | `/api/v1/cms/announcements/{ann_id}/publish` | 发布公告 |
| `POST` | `/api/v1/cms/announcements` | 创建公告（草稿） |
| `POST` | `/api/v1/cms/banners` | 新增 Banner |
| `POST` | `/api/v1/cms/pages/{page_id}/preview` | 草稿预览（快照） |
| `POST` | `/api/v1/cms/pages/{page_id}/publish` | 发布（生成不可变版本） |
| `POST` | `/api/v1/cms/pages/{page_id}/rollback/{version_id}` | 回滚到指定版本 |
| `POST` | `/api/v1/cms/pages/{page_id}/sections` | 新增区块 |
| `POST` | `/api/v1/cms/pages` | 创建页面 |
| `PUT` | `/api/v1/cms/banners/{banner_id}` | 更新 Banner |
| `PUT` | `/api/v1/cms/pages/{page_id}/sections/{section_id}` | 更新区块 |

## cms-client

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/client/banners` | Banner 列表（生效中） |
| `GET` | `/api/v1/client/config/{page_key}` | 读取已发布页面配置（ETag 缓存） |
| `GET` | `/api/v1/client/notices` | 公告列表（已发布） |

## green

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/green/products/{product_id}` | 商品绿色资料与碳评估（含核验状态） |

## logistics

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/logistics/{order_id}` | 订单物流（发货单+轨迹） |

## merchant

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/merchant/merchants/me` | 我所属的商家主体 |
| `POST` | `/api/v1/merchant/apply` | 提交入驻申请（任意登录用户） |

## merchant-catalog

| 方法 | 路径 | 说明 |
|---|---|---|
| `DELETE` | `/api/v1/merchant/products/images/{image_id}` | 删除商品图片 |
| `DELETE` | `/api/v1/merchant/products/{product_id}` | 删除商品（仅草稿/驳回） |
| `GET` | `/api/v1/merchant/products/{product_id}` | 本店商品详情 |
| `GET` | `/api/v1/merchant/products` | 本店商品列表 |
| `PATCH` | `/api/v1/merchant/products/skus/{sku_id}/price` | 修改 SKU 价格（触发重新审核） |
| `PATCH` | `/api/v1/merchant/products/{product_id}` | 修改商品信息 |
| `POST` | `/api/v1/merchant/products/{product_id}/delist` | 下架 |
| `POST` | `/api/v1/merchant/products/{product_id}/images` | 上传商品图片 |
| `POST` | `/api/v1/merchant/products/{product_id}/list` | 上架 |
| `POST` | `/api/v1/merchant/products/{product_id}/skus` | 新增 SKU |
| `POST` | `/api/v1/merchant/products/{product_id}/submit` | 提交审核 |
| `POST` | `/api/v1/merchant/products` | 新建商品（草稿） |

## merchant-finance

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/merchant/finance/settlements` | 本店结算单 |
| `GET` | `/api/v1/merchant/finance/summary` | 本店财务汇总 |

## merchant-green

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/v1/merchant/green/profiles` | 提交/更新绿色资料（进入审核） |

## merchant-inventory

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/merchant/inventory/logs` | 库存流水 |
| `GET` | `/api/v1/merchant/inventory` | 本店库存列表 |
| `POST` | `/api/v1/merchant/inventory/adjust` | 调整库存（记流水） |

## merchant-orders

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/merchant/orders/aftersales/all` | 本店售后/退款列表（只读，处理由平台客服完成） |
| `GET` | `/api/v1/merchant/orders/{store_order_id}` | 本店订单详情 |
| `GET` | `/api/v1/merchant/orders` | 本店订单列表 |
| `POST` | `/api/v1/merchant/orders/{store_order_id}/ship` | 发货（出库+物流单） |

## merchant-stores

| 方法 | 路径 | 说明 |
|---|---|---|
| `DELETE` | `/api/v1/merchant/stores/{store_id}/employees/{member_id}` | 移除员工 |
| `GET` | `/api/v1/merchant/stores/{store_id}/dashboard` | 商家工作台统计 |
| `GET` | `/api/v1/merchant/stores/{store_id}/employees` | 员工列表 |
| `GET` | `/api/v1/merchant/stores` | 我的店铺列表 |
| `PATCH` | `/api/v1/merchant/stores/{store_id}/employees/{member_id}` | 调整员工角色 |
| `PATCH` | `/api/v1/merchant/stores/{store_id}` | 更新店铺资料（owner/manager） |
| `POST` | `/api/v1/merchant/stores/{store_id}/employees` | 添加员工 |

## meta

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/healthz` | 存活探针 |
| `GET` | `/readyz` | 就绪探针（检查数据库） |

## notifications

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/notifications` | 我的通知（最近100条） |
| `POST` | `/api/v1/notifications/read-all` | 全部已读 |
| `POST` | `/api/v1/notifications/{notification_id}/read` | 标记已读 |

## orders

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/orders/{order_id}/refunds` | 订单退款记录 |
| `GET` | `/api/v1/orders/{order_id}` | 订单详情 |
| `GET` | `/api/v1/orders` | 我的订单列表 |
| `POST` | `/api/v1/orders/preview` | 订单预览（服务端计价） |
| `POST` | `/api/v1/orders/{order_id}/cancel` | 取消待支付订单 |
| `POST` | `/api/v1/orders/{order_id}/confirm-receipt` | 确认收货 |
| `POST` | `/api/v1/orders/{order_id}/refunds` | 申请退款（按店铺子单） |
| `POST` | `/api/v1/orders` | 创建订单（多商家拆单+库存预占+幂等） |

## payments

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/payments/{pay_no}` | 查询支付单状态 |
| `POST` | `/api/v1/payments/callback/mock` | 【SANDBOX】Mock 渠道支付回调（验签+金额核对+幂等） |
| `POST` | `/api/v1/payments/mock/pay` | 【SANDBOX 仿真】模拟用户完成支付并触发签名回调 |
| `POST` | `/api/v1/payments/{order_id}/init` | 发起/重新发起支付 |

## points

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/points/account` | 我的绿豆账户 |
| `GET` | `/api/v1/points/redemption-catalog` | 可兑换权益目录（Mock） |
| `GET` | `/api/v1/points/transactions` | 绿豆流水 |
| `POST` | `/api/v1/points/redemptions` | 绿豆兑换（Mock 权益） |

## users

| 方法 | 路径 | 说明 |
|---|---|---|
| `DELETE` | `/api/v1/users/me/addresses/{address_id}` | 删除收货地址 |
| `GET` | `/api/v1/users/me/addresses` | 收货地址列表 |
| `GET` | `/api/v1/users/me` | 当前登录用户信息 |
| `PATCH` | `/api/v1/users/me` | 更新个人资料 |
| `POST` | `/api/v1/users/me/addresses` | 新增收货地址 |
| `PUT` | `/api/v1/users/me/addresses/{address_id}` | 修改收货地址 |
