# 碳惠陇原 · 管理端 Web 需求与技术供给说明

> 版本：v1.0（2026-11-24）
> 适用对象：AI 开发代理、前端开发、后端联调、评审人
> 基线仓库：`C:\Users\85046\Desktop\碳惠陇原`
> 基线事实：后端 **134 个接口 / 58 张表 / 33 个 pytest 通过**；消费者端 **25 条路由**，管理端 **0 条路由**。
> 文档定位：不是泛泛的 PRD，而是「可直接拆任务、可直接写代码、可直接验收」的供给说明。
>
> 阅读路径：§0 结论 → §1 现状 → §2 功能 → §3 页面 → §4 权限 → §5 指标 → §6 流程 → §7 复用 → §8 接口 → §9 技术 → §10 改造 → §11 非功能 → §12 交付 → §13 AI 约束 → §14 风险。
> 拆任务顺序：先做 §12.1 的 M0（后端 B01/B02/B08 + 前端脚手架），再按 §3.3 建路由，按 §8.2 补接口，按 §12.5 验收。

---

## 0. 一页结论

| # | 结论 | 依据 |
|---|---|---|
| 1 | **不是重写后端，而是补前端 + 补 8 个 P0 后端阻塞项（另有 18 个 P1 优化项）** | 管理端可用接口已有 **55 个**：41 个 `/admin/*` + 14 个 `/cms/*`，覆盖全部关键写操作 |
| 2 | **管理端必须是独立应用**，不要塞进消费者商城 | 消费者端 25 条路由、7146 行 `main.css`、含 maplibre/deck.gl；混在一起会污染包体与登录态 |
| 3 | **三个最关键的 P0 阻塞必须先解** | 管理员密码不可得；`/admin/me` 不回传角色权限；工作台只有 5 个指标且权限判断为 AND |
| 4 | **MVP 只需 9 条路由 / 8 项能力** | 登录、工作台、商品审核、商家审核、订单列表/详情、退款、结算、台账；净开发约 8 人天 |
| 5 | **指标一律服务端算** | 前端只做字符串格式化；禁止前端跨页汇总金额作为权威值 |
| 6 | **现有权限设计与业务预期有 8 处错配/风险** | 运营不能审商家/退款；财务无 `store:read` 且结算不返回店铺名；商品审核接口要求 `approve + remove` 两个权限；详见 §4.3 |
| 7 | **图表数据必须新增聚合接口** | 现有 `/admin/dashboard/stats` 只有 5 个标量，`pending_product_audits` 硬编码为 0 |
| 8 | **明确不做**：行级数据权限、地图大屏、拖拽建站、自定义报表 SQL、真实支付/物流对接 | 见 §10.4 与 §14 |

### 0.1 AI 开发必须先读的 6 个文件

| 顺序 | 文件 | 用途 |
|---|---|---|
| 1 | `tanhui-backend/docs/api-list.md` | 134 个接口的权威清单 |
| 2 | `tanhui-backend/docs/conventions.md` | 统一响应、错误码、分页、金额/时间/ID 约定 |
| 3 | `tanhui-backend/docs/state-machines.md` | 订单、退款、商品、商家、CMS 状态机 |
| 4 | `tanhui-backend/docs/er-diagram.md` | 58 张表的关系与外键 |
| 5 | `docs/page-api-map.md` | 消费者端「页面 → API → DTO」的写法范例 |
| 6 | `src/api/http.ts` | 统一请求、401 刷新、错误码、`request_id` 的现成实现 |

> 任何与本文件冲突之处，以 **后端实际代码 + `openapi.yaml`** 为准；本文件负责指出「哪里不够、应该补什么」。

---

## 1. 现状分析

### 1.1 工程结构

```
碳惠陇原/
├─ src/                         消费者端 Vue 3 应用（25 条路由）
│  ├─ api/                      http.ts / index.ts / types.ts
│  ├─ components/               Header、Footer、ProductCard、StateBlock、CMS 区块、产地地图
│  ├─ stores/                   auth / cart / checkout / points / toast / confirm
│  ├─ views/                    消费者页面（含 account 子页）
│  └─ assets/main.css           7146 行设计 Token + 页面样式
├─ tanhui-backend/              FastAPI 统一后端（20 个域，134 接口，58 表）
│  ├─ app/modules/*/admin_router.py   管理端接口
│  ├─ app/core/                 deps / responses / errors / security / ratelimit
│  ├─ docs/                     api-list / openapi / er-diagram / state-machines / conventions
│  └─ scripts/seed.py           基础种子（管理员密码随机生成）
├─ scripts/                     seed_demo.py、Playwright 冒烟、截图、图片处理
├─ docs/                        architecture / page-api-map / backend-notes / test-report
├─ public/images/               设计素材
├─ artifacts/                   截图（已 gitignore）
└─ dist/                        消费者端构建产物
```

### 1.2 技术栈基线

| 层 | 现状 | 版本/说明 |
|---|---|---|
| 前端框架 | Vue 3 + TypeScript + Vite | `vue 3.5.21`、`typescript 5.9.2`、`vite 7.1.7` |
| 路由/状态 | Vue Router + Pinia | `vue-router 4.5.1`、`pinia 3.0.3` |
| 消费者端可视化 | maplibre-gl + deck.gl | 仅产地地图使用，管理端 **不要引入** |
| 后端 | FastAPI + SQLAlchemy 2 + Pydantic 2 | 20 个域，134 接口 |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） | 当前开发库 58 张表 |
| 认证 | JWT HS256 + Refresh 轮换 | access 30 分钟、refresh 14 天、Argon2id、TOTP MFA（仿真） |
| 测试 | pytest + Playwright 脚本 | 后端 33 passed；前端 typecheck/lint/build 通过 |
| 规范 | ESLint 10 + Prettier 3 + vue-tsc 3 | 交付前必须全绿 |

> **运行目录提醒**：`README.md` 记载当前联调后端实际运行在 `C:\Users\85046\Desktop\碳惠陇原统一后端-tanhui-backend\tanhui-backend`，而本仓库内也有 `tanhui-backend/` 同源副本。改后端代码前先确认 `uvicorn` 的工作目录，避免改了不运行的副本；本文所有后端路径均指本仓库 `tanhui-backend/`。

### 1.3 已有页面（消费者端）

| 分组 | 路由 | 说明 |
|---|---|---|
| 公共 | `/`、`/products`、`/products/:id`、`/origin`、`/aid`、`/aid/:id`、`/green`、`/notices`、`/notices/:id`、`/help` | 首页、列表、详情、产地、助农、绿色专区、公告、帮助 |
| 交易 | `/cart`、`/checkout`、`/pay/:orderId` | 购物车、确认订单、Mock 支付 |
| 账户 | `/login`、`/register`、`/account`、`/account/orders`、`/account/orders/:id`、`/account/orders/:id/logistics`、`/account/orders/:id/refund`、`/account/addresses`、`/account/points`、`/account/profile`、`/account/notifications` | 登录注册、个人中心、订单、物流、退款、地址、积分、资料、通知 |
| 兜底 | `/:pathMatch(.*)*` | 404 |

> 现状偏差：`README.md` 仍列 `/brand` 品牌故事，但当前 `src/router/index.ts` 已无该路由，`src/views/BrandView.vue` 已在工作区删除。以 router 为准。管理端无关，但说明文档会漂移，AI 开发必须以代码为准。

消费者端页面可归纳为 4 种模式，管理端可直接借鉴其数据组织方式：

| 模式 | 代表页面 | 可借鉴 | 不要照搬 |
|---|---|---|---|
| 列表 | `CatalogView`、`OrdersView`、`NoticesView` | query 驱动筛选、分页、四态、空态 | 消费者卡片网格、营销视觉 |
| 详情 | `ProductDetailView`、`OrderDetailView`、`AidDetailView` | 主从数据、金额字符串、状态文案 | 大图横幅、叙事型排版 |
| 表单 | `CheckoutView`、`RefundView`、`AddressFormModal` | 校验、提交锁、二次确认、错误分支 | 消费者文案与 Toast 风格 |
| 内容区块 | `HomeView` + `CmsSectionRenderer` | 白名单渲染、未知组件降级 | 只读渲染器不能用于编辑态 |

### 1.4 数据结构（按域）

| 域 | 核心表 | 关键字段 | 状态/说明 |
|---|---|---|---|
| 用户 | `users`、`user_profiles`、`user_addresses` | `email`、`is_active`、`mfa_enabled`、`ban_reason`、`banned_until` | 封禁即 `is_active=false` 并撤销全部会话 |
| 商家 | `merchants`、`merchant_users` | `status`、`company_name`、`license_no`、`legal_person`、`initial_store_name` | `pending_review/approved/rejected/frozen` |
| 店铺 | `stores`、`store_members` | `status`、`is_closed_temporarily`、`role` | `active/suspended/closed`；成员角色 `owner/manager/staff/viewer` |
| 商品 | `categories`、`products`、`product_skus`、`product_images`、`product_audit_records` | `status`、`is_listed`、`price`、`audit_reason` | `draft/pending_review/approved/rejected/removed` |
| 库存 | `inventories`、`inventory_logs`、`inventory_reservations` | `quantity_total`、`quantity_reserved`、`status` | 条件 UPDATE 防超卖；预占/释放/出库 |
| 订单 | `orders`、`store_orders`、`order_items`、`order_status_logs` | `status`、`pay_amount`、`refund_amount`、快照字段 | 父单 + 店铺子单；金额服务端算 |
| 支付/退款 | `payment_orders`、`payment_callbacks`、`payment_transactions`、`refunds` | `status`、`trade_no`、`amount`、`handled_at` | 支付 Mock 沙箱；退款 Mock 原路退回 |
| 财务 | `merchant_settlements`、`settlement_items`、`platform_ledger` | `orders_total`、`commission_total`、`payable_total`、`entry_type` | 结算单 `pending/confirmed/paid`；台账只追加 |
| 积分 | `point_accounts`、`point_transactions`、`point_rules`、`point_rule_versions` | `balance`、`type`、`amount`、`balance_after`、`config` | `earn/spend/reverse/adjust`；规则版本化 |
| 绿色 | `product_green_profiles`、`carbon_assessments`、`verification_records` | `status`、`co2e_per_unit`、`verified`、`result` | 碳评估默认 `verified=false` |
| 助农 | `cooperatives`、`aid_projects`、`aid_donations`、`aid_records` | `status`、`goal_amount`、`raised_amount`、`amount` | 项目 `draft/pending_review/published/offline` |
| CMS | `cms_pages`、`cms_sections`、`cms_page_versions`、`cms_publish_records`、`cms_banners`、`cms_announcements` | `page_key`、`section_type`、`snapshot`、`enabled` | 发布=不可变快照；组件白名单 6 类 |
| RBAC | `roles`、`permissions`、`role_permissions`、`user_roles`、`data_scopes` | `code`、`is_super`、`kind` | 20 个权限码、5 个内置角色 |
| 审计 | `operation_logs`、`login_logs`、`security_events` | `action`、`resource`、`detail`、`ip` | 敏感写操作落审计；无读操作审计 |
| 系统 | `system_settings` | `key`、`value`（JSON） | 无 schema 校验，前端需兜底 |

> 完整枚举见附录 A；完整 ER 见 `tanhui-backend/docs/er-diagram.md`。

### 1.5 接口存量

| 分组 | 数量 | 说明 |
|---|---:|---|
| `admin`（工作台/设置/用户） | 6 | 工作台统计、系统设置、用户列表与封禁 |
| `admin-catalog` | 3 | 商品列表、审核历史、审核 |
| `admin-orders` | 4 | 订单列表/详情、退款列表/处理 |
| `admin-finance` | 5 | 结算生成/列表/确认/打款、台账 |
| `admin-merchants` | 2 | 商家列表、审核/冻结 |
| `admin-stores` | 2 | 店铺列表、状态变更 |
| `admin-green` | 3 | 绿色资料列表/审核、碳评估核验 |
| `admin-aid` | 4 | 项目列表/创建/发布下线、合作社创建 |
| `admin-points` | 4 | 规则列表/版本/更新、积分调整 |
| `admin-rbac` | 5 | 角色/权限/用户角色/授予/移除 |
| `admin-audit` | 3 | 操作/登录/安全事件 |
| `cms-admin` | 14 | 页面/区块/预览/发布/版本/回滚、公告、Banner |
| **管理端可用合计** | **55** | 41 个 `/admin/*` + 14 个 `/cms/*` |
| 消费者/商家/公共 | 79 | 含 auth/users/catalog/cart/orders/payments/points/logistics/notifications/aid/green/client/merchant |
| **总计** | **134** | 来源：`tanhui-backend/docs/api-list.md` |

统一契约：

- 响应：`{ code, message, data, request_id }`，错误码见 `docs/conventions.md`。
- 分页：`?page=1&page_size=20` → `data.items[] + data.pagination{page,page_size,total,total_pages}`，`page_size ≤ 100`。
- 金额：两位小数字符串（`"99.00"`），服务端 Decimal 计算，禁止浮点。
- 时间：ISO 8601 UTC；数据库 timestamptz。
- ID：UUID v4 字符串；单号 `TH/SO/PAY/RF` 前缀。
- 认证：`Authorization: Bearer <access>`；401 静默刷新一次并重放；刷新失败清会话。
- 权限：`require_permissions(...)` 为 **AND** 语义；`super_admin` 通过 `is_super` 通配。

### 1.6 业务逻辑要点（管理端必须理解）

1. **订单与库存**：下单服务端计价 → 库存预占 → 父单 + 店铺子单 + 条目快照 → 幂等键。支付回调成功 `pending_payment → paid`；发货消耗预占；确认收货发积分；取消释放预占。
2. **父单状态聚合**：全部发货→`shipped`；部分发货→保持 `paid`；全部退款→`refunded`；任一退款>0→`partially_refunded`；全部完成→`completed`。
3. **退款副作用**：管理员 `approve` 后，退款单 `requested → refunded`，累加 `store_orders.refund_amount`，写 `platform_ledger` 退款流水，按比例冲正积分，推进子/父单状态，发站内通知。`reject` 回到退款前状态。
4. **商品审核**：商家 `draft → pending_review`；管理员 `approve/reject`（驳回原因后端有默认值，前端必须强制填写）；`approved` 后商家自主上下架；平台可 `remove`。
5. **商家审核**：`pending_review → approved` 时自动创建默认店铺并绑定 `owner`；`rejected` 记录原因；`approved ⇄ frozen`。
6. **结算口径**：只结算 `completed / partially_refunded` 且 `completed_at ∈ [period_start, period_end)`、未被其他结算单引用的店铺子单；`orders_total = Σ items_total`（不含运费），`commission = 5% × items_total`，`payable = orders_total - commission`；同店同期唯一。**注意**：当前实现未扣减 `store_orders.refund_amount`，部分退款子单仍按 `items_total` 全额结算，这是待财务确认的口径（见 §10.2 B26、§14 D13）。
7. **积分**：订单完成按 1 元=1 积分发放；退款按比例冲正；助农 1 元=3 积分；管理员调整必填原因并记审计；流水只追加，带 `balance_after`。
8. **绿色**：商家提交即 `pending_review`；管理员审核资料；碳评估提交一律 `verified=false`，平台核验 `pass/fail` 后写 `verification_records`；未核验不得对外宣称已核验。
9. **CMS**：页面区块白名单 `banner/product_grid/rich_text/points_panel/aid_project/navigation`；发布生成不可变快照；回滚生成新版本；公告 `draft/published/offline`。
10. **RBAC**：20 个权限码、5 个内置角色；超管通配；店铺角色独立（管理端不涉及店铺角色）。
11. **审计**：敏感写操作写 `operation_logs`（操作者、动作、资源、detail、IP）；登录写 `login_logs`；刷新令牌复用写 `security_events`。

### 1.7 现状结论（管理端视角）

| 结论 | 证据 | 影响 |
|---|---|---|
| 核心读接口基本齐全，写接口覆盖关键动作 | 55 个管理接口已存在 | 管理端主要是前端工程 + DTO/聚合补齐 |
| 列表筛选普遍不足 | 商品只有 `status/store_id`；订单/退款只有 `status`；审计只有 `action/resource/email/kind` | 运营无法按订单号、日期、店铺、关键词定位 |
| 列表 DTO 缺展示字段 | 商品列表 `min_price/cover_url` 为空；订单列表只有 6 个字段；结算/台账无店铺名 | 页面无法直接渲染，必须补后端 |
| 无 `admin/me` | `/users/me` 只返回 `user/profile`，JWT 无 roles | 前端无法做菜单与路由权限 |
| 无报表/导出 | 134 接口中无 export/report | 财务对账只能手工翻页 |
| 无聚合接口 | 工作台 5 个标量，待办硬编码 0 | 无法做趋势、分布、Top 榜 |
| 演示数据量小 | 当前库：7 商品、7 订单、2 店铺、8 用户、0 结算 | 图表几乎为空，必须扩样 |
| 角色配置有错配 | 运营无 `merchant:review/refund:approve`；财务无 `store:read` | 页面 403 或显示空店铺名 |

---

## 2. 核心功能清单

| ID | 能力 | 优先级 | 说明 | 后端就绪度 | 验收标准 |
|---|---|---|---|---|---|
| F01 | 登录与权限 | P0 | 管理员登录、MFA 分支、会话保持、菜单/路由按权限 | ⚠️ 需 `/admin/me` | 非管理员无法进入；刷新不掉线；403 不登出 |
| F02 | 工作台 | P0 | KPI、待办、趋势、分布、Top 榜 | ⚠️ 需聚合接口 | 6 KPI + 7 待办 + 2 图；与列表对账一致 |
| F03 | 商品审核 | P0 | 待审队列、详情、通过/驳回、审核历史 | ✅ 接口，⚠️ 列表字段 | 驳回必填原因；审核后队列减少 |
| F04 | 商品库 | P1 | 全状态查询、筛选、查看 | ⚠️ DTO/筛选 | 可按状态/店铺/分类/关键词筛选 |
| F05 | 商家入驻审核 | P0 | 待审、资质、通过/驳回 | ✅ | 通过后自动建店；驳回有原因 |
| F06 | 商家/店铺管理 | P1 | 商家列表、冻结/解冻、店铺状态 | ⚠️ 筛选/字段 | 状态流转正确；`closed` 不可再变更 |
| F07 | 订单查询 | P0 | 列表、详情、父子单、金额、物流、退款记录 | ⚠️ 筛选/字段 | 按订单号/状态/日期可查；详情完整 |
| F08 | 退款售后 | P0 | 待处理队列、通过/驳回、副作用 | ✅ | approve 后状态/台账/积分/通知正确 |
| F09 | 财务结算 | P0 | 预览、生成、确认、打款、明细 | ⚠️ 需 preview/detail | 状态流转；重复生成 409 |
| F10 | 平台台账 | P0 | 只读流水、筛选、汇总 | ⚠️ 字段/筛选 | 收支方向正确；可按类型/日期筛选 |
| F11 | 绿色资料/碳核验 | P1 | 审核队列、详情、碳核验 | ⚠️ 列表缺字段 | 未核验标识不被隐藏；核验记录可追溯 |
| F12 | 助农项目/合作社 | P1 | 项目 CRUD/发布/下线、合作社 | ❌ 合作社列表 | 项目可创建并发布；合作社可选 |
| F13 | CMS Banner/公告 | P1 | 列表、创建、编辑、发布/下线、启停 | ❌ 管理列表 | 公告发布后客户端可见；Banner 生效时间正确 |
| F14 | CMS 页面配置 | P2 | 页面/区块编辑、预览、发布、版本/回滚 | ✅ | 发布生成版本；回滚可用 |
| F15 | 会员管理 | P1 | 列表、详情、封禁/解封 | ⚠️ 详情/筛选 | 封禁后会话失效 |
| F16 | 积分规则/调整 | P1 | 规则版本、调整、流水 | ⚠️ 查询账户 | 调整必填原因；流水可追溯 |
| F17 | RBAC | P1 | 角色/权限查看、用户角色授予/移除 | ✅ | 授予后重新登录生效；审计记录 |
| F18 | 审计日志 | P1 | 操作/登录/安全事件 | ⚠️ 筛选 | 可按时间/动作/用户筛选 |
| F19 | 系统设置 | P2 | 键值查看/编辑 | ✅ | JSON 校验；写审计 |
| F20 | 报表/导出 | P1 导出 / P2 报表 | 固定报表、CSV 导出 | ❌ | 导出可用 Excel 打开；报表与列表对账一致 |

> 优先级定义：P0 = 没有它平台无法运营；P1 = 上线后 2 周内必须补；P2 = 可排到第二迭代。

---

## 3. 页面与模块划分

### 3.1 信息架构

```
管理端
├─ 工作台
├─ 交易
│  ├─ 订单
│  └─ 退款售后
├─ 商品
│  ├─ 商品审核
│  └─ 商品库
├─ 商家
│  ├─ 入驻审核
│  └─ 商家与店铺
├─ 财务
│  ├─ 结算单
│  └─ 平台台账
├─ 绿色与助农
│  ├─ 绿色资料
│  ├─ 碳评估核验
│  ├─ 助农项目
│  └─ 合作社
├─ 内容
│  ├─ Banner
│  ├─ 公告
│  └─ 页面配置
├─ 会员与积分
│  ├─ 会员
│  ├─ 积分规则
│  └─ 积分调整
├─ 权限与审计
│  ├─ 角色权限
│  ├─ 用户角色
│  ├─ 操作日志
│  ├─ 登录日志
│  └─ 安全事件
└─ 系统
   ├─ 系统设置
   └─ 报表中心
```

### 3.2 布局规范

| 项 | 规范 |
|---|---|
| 侧边栏 | 232px，可折叠至 64px；深森林绿 `--green-900`；分组标题 12px；当前项金色左侧指示条 |
| 顶栏 | 56px；面包屑 + 环境标识 + 刷新 + 用户菜单；环境非 `prod` 时显示「仿真环境」 |
| 内容区 | 背景 `#f5f7f4`；卡片白色；内边距 24px；卡片圆角 12px；阴影 `0 2px 8px rgba(20,80,45,.06)` |
| 表格 | 行高 44px；表头 13px 加粗；正文 13px；金额右对齐、等宽数字；状态用「色点 + 文字」 |
| 字体 | 正文 `PingFang SC / Microsoft YaHei`；管理端不使用消费者端的宋体展示字体 |
| 状态色 | 成功 `#18a05f`、警告 `#c9a227`、危险 `#d93a42`、信息 `#2f6feb`、中性 `#788b7f` |
| 断点 | ≥1440 舒适；1280–1440 紧凑；1024–1280 表格横向滚动；<1024 显示「请使用桌面端」 |
| 暗色模式 | P0 不做；P2 可选，不作为验收项 |
| 详情形态 | 审核/退款用右侧抽屉 720px；订单/结算用独立页面；表格行可点击进入 |

### 3.3 页面清单（路由 + 权限 + 接口 + 就绪度）

| 路由 | 页面 | 模块 | 权限 | 主要接口 | 就绪度 |
|---|---|---|---|---|---|
| `/admin/login` | 登录 | 认证 | 公开 | `POST /auth/login`、`GET /users/me`、`GET /admin/me`（新） | ⚠️ |
| `/admin/dashboard` | 工作台 | 工作台 | `dashboard:read`（新） | `GET /admin/dashboard/overview`（新） | ❌ |
| `/admin/orders` | 订单列表 | 交易 | `order:read` | `GET /admin/orders` | ⚠️ |
| `/admin/orders/:id` | 订单详情 | 交易 | `order:read` | `GET /admin/orders/{id}` | ⚠️ |
| `/admin/refunds` | 退款售后 | 交易 | `order:read` + `refund:approve` | `GET /admin/refunds`、`POST /admin/refunds/{id}/handle` | ⚠️ |
| `/admin/products/review` | 商品审核 | 商品 | `product:read` + `product:approve` | `GET /admin/products?status=pending_review`、`GET /admin/products/{id}`（新）、`POST /admin/products/{id}/audit` | ⚠️ |
| `/admin/products` | 商品库 | 商品 | `product:read` | `GET /admin/products` | ⚠️ |
| `/admin/merchants/review` | 商家入驻审核 | 商家 | `merchant:read` + `merchant:review` | `GET /admin/merchants`、`POST /admin/merchants/{id}/review` | ✅ |
| `/admin/merchants` | 商家与店铺 | 商家 | `merchant:read`、`store:read`、`store:manage` | `GET /admin/merchants`、`GET /admin/stores`、`POST /admin/stores/{id}/status` | ⚠️ |
| `/admin/finance/settlements` | 结算单 | 财务 | `finance:read` / `finance:manage` | `GET/POST /admin/finance/settlements*`、preview/detail（新） | ⚠️ |
| `/admin/finance/ledger` | 平台台账 | 财务 | `finance:read` | `GET /admin/finance/ledger` | ⚠️ |
| `/admin/green/profiles` | 绿色资料 | 绿色 | `green:review` | `GET /admin/green/profiles`、`POST .../review` | ⚠️ |
| `/admin/green/assessments` | 碳评估核验 | 绿色 | `green:review` | `POST /admin/green/assessments/{id}/verify`、detail（新） | ⚠️ |
| `/admin/aid/projects` | 助农项目 | 助农 | `aid:manage` | `GET/POST /admin/aid/projects`、`POST .../review` | ⚠️ |
| `/admin/aid/cooperatives` | 合作社 | 助农 | `aid:manage` | `GET`（新）/`POST /admin/aid/cooperatives` | ❌ |
| `/admin/cms/banners` | Banner | 内容 | `cms:manage` | `GET`（新）/`POST/PUT`、上传（新） | ❌ |
| `/admin/cms/announcements` | 公告 | 内容 | `cms:manage` | `GET`（新）/`POST/publish/offline` | ❌ |
| `/admin/cms/pages` | 页面配置 | 内容 | `cms:manage` | `GET/POST /cms/pages` | ✅ |
| `/admin/cms/pages/:id` | 页面编辑 | 内容 | `cms:manage` | sections、preview、publish、versions、rollback | ✅ |
| `/admin/members` | 会员列表 | 会员 | `user:read` | `GET /admin/users`、ban/unban | ⚠️ |
| `/admin/members/:id` | 会员详情 | 会员 | `user:read` + `user:ban` | detail（新）、points（新） | ❌ |
| `/admin/points/rules` | 积分规则 | 积分 | `points:manage` | `GET/PUT /admin/points/rules`、versions | ✅ |
| `/admin/points/adjust` | 积分调整 | 积分 | `points:manage` | accounts（新）、`POST /admin/points/adjust` | ⚠️ |
| `/admin/rbac/roles` | 角色权限 | 权限 | `rbac:manage` | `GET /admin/rbac/roles`、permissions | ✅ |
| `/admin/rbac/users` | 用户角色 | 权限 | `rbac:manage` | `GET /admin/rbac/user-roles`、POST/DELETE | ✅ |
| `/admin/audit/operations` | 操作日志 | 审计 | `audit:read` | `GET /admin/audit/operation-logs` | ⚠️ |
| `/admin/audit/logins` | 登录日志 | 审计 | `audit:read` | `GET /admin/audit/login-logs` | ⚠️ |
| `/admin/audit/security` | 安全事件 | 审计 | `audit:read` | `GET /admin/audit/security-events` | ⚠️ |
| `/admin/settings` | 系统设置 | 系统 | `settings:manage` | `GET/PUT /admin/system-settings` | ✅ |
| `/admin/reports` | 报表中心 | 报表 | 按报表 | reports（新）、export（新） | ❌ |
| `/admin/forbidden` | 403 | 兜底 | 登录 | — | — |
| `/:pathMatch(.*)*` | 404 | 兜底 | 公开 | — | — |

> 就绪度：✅ 现有接口可直接支撑；⚠️ 现有接口可用但缺字段/筛选；❌ 需要新增接口或管理列表。

> 权限列若含多个码：**第一个是路由进入权限，其余是按钮/操作权限**。路由守卫只校验读权限，操作按钮用 `PermissionGate` 单独校验。例如 `/admin/refunds` 进入只要 `order:read`，`refund:approve` 只控制「通过/驳回」按钮；不要把操作权限作为路由条件，否则只有读权限的角色会看不到页面。同一页面内不同 Tab 也按各自读权限显示，例如财务只有 `merchant:read`，则只显示商家 Tab，不显示店铺 Tab。

### 3.4 P0 页面区块与交互

| 页面 | 区块 | 必须展示 | 操作 |
|---|---|---|---|
| 工作台 | KPI 行（6 卡） | 实付 GMV、支付订单、客单价、支付转化率、退款率、新增用户 | 点击卡片跳转对应筛选列表 |
| 工作台 | 待办行（7 项） | 商品待审、商家待审、退款待处理、绿色待审、碳评估待核验、结算待确认、库存预警 | 点击进入对应队列 |
| 工作台 | 趋势图 | 近 30 日 GMV + 支付订单双轴 | 切换 7/30/90 日 |
| 工作台 | 分布图 | 订单状态环形图 | 点击扇区跳转订单列表 |
| 工作台 | Top 榜 | 品类 Top5、店铺 Top10 | 表格可排序 |
| 商品审核 | 筛选栏 | 关键词、店铺、分类；状态固定 `pending_review` | 重置、刷新 |
| 商品审核 | 队列表格 | 封面、标题、店铺、分类、价格区间、SKU 数、提交时间 | 行点击开抽屉 |
| 商品审核 | 详情抽屉 | 图集、标题/副标题/描述、SKU 表、绿色资料摘要、审核历史 | 通过、驳回 |
| 商家审核 | 表格 | 公司名、信用代码、法人、电话、地区、申请店铺名、申请时间 | 行点击开抽屉 |
| 商家审核 | 详情抽屉 | 资质图、字段、审核记录 | 通过（提示自动建店）、驳回 |
| 订单列表 | 状态 Tab | 全部 + 8 个状态 | 切换即筛选 |
| 订单列表 | 筛选栏 | 订单号/收货电话、店铺、创建日期范围 | 查询、重置、导出 |
| 订单列表 | 表格 | 订单号、买家（脱敏）、店铺、件数、实付、退款、状态、创建/支付时间 | 行点击进详情 |
| 订单详情 | 概览 | 订单号、状态、买家、收货信息、金额明细 | 查看退款、复制订单号 |
| 订单详情 | 子单区 | 店铺子单、条目快照、金额、退款额、可退额、物流 | 展开条目 |
| 订单详情 | 时间线 | 状态变更记录 | 只读 |
| 退款售后 | 状态 Tab | 待处理、已退款、已驳回、全部 | 默认待处理 |
| 退款售后 | 表格 | 退款单号、订单号、店铺、买家、金额、原因、状态、申请/处理时间 | 行点击开抽屉 |
| 退款售后 | 抽屉 | 订单摘要、可退金额、退款原因、处理记录 | 通过（Mock 原路退回）、驳回 |
| 结算单 | 工具条 | 店铺选择、周期选择、预览 | 预览后生成 |
| 结算单 | 预览面板 | 子单数、商品金额、佣金、应结、已结算跳过数 | 确认生成 |
| 结算单 | 表格 | 店铺、周期、商品金额、佣金、应结、状态、时间 | 确认、打款、明细 |
| 平台台账 | 筛选栏 | 类型、日期范围、订单号、店铺 | 查询、导出 |
| 平台台账 | 表格 | 时间、类型、关联单号、店铺、金额（正负色）、备注 | 只读 |

---

## 4. 角色权限与数据可见范围

### 4.1 权限模型

- 权限码共 **20 个**，定义在 `app/modules/rbac/service.py` 的 `PERMISSION_CATALOG`。
- 内置角色 **5 个**：`super_admin`、`ops_admin`、`product_auditor`、`finance_admin`、`cs_admin`。
- `super_admin` 通过 `is_super=true` 通配全部权限，不逐条绑定 `role_permissions`。
- 后端 `require_permissions(...)` 是 **AND** 语义：传入多个权限码时全部满足才放行。
- 前端权限只用于菜单/路由/按钮的体验层控制；**后端永远是权威**。

```ts
// 管理端权限码（与后端 PERMISSION_CATALOG 对齐）
export type PermissionCode =
  | 'user:read' | 'user:ban'
  | 'merchant:read' | 'merchant:review'
  | 'store:read' | 'store:manage'
  | 'product:read' | 'product:approve' | 'product:remove'
  | 'order:read' | 'refund:approve'
  | 'finance:read' | 'finance:manage'
  | 'points:manage'
  | 'cms:manage'
  | 'aid:manage'
  | 'green:review'
  | 'audit:read'
  | 'rbac:manage'
  | 'settings:manage'
  | 'dashboard:read' // 新增，见 §10
```

### 4.2 角色—功能矩阵（按当前 seed 配置）

| 功能/权限 | 超级管理员 | 运营管理员 | 商品审核员 | 财务管理员 | 客服管理员 |
|---|:---:|:---:|:---:|:---:|:---:|
| 工作台（现状：`order:read AND user:read`） | ✅ | ✅ | ❌ | ❌ | ✅ |
| 商品查看 `product:read` | ✅ | — | ✅ | — | ✅ |
| 商品审核/下架 `product:approve/remove` | ✅ | — | ✅ | — | — |
| 商家查看 `merchant:read` | ✅ | ✅ | ✅ | ✅ | — |
| 商家审核 `merchant:review` | ✅ | — | — | — | — |
| 店铺查看 `store:read` | ✅ | ✅ | ✅ | — | — |
| 店铺状态 `store:manage` | ✅ | — | — | — | — |
| 订单查看 `order:read` | ✅ | ✅ | — | ✅ | ✅ |
| 退款处理 `refund:approve` | ✅ | — | — | ✅ | ✅ |
| 财务查看 `finance:read` | ✅ | — | — | ✅ | — |
| 财务结算 `finance:manage` | ✅ | — | — | ✅ | — |
| 绿色审核 `green:review` | ✅ | — | ✅ | — | — |
| 助农管理 `aid:manage` | ✅ | ✅ | — | — | — |
| CMS 内容 `cms:manage` | ✅ | ✅ | — | — | — |
| 会员查看 `user:read` | ✅ | ✅ | — | — | ✅ |
| 封禁/解封 `user:ban` | ✅ | ✅ | — | — | — |
| 积分管理 `points:manage` | ✅ | — | — | — | — |
| RBAC `rbac:manage` | ✅ | — | — | — | — |
| 审计日志 `audit:read` | ✅ | ✅ | — | — | — |
| 系统设置 `settings:manage` | ✅ | — | — | — | — |

> 这张表是**当前代码事实**，不是建议值。工作台行按现状 `order:read AND user:read` 计算；若采纳 §4.3 建议新增 `dashboard:read` 并授予全部管理角色，则 5 个角色均可用。建议调整见 §4.3 与 §14。

### 4.3 现状错配与建议

| # | 问题 | 现状/证据 | 影响 | 建议 |
|---|---|---|---|---|
| 1 | 工作台权限是 AND | `app/modules/admin/router.py`：`require_permissions("order:read","user:read")` | 财务（无 `user:read`）、商品审核员（两者都无）打开工作台直接 403 | 新增 `dashboard:read` 并授予全部管理角色；或改为 `require_any_permission` |
| 2 | 运营不能审商家 | `ops_admin` 无 `merchant:review` | 「运营管理员」看不到商家审核动作，只有超管能审 | 建议给 `ops_admin` 加 `merchant:review`；如合规要求双人复核，则保留 |
| 3 | 运营不能处理退款 | `ops_admin` 无 `refund:approve` | 退款只有财务/客服能处理 | 建议保持（退款归财务/客服），在文档中明确 |
| 4 | 财务看不到店铺名 | `finance_admin` 无 `store:read`；结算/台账 DTO 只返回 `store_id` | 财务页面只能显示 UUID | 优先在 DTO 里补 `store_name`；不建议为此扩大 `store:read` |
| 5 | 客服看不到店铺名 | `cs_admin` 无 `merchant:read/store:read`；订单列表无店铺字段 | 客服处理订单时无法识别店铺 | 在订单 DTO 补 `store_names`；不要依赖前端再查 |
| 6 | 商品审核接口要求两个权限 | `require_permissions("product:approve","product:remove")` | 只给 `approve` 的角色会被 403 | 拆成 `approve`/`reject`/`remove` 三个动作分别校验，或改 any |
| 7 | 高权限集中在超管 | `points:manage`、`settings:manage`、`rbac:manage` 仅超管 | 单点故障，超管请假则无法处理 | 至少指定一名副超管；或拆出 `points:read` 给财务 |
| 8 | 审计只读也仅超管/运营 | `audit:read` 仅 `super_admin/ops_admin` | 财务无法自查操作 | 可给 `finance_admin` 只读审计（建议 P2） |

### 4.4 数据可见范围

| 维度 | 现状 | 管理端要求 |
|---|---|---|
| 行级范围 | **所有管理角色都是全平台**；`data_scopes` 表只有 `global/store` 两条字典，未被任何查询使用 | 首版明确不支持「区域/店铺级管理员」；不要在前端假装有 |
| 字段级 | 订单详情返回完整收货人姓名/电话/地址；用户列表返回邮箱；商家列表返回信用代码 | 列表默认脱敏（手机号 `138****0001`、邮箱 `a***@x.com`）；详情页可看全量；如合规更严，后端按权限脱敏 |
| 导出 | 无导出接口 | 导出必须：按数据集校验权限、默认脱敏、记录审计、限制 5 万行 |
| 敏感操作 | 封禁、退款通过、结算打款、积分调整、设置写入、角色授予 | 必须二次确认 + 原因（后端支持时）+ 结果反馈；可选 `X-MFA-Code` |
| 会话 | access 30 分钟、refresh 14 天、封禁撤销全部会话 | 401 刷新一次；刷新失败清会话；封禁后对方下一次请求即失效 |

> 如果未来要做区域/店铺级数据权限，最小改造是：`user_roles` 增加 `scope_type/scope_id`，在 `require_permissions` 之后追加 `apply_scope(stmt, user)`，并为订单/商品/店铺/结算查询统一注入。不要在首版偷偷用前端过滤代替。

**禁止展示字段**：`password_hash`、`mfa_secret`、`refresh_token_hash`、`SECRET_KEY`、`MOCK_PAYMENT_SECRET`、数据库连接串。管理端任何页面/导出/日志都不得出现；若后端误返回，前端必须过滤并提后端修复。

### 4.5 前端权限实现

```ts
// router/routes.ts
{
  path: 'products/review',
  name: 'product-review',
  component: () => import('@/views/products/ProductReviewView.vue'),
  meta: { title: '商品审核', permission: 'product:read', nav: true, group: '商品' }
}

// router/guards.ts
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  if (!auth.isAuthenticated) return { name: 'login', query: { redirect: to.fullPath } }
  if (!auth.ready) await auth.loadMe()
  const required = to.meta.permission as PermissionCode | undefined
  if (required && !auth.can(required)) return { name: 'forbidden' }
  return true
})
```

- 菜单从路由表生成，只渲染 `meta.nav && auth.can(meta.permission)` 的项。
- 403 页面显示「当前账号无此权限」+ 返回工作台；**不清理 token**。
- 按钮级：`<PermissionGate code="refund:approve">`，无权限时不渲染，而不是禁用后让用户猜。
- 权限变更后要求重新登录（或至少重新拉 `/admin/me`），避免前端缓存旧权限。

---

## 5. 关键指标、图表与报表

### 5.1 指标口径总表

> 所有指标由后端计算并返回；前端只格式化。金额单位元，比率用 0–1 小数，前端显示为百分比。
> GMV = 商品交易总额；本文默认「实付 GMV」，另有「商品 GMV」「净 GMV」分项，报表必须写明用的是哪一个。

| # | 指标 | 定义/公式 | 数据源 | 备注 |
|---|---|---|---|---|
| M01 | 实付 GMV | `SUM(orders.pay_amount)`，条件 `paid_at ∈ [start,end)` 且 `status ∉ (pending_payment, cancelled)` | `orders` | 含运费、扣积分后；主指标 |
| M02 | 商品 GMV | `SUM(orders.items_total)`，同一时间与状态条件 | `orders` | 不含运费，用于商家结算参考 |
| M03 | 净 GMV | 实付 GMV − `SUM(refunds.amount)`，退款条件 `status='refunded'` 且 `handled_at ∈ [start,end)` | `orders`、`refunds` | 退款按处理时间，非原订单时间 |
| M04 | 支付订单数 | `COUNT(DISTINCT orders.id)`，`paid_at ∈ [start,end)` | `orders` | 不按当前状态排除退款单 |
| M05 | 新建订单数 | `COUNT(*)`，`created_at ∈ [start,end)` | `orders` | 含未支付/取消 |
| M06 | 客单价 | 实付 GMV ÷ 支付订单数 | 派生 | 分母为 0 时返回 `"0.00"` |
| M07 | 支付转化率 | 同一批「创建于区间内」的订单中，`paid_at IS NOT NULL` 的占比 | `orders` | 必须按创建 cohort；新近 cohort 未成熟，页面标注「截至当前」 |
| M08 | 退款率 | 退款金额 ÷ 实付 GMV | `refunds`、`orders` | 同期口径；报表可另做「同批订单退款率」 |
| M09 | 新增注册 | `COUNT(users)`，`created_at ∈ [start,end)` | `users` | 含商家/管理员；页面标注「注册账号」 |
| M10 | 活跃买家 | `COUNT(DISTINCT user_id)`，区间内有支付订单 | `orders` | 排除管理员账号 |
| M11 | 复购买家 | 区间内支付订单数 ≥ 2 的买家数 | `orders` | P2 报表 |
| M12 | 待审商品 | `COUNT(products)`，`status='pending_review'` | `products` | 工作台待办 |
| M13 | 待审商家 | `COUNT(merchants)`，`status='pending_review'` | `merchants` | 工作台待办 |
| M14 | 待处理退款 | `COUNT(refunds)`，`status='requested'` | `refunds` | 工作台待办 |
| M15 | 待审绿色资料 | `COUNT(product_green_profiles)`，`status='pending_review'` | `green` | 工作台待办 |
| M16 | 待核验碳评估 | `COUNT(carbon_assessments)`，`verified=false` | `green` | 工作台待办 |
| M17 | 待确认结算 | `COUNT(merchant_settlements)`，`status='pending'` | `finance` | 工作台待办 |
| M18 | 库存预警 | `COUNT(inventories)`，`quantity_total - quantity_reserved <= threshold` | `inventories` | 阈值默认 10，放 `system_settings` |
| M19 | 绿色商品占比 | 分子：`is_listed=true AND status='approved'` 且有 `approved` 绿色资料的商品数；分母：`is_listed=true AND status='approved'` 商品数 | `products`、`green` | 明确分子/分母，避免把待审算进去 |
| M20 | 助农筹资进度 | `SUM(raised_amount) ÷ SUM(goal_amount)`，仅 `status='published'` 且 `goal_amount > 0` | `aid_projects` | 无目标金额的项目不计入分母 |
| M21 | 积分余额（负债） | `SUM(point_accounts.balance)` | `points` | 只算存量，不等于可兑付 |
| M22 | 积分流转 | 按 `type` 分别 `SUM(amount)`：earn/spend/reverse/adjust | `point_transactions` | `amount` 带符号；前端展示绝对值并标注方向 |

### 5.2 工作台布局

```
┌──────────────────────────────────────────────────────────────┐
│ 工作台   日期 [近30天 ▾]  刷新   数据截至 12:18              │
├──────────┬──────────┬──────────┬──────────┬──────────┬────────┤
│ 实付GMV  │ 支付订单 │ 客单价   │ 支付转化 │ 退款率   │ 新增注册│
│ ¥12,345  │ 128      │ ¥96.45   │ 68.2%    │ 2.1%     │ 36     │
├──────────┴──────────┴──────────┴──────────┴──────────┴────────┤
│ 待办：商品待审 12 · 商家待审 3 · 退款 5 · 绿色 8 · 碳核验 4 · 结算 2 · 库存预警 6 │
├──────────────────────────────────┬───────────────────────────┤
│ GMV / 订单趋势（双轴，近30日）    │ 订单状态分布（环形）       │
├──────────────────────────────────┼───────────────────────────┤
│ 品类销售 Top5（横向条形）         │ 店铺销售 Top10（表格）     │
├──────────────────────────────────┼───────────────────────────┤
│ 助农项目进度（进度条列表）        │ 绿色占比 / 积分概览        │
└──────────────────────────────────┴───────────────────────────┘
```

交互要求：

- 日期切换 7/30/90 天；默认 30 天；`date_to` 含当天。
- 每张 KPI 卡可点击，跳到带相同日期范围的对应列表。
- 待办项点击跳转到对应队列，默认筛选「待处理」。
- 单个区块 403 时只隐藏该区块并显示「无权限查看」，不要让整页失败。
- 页面显示「数据截至 HH:mm」，并支持手动刷新；前端缓存不超过 60 秒。

### 5.3 图表清单

| # | 图表 | 类型 | 维度 | 指标 | 依赖接口 | 优先级 |
|---|---|---|---|---|---|---|
| C01 | GMV/订单趋势 | 双轴折线+柱 | 日 | M01、M04 | `overview.trend` | P0 |
| C02 | 订单状态分布 | 环形 | 状态 | M05 按状态 | `overview.order_status` | P0 |
| C03 | 品类销售 Top5 | 横向条形 | 品类 | `SUM(order_items.subtotal)` | `overview.category_top` | P1 |
| C04 | 店铺销售 Top10 | 表格/条形 | 店铺 | `SUM(store_orders.items_total)`，限已支付未取消子单 | `overview.store_top` | P1 |
| C05 | 助农项目进度 | 进度条列表 | 项目 | `raised/goal` | `overview.aid` | P1 |
| C06 | 绿色商品占比 | 环形/指标卡 | 平台 | M19 | `overview.green` | P2 |
| C07 | 积分流转 | 堆叠柱 | 日/类型 | M22 | `overview.points` | P2 |
| C08 | 商品审核时效 | 条形 | 审核人/周 | 平均小时 | 报表接口 | P2 |

> 地图类图表 P0/P1 不做。区域分析用横向条形图；如果后续必须做地图，需使用合规底图（天地图/高德等）并遵循审图号要求，不能直接使用未经审核的 GeoJSON。

### 5.4 报表清单

| # | 报表 | 行维度 | 列 | 筛选 | 导出 | 优先级 |
|---|---|---|---|---|---|---|
| R01 | 交易日报/月报 | 日或月 | 新建订单、支付订单、实付 GMV、商品 GMV、退款额、净 GMV、客单价、支付转化率 | 日期、店铺 | CSV | P2 |
| R02 | 商家结算对账单 | 店铺 × 周期 | 完成子单数、商品金额、佣金、应结、状态、生成/确认/打款时间 | 店铺、周期、状态 | CSV | P1 |
| R03 | 商品审核效率 | 周/审核人 | 提交数、通过数、驳回数、平均时效、Top 驳回原因 | 日期、审核人 | CSV | P2 |
| R04 | 退款分析 | 日/店铺 | 申请数、通过数、驳回数、退款额、退款率、Top 原因 | 日期、店铺、状态 | CSV | P2 |
| R05 | 会员增长与复购 | 日/月 | 新增注册、首购人数、复购买家、复购率、客单价 | 日期 | CSV | P2 |
| R06 | 积分负债与流转 | 日/月 | 期初、发放、消耗、冲正、调整、期末余额 | 日期 | CSV | P2 |
| R07 | 审计操作统计 | 日/操作人 | 操作数、动作 Top、资源 Top | 日期、操作人 | CSV | P2 |

报表实现约束：

- 固定报表，不做自定义维度/SQL 拖拽。
- 单次查询范围 ≤ 366 天；超过返回 `INVALID_DATE_RANGE`。
- 报表数字必须能与同筛选条件的列表 `pagination.total` / 汇总对账，差异为 0.00。
- 导出走独立接口，不受分页限制；上限 5 万行，超过返回 `EXPORT_TOO_LARGE`。

### 5.5 口径红线

| # | 红线 | 说明 |
|---|---|---|
| 1 | 前端不做权威汇总 | 表格「本页合计」可以前端算，但必须标注「本页」；全量汇总一律用后端 `summary` |
| 2 | 毛 GMV 与净 GMV 必须分名 | 不允许只写「GMV」而不说明是否扣退款 |
| 3 | 退款率分母写清楚 | 默认「同期退款额 ÷ 同期实付 GMV」，不是「退款订单数 ÷ 订单数」 |
| 4 | 支付转化率按 cohort | 分母是区间内创建的订单，分子是其中已支付的订单 |
| 5 | 碳数据不聚合 | 未核验的 `co2e_per_unit` 不得汇总成「平台减排量」；最多展示「已核验商品数/覆盖率」和单商品单位碳足迹 |
| 6 | 时区统一 | 后端 UTC 存储；管理端筛选与图表按 `Asia/Shanghai` 日切；`date_to` 含当天 |
| 7 | 演示数据必须扩样 | 当前 7 笔订单无法验证趋势/分布；D0 生成 ≥200 笔、覆盖 30 天的演示订单 |
| 8 | 不虚构指标 | 后端没有评价、销量、优惠券、发票字段；不要在前端造「销量榜」「好评率」等管理指标 |

---

## 6. 查询筛选与操作流程

### 6.1 列表页统一规范

| 项 | 规范 |
|---|---|
| URL 状态 | 所有筛选、分页写入 query：`?status=&keyword=&date_from=&date_to=&page=1&page_size=20`；刷新/回退可恢复 |
| 筛选触发 | 输入框 300ms 防抖；下拉/日期选择立即触发；回车立即查询 |
| 分页 | 筛选变化重置 `page=1`；每页 20/50/100；后端上限 100 |
| 排序 | 审核/退款队列 `created_at ASC`（先到先处理）；其他 `created_at DESC`；结算 `period_end DESC` |
| 四态 | loading 骨架、empty 空态、error 错误重试、forbidden 无权限；四者都必须有 |
| 空态区分 | 「暂无数据」与「无匹配结果」分开；后者给「清除筛选」 |
| 行操作 | 主操作 1 个 + 更多菜单；危险操作红色且二次确认 |
| 删除末页 | 操作后若当前页为空且 `page>1`，自动回上一页 |
| 批量 | P0 不做；P2 只允许批量导出，不允许批量审核/退款 |

日期范围统一转换（禁止页面手写 `new Date()` 拼接）：

```ts
// utils/dateRange.ts
export function toUtcRange(dateFrom: string, dateTo: string) {
  const start = new Date(`${dateFrom}T00:00:00+08:00`)
  const end = new Date(`${dateTo}T00:00:00+08:00`)
  const endExclusive = new Date(end.getTime() + 24 * 60 * 60 * 1000) // 末日次日 00:00+08
  return { startUtc: start.toISOString(), endUtcExclusive: endExclusive.toISOString() }
}
```

- 列表接口的 `date_from/date_to` 直接传 `YYYY-MM-DD`，由后端按 `Asia/Shanghai` 解释；
- 结算预览/生成的 `period_start/period_end` 用 `toUtcRange()` 转成 ISO UTC，`period_end` 取 `endUtcExclusive`；
- 展示时把 UTC 转回 `Asia/Shanghai`，结算周期显示时对 `period_end` 减 1 天。

### 6.2 筛选条件总表

| 页面 | 筛选条件 | 默认排序 | 默认页大小 | 备注 |
|---|---|---|---|---|
| 商品审核 | `keyword`（标题）、`store_id`、`category_id`；状态固定 `pending_review` | `created_at ASC` | 20 | 先到先审 |
| 商品库 | `status`、`keyword`、`store_id`、`category_id`、`date_from/date_to` | `created_at DESC` | 20 | 日期按创建时间 |
| 商家审核 | `keyword`（公司名/信用代码）、状态固定 `pending_review` | `created_at ASC` | 20 | 先到先审 |
| 商家与店铺 | `status`、`keyword`、`merchant_id` | `created_at DESC` | 20 | 商家/店铺两个 Tab |
| 订单 | `status`、`keyword`（订单号/收货电话）、`store_id`、`date_from/date_to` | `created_at DESC` | 20 | 日期按创建时间 |
| 退款 | `status`、`order_no`、`store_id`、`date_from/date_to` | `created_at ASC`（待处理）/ `DESC`（其他） | 20 | 默认 `requested` |
| 结算 | `status`、`store_id`、`period_start/period_end` | `period_end DESC` | 20 | 周期按本地日 |
| 台账 | `entry_type`、`date_from/date_to`、`order_id`、`store_id` | `created_at DESC` | 20 | 只读 |
| 绿色资料 | `status`、`keyword`（商品名）、`store_id` | `updated_at ASC`（待审） | 20 | 未核验单独标识 |
| 助农项目 | `status`、`keyword` | `created_at DESC` | 20 | 含草稿 |
| 会员 | `keyword`（邮箱/昵称）、`status`、`role`、`date_from/date_to` | `created_at DESC` | 20 | 角色筛选 P1 |
| 积分规则 | 无 | `code ASC` | — | 少量数据 |
| 积分流水 | `user_id`、`type`、`date_from/date_to` | `created_at DESC` | 20 | 先选会员再进 |
| 审计-操作 | `action`、`resource`、`user_id`、`date_from/date_to` | `created_at DESC` | 50 | 只读 |
| 审计-登录 | `email`、`success`、`date_from/date_to` | `created_at DESC` | 50 | 只读 |
| 审计-安全 | `kind`、`date_from/date_to` | `created_at DESC` | 50 | 只读 |

### 6.3 关键操作流程

#### 流程 1：商品审核

1. 进入 `/admin/products/review`，默认加载 `status=pending_review&page=1&page_size=20&sort=created_at asc`。
2. 行点击打开抽屉：`GET /admin/products/{id}`（新）；若暂未实现，用列表行 + `GET /admin/products/{id}/audit-records`。
3. 抽屉展示图集、标题、SKU 与价格、库存、绿色资料摘要、审核历史。
4. 点击「通过」→ 二次确认 → `POST /admin/products/{id}/audit` `{action:"approve"}`。
5. 点击「驳回」→ 原因必填（2–255 字，快捷原因：资质不全/图片不合规/描述不符/价格异常/其他）→ `{action:"reject", reason}`。
6. 成功后：关闭抽屉、刷新当前页、待办数减 1、Toast「已通过/已驳回」。
7. 失败分支：`409 CONFLICT` 提示「商品状态已变化，已刷新」；`403` 提示缺少权限；`422` 展示首条字段错误。

#### 流程 2：商家入驻审核

1. `GET /admin/merchants?status=pending_review`。
2. 抽屉展示 `company_name/license_no/license_url/legal_person/contact_phone/region/initial_store_name/created_at`。
3. 通过：确认文案必须写明「通过后将自动创建店铺「{initial_store_name}」并绑定店主」→ `POST /admin/merchants/{id}/review` `{action:"approve"}`。
4. 驳回：原因必填 → `{action:"reject", reason}`。
5. 成功后刷新队列；通过后提供「查看店铺」链接（`/admin/merchants?tab=stores&merchant_id=...`）。
6. 失败：`MERCHANT_STATE_INVALID` 提示状态不允许；`409` 提示刷新。

#### 流程 3：退款处理

1. `GET /admin/refunds?status=requested`；默认按申请时间升序。
2. 抽屉加载退款单、订单摘要、子单可退金额、退款原因、历史处理记录。
3. 通过：确认文案「将通过 Mock 渠道原路退回 ¥{amount}，同时冲正积分并写入平台台账（仿真，无真实资金流）」→ `POST /admin/refunds/{id}/handle` `{action:"approve", note?}`。
4. 驳回：备注必填 → `{action:"reject", note}`。
5. 成功后刷新；若订单详情已打开，需重新拉取订单状态。
6. 失败：`CONFLICT` 表示退款单已被处理；`REFUND_EXCEED_LIMIT` 不会在管理员处理阶段出现，但需保留提示。

#### 流程 4：结算单

1. 工具条选择店铺 + 本地日周期（含首尾）→ 点击「预览」。前端转换为：`period_start = 首日 00:00+08`、`period_end = 末日次日 00:00+08`（**排他上界**），均以 ISO UTC 发送。
2. `GET /admin/finance/settlements/preview?store_id=&period_start=&period_end=`（新）返回：可结算子单数、商品金额、佣金、应结、已结算跳过数、样例明细。
3. 确认无误 → `POST /admin/finance/settlements/generate` `{store_id, period_start, period_end}`（同上，ISO UTC，`period_end` 排他）。
4. 生成成功 → 列表刷新，状态 `pending`。
5. 确认 → `POST /admin/finance/settlements/{id}/confirm`；打款 → `POST .../mark-paid`（仿真，无真实资金流）。
6. 失败：`CONFLICT`「该店铺此周期已生成结算单」；不要自动重试，提示用户改周期或查看已有单。

#### 流程 5：绿色资料与碳核验

1. `GET /admin/green/profiles?status=pending_review`。
2. 抽屉展示商品、产地、种植方式、认证列表、描述、最新碳评估（含 `verified`）。
3. 资料审核：`POST /admin/green/profiles/{id}/review` `{action:"approve|reject", reason?}`。
4. 碳核验：`POST /admin/green/assessments/{id}/verify` `{action:"approve|reject", reason}`；`approve` 即 `pass`，`reject` 即 `fail`。
5. 页面必须始终显示「未核验/已核验」标签；不得把 `verified=false` 渲染成已认证。
6. 失败：`CONFLICT`「当前状态不可审核」；刷新。

#### 流程 6：助农项目与合作社

1. 先在 `/admin/aid/cooperatives` 创建合作社：`POST /admin/aid/cooperatives?name=&region=&description=`（当前是 query 参数，不是 JSON；前端需按此发送）。
2. 在 `/admin/aid/projects` 新建项目：`POST /admin/aid/projects` `{cooperative_id, title, cover_url?, description?, goal_amount?}`，默认 `draft`。
3. 发布：`POST /admin/aid/projects/{id}/review` `{action:"publish"}`；下线：`{action:"offline"}`。
4. 失败：合作社不存在 `NOT_FOUND`；状态不允许 `CONFLICT`。

#### 流程 7：CMS 公告与 Banner

1. 公告：`POST /cms/announcements` `{title, content}` → 草稿；`POST /cms/announcements/{id}/publish` 发布；`POST .../offline` 下线。
2. Banner：`POST /cms/banners` `{title, image_url, link_type, link_url, sort, enabled}`；`PUT /cms/banners/{id}` 更新。
3. 当前 `BannerIn`/`AnnouncementIn` **没有 `start_at/end_at`**，管理端不要显示「定时生效」控件；如需该能力，先补后端字段（见 §10）。
4. 当前没有管理端 Banner/公告列表接口；P1 先补 `GET /admin/cms/banners`、`GET /admin/cms/announcements`，否则只能「盲创建」。
5. 图片上传：P1 补 `POST /admin/uploads`，返回 `{url}`；在未实现前，允许手填 `/uploads/...` 或 `https://...`，并在 UI 标注「需先上传素材」。

#### 流程 8：会员封禁与积分调整

1. 会员列表 `GET /admin/users?keyword=`；行内「封禁」→ 原因必填（2–255 字）→ `POST /admin/users/{id}/ban` `{reason}`。
2. 封禁成功后该用户全部会话被撤销；提示「已封禁并撤销 N 个会话」。
3. 解封：`POST /admin/users/{id}/unban`，二次确认。
4. 积分调整：先搜索用户 → 展示当前余额（新接口）→ 输入 `delta`（非零整数，正加负减）+ 原因（≥2 字）→ `POST /admin/points/adjust` `{user_id, delta, reason}`。
5. 成功后展示 `balance_after`；失败 `POINTS_INSUFFICIENT`（扣减过多）或 `NOT_FOUND`。

### 6.4 错误码与 UI 映射

| 错误码 | HTTP | UI 行为 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 展示 `data.errors[0].message`；表单字段标红 |
| `UNAUTHENTICATED` / `TOKEN_EXPIRED` | 401 | 静默刷新一次；失败清会话跳登录 |
| `FORBIDDEN` | 403 | 页面级 403 或按钮隐藏；**不登出** |
| `ACCOUNT_DISABLED` | 403 | 清会话，提示账号被禁用 |
| `NOT_FOUND` | 404 | 空态/「资源不存在」，提供返回列表 |
| `CONFLICT` / `MERCHANT_STATE_INVALID` / `ORDER_STATE_INVALID` | 409 | 提示状态已变化，自动刷新当前数据 |
| `INSUFFICIENT_STOCK` / `PRICE_CHANGED` | 409 | 管理端一般不触发；若触发，提示刷新 |
| `REFUND_NOT_ALLOWED` / `REFUND_EXCEED_LIMIT` | 409 | 展示后端 message，保留表单 |
| `POINTS_INSUFFICIENT` | 409 | 展示当前余额与可扣上限 |
| `CMS_COMPONENT_UNKNOWN` | 422 | 页面编辑器提示「组件类型不在白名单」 |
| `CMS_PAGE_NOT_PUBLISHED` | 404 | 预览不存在，提示先发布 |
| `EXPORT_TOO_LARGE`（新增） | 409 | 提示缩小日期范围或加筛选 |
| `RATE_LIMITED` | 429 | Toast「请求过于频繁」，指数退避 |
| `INTERNAL_ERROR` | 500 | Toast + `request_id` 可复制 |

### 6.5 防重与幂等

| 场景 | 要求 |
|---|---|
| 所有提交按钮 | 提交中禁用 + loading；成功/失败后恢复；不允许双击发两次 |
| 退款处理 | 打开抽屉即锁定退款单 id；提交后即使失败也先刷新状态 |
| 结算生成 | 前端不自动重试；`409` 视为「已生成」，引导查看 |
| 积分调整 | 一次只允许一个弹窗；成功后关闭并刷新流水 |
| 封禁/解封 | 二次确认；成功后刷新行 |
| GET 请求 | 超时/网络错误可重试 1 次；401 刷新由 `http.ts` 处理 |
| POST 请求 | 除后端明确支持幂等键的接口外，不自动重试 |

---

## 7. 可复用的项目能力

### 7.1 可直接复用/改造的资产

| 能力 | 位置 | 复用方式 | 注意事项 | 复用等级 |
|---|---|---|---|---|
| 统一请求层 | `src/api/http.ts` | 复制到 `admin/src/api/http.ts` | 改 token key（`tanhui_admin_access_token`）、API base；保留 401 刷新/错误码/`request_id` | 直接 |
| Service 分层 | `src/api/index.ts` | 参考写法，按域拆 `admin/orders.ts` 等 | 页面不直接 fetch | 参考 |
| 类型组织 | `src/api/types.ts` | 参考命名与 DTO 风格 | 管理端单独 `types.ts`，避免消费者类型污染 | 参考 |
| 四态组件 | `src/components/StateBlock.vue` | 复制改造 | 可换成 `el-skeleton/el-empty/el-result`，但保留统一 API | 改造 |
| 分页组件 | `src/components/PaginationBar.vue` | 建议替换 | 用 `el-pagination`，支持 20/50/100 与总数 | 参考 |
| Toast | `src/components/ToastHost.vue`、`src/stores/toast.ts` | 保留或换 `ElMessage` | 错误 Toast 必须能展示/复制 `request_id` | 改造 |
| 二次确认 | `src/components/ConfirmHost.vue`、`src/stores/confirm.ts` | 换 `ElMessageBox.confirm` | 保留 Promise 化调用习惯 | 改造 |
| 订单状态标签 | `src/components/OrderStatusTag.vue` | 复制扩展 | 管理端需要 8 个订单状态 + 4 个退款状态 + 结算状态 | 改造 |
| 金额展示 | `src/components/PriceTag.vue` | 改为 `MoneyText` | 只格式化字符串，不做运算 | 改造 |
| 格式化工具 | `src/utils/format.ts` | 复制扩展 | 增加管理端枚举、时区、脱敏；删除消费者专用映射 | 直接 |
| 设计 Token | `src/assets/main.css` 顶部 | 抽取 `--green-*`、`--cream`、`--gold`、`--price`、字体 | **不要整文件复制 7146 行** | 部分 |
| Vite 代理 | `vite.config.ts` | 复制 | 端口 5176、`base:'/admin/'`、代理 `/api` 与 `/uploads` | 直接 |
| Playwright 冒烟 | `scripts/smoke.mjs` | 参考流程与断言方式 | 写 `admin-smoke.mjs`，用 5 个角色账号跑权限 | 参考 |
| 截图脚本 | `scripts/visual.mjs` | 参考 | 1440/1280 两档；关键页截图入 `artifacts/` | 参考 |
| 演示数据 | `scripts/seed_demo.py` | 扩展 | 生成 ≥200 笔、30 天订单，供图表验证 | 改造 |
| 页面-API 对照 | `docs/page-api-map.md` | 复制表格格式 | 新增 `docs/admin-page-api-map.md` 或在本文 §3.3 维护 | 直接 |
| RBAC 权限码 | `tanhui-backend/app/modules/rbac/service.py` | 直接读取 | 前端权限码必须与后端一致，禁止自造 | 直接 |
| OpenAPI | `tanhui-backend/docs/openapi.yaml` | `openapi-typescript` 生成 | 新增接口后重新导出 | 直接 |

### 7.2 明确不要复用

| 资产 | 原因 |
|---|---|
| `SiteHeader` / `SiteFooter` / `HomeCarousel` | 消费者视觉语言，信息密度低，不适合管理端 |
| `main.css` 全量 | 7146 行含大量消费者页面样式，会拖慢构建并造成选择器冲突 |
| `maplibre-gl` / `deck.gl` / `OriginMapStage` | 包体大、与后台表格无关；区域分析用条形图 |
| `CmsSectionRenderer` | 消费者渲染器只读已发布页面；管理端需要编辑态，不复用 |
| `cart` / `checkout` stores | 与管理端无关 |
| 消费者路由守卫 | 只判断 `requiresAuth`，没有权限码概念 |
| `productFallbackImage` 等演示兜底 | 管理端不能给缺失图片造假；应显示「无图」占位 |
| `pointsCopy`（绿豆→绿色积分） | 管理端统一用「绿色积分（绿豆）」；不要做消费者文案替换 |

### 7.3 复用后的工程结构

```
tanhui-admin/
├─ src/
│  ├─ api/
│  │  ├─ http.ts             # 复制改造
│  │  ├─ admin.ts            # 按域聚合导出
│  │  ├─ types.ts            # 管理端 DTO + ViewModel
│  │  └─ schema.d.ts         # openapi-typescript 生成（可选）
│  ├─ components/
│  │  ├─ layout/             # AdminLayout、SideNav、TopBar、PageHeader
│  │  ├─ common/             # DataTable、FilterBar、StatusTag、MoneyText、ReasonDialog
│  │  └─ charts/             # KpiCard、ChartCard、TrendChart、DonutChart、BarChart
│  ├─ composables/
│  │  ├─ useTableQuery.ts    # URL 同步、分页、筛选、刷新
│  │  ├─ usePermission.ts    # can/canAny
│  │  └─ useExport.ts        # 下载与错误处理
│  ├─ constants/
│  │  ├─ permissions.ts
│  │  └─ labels.ts           # 所有枚举中文文案
│  ├─ layouts/AdminLayout.vue
│  ├─ router/
│  │  ├─ index.ts
│  │  ├─ routes.ts
│  │  └─ guards.ts
│  ├─ stores/
│  │  ├─ auth.ts
│  │  └─ app.ts              # 侧边栏折叠、环境标识
│  ├─ styles/
│  │  ├─ tokens.css          # 从消费者端抽取
│  │  ├─ base.css
│  │  └─ admin.css
│  ├─ utils/
│  │  ├─ format.ts
│  │  ├─ dateRange.ts        # 本地日 ↔ UTC
│  │  └─ mask.ts             # 手机号/邮箱/地址脱敏
│  └─ views/
│     ├─ auth/LoginView.vue
│     ├─ dashboard/DashboardView.vue
│     ├─ orders/...
│     ├─ refunds/...
│     ├─ products/...
│     ├─ merchants/...
│     ├─ finance/...
│     ├─ green/...
│     ├─ aid/...
│     ├─ cms/...
│     ├─ members/...
│     ├─ points/...
│     ├─ rbac/...
│     ├─ audit/...
│     ├─ settings/...
│     ├─ reports/...
│     └─ system/{ForbiddenView,NotFoundView}.vue
├─ scripts/
│  ├─ admin-smoke.mjs
│  ├─ visual.mjs
│  └─ contract-check.mjs     # 校验 openapi 中必需接口存在
├─ .env.example
├─ vite.config.ts
├─ tsconfig.json
└─ package.json
```

---

## 8. 所需接口与数据来源

### 8.1 已有管理接口（55 个）

> 以下为当前后端**已实现**的接口，标注了权限与已知缺口。AI 开发不得臆造路径。

```text
# 工作台 / 系统设置 / 用户（6）
GET    /api/v1/admin/dashboard/stats              order:read AND user:read   # 指标少、权限 AND、待办硬编码
GET    /api/v1/admin/system-settings              settings:manage
PUT    /api/v1/admin/system-settings              settings:manage
GET    /api/v1/admin/users                        user:read                  # 仅 email 筛选
POST   /api/v1/admin/users/{user_id}/ban          user:ban                   # body: {reason}
POST   /api/v1/admin/users/{user_id}/unban        user:ban

# 商品审核（3）
GET    /api/v1/admin/products                     product:read               # status/store_id；无 keyword/category
GET    /api/v1/admin/products/{product_id}/audit-records  product:read
POST   /api/v1/admin/products/{product_id}/audit  product:approve AND product:remove
                                                    # body: {action: approve|reject|remove, reason?}

# 订单 / 退款（4）
GET    /api/v1/admin/orders                       order:read                 # 仅 status
GET    /api/v1/admin/orders/{order_id}            order:read                 # 无买家邮箱/物流
GET    /api/v1/admin/refunds                      order:read                 # 仅 status
POST   /api/v1/admin/refunds/{refund_id}/handle   refund:approve             # body: {action: approve|reject, note?}

# 财务（5）
GET    /api/v1/admin/finance/settlements          finance:read               # 仅 status；无 store_name
POST   /api/v1/admin/finance/settlements/generate finance:manage             # body: {store_id, period_start, period_end}
POST   /api/v1/admin/finance/settlements/{id}/confirm  finance:manage
POST   /api/v1/admin/finance/settlements/{id}/mark-paid finance:manage
GET    /api/v1/admin/finance/ledger               finance:read               # 仅 entry_type；无 store_name/order_no

# 商家 / 店铺（4）
GET    /api/v1/admin/merchants                    merchant:read              # 仅 status
POST   /api/v1/admin/merchants/{merchant_id}/review merchant:review          # approve|reject|freeze|unfreeze
GET    /api/v1/admin/stores                       store:read                 # 仅 status
POST   /api/v1/admin/stores/{store_id}/status     store:manage               # suspend|activate|close

# 绿色（3）
GET    /api/v1/admin/green/profiles               green:review               # 仅 status；无商品名/评估 id
POST   /api/v1/admin/green/profiles/{id}/review   green:review               # approve|reject
POST   /api/v1/admin/green/assessments/{id}/verify green:review              # approve|reject → pass|fail

# 助农（4）
GET    /api/v1/admin/aid/projects                 aid:manage                 # 仅 status
POST   /api/v1/admin/aid/projects                 aid:manage                 # body: {cooperative_id,title,cover_url?,description?,goal_amount?}
POST   /api/v1/admin/aid/projects/{id}/review     aid:manage                 # publish|offline
POST   /api/v1/admin/aid/cooperatives             aid:manage                 # query: name,region,description

# 积分（4）
GET    /api/v1/admin/points/rules                 points:manage
GET    /api/v1/admin/points/rules/{id}/versions   points:manage
PUT    /api/v1/admin/points/rules/{code}          points:manage              # body: {config: dict}
POST   /api/v1/admin/points/adjust                points:manage              # body: {user_id, delta, reason}

# RBAC（5）
GET    /api/v1/admin/rbac/roles                   rbac:manage
GET    /api/v1/admin/rbac/permissions             rbac:manage
GET    /api/v1/admin/rbac/user-roles              rbac:manage                # email/page/page_size
POST   /api/v1/admin/rbac/users/{id}/roles        rbac:manage                # body: {role_code}
DELETE /api/v1/admin/rbac/users/{id}/roles/{code} rbac:manage

# 审计（3）
GET    /api/v1/admin/audit/operation-logs         audit:read                 # action/resource
GET    /api/v1/admin/audit/login-logs             audit:read                 # email
GET    /api/v1/admin/audit/security-events        audit:read                 # kind

# CMS 管理（14，前缀 /api/v1/cms，不是 /admin）
GET    /api/v1/cms/pages                          cms:manage
POST   /api/v1/cms/pages                          cms:manage                 # {page_key,title}
POST   /api/v1/cms/pages/{id}/sections            cms:manage                 # {section_type,sort,enabled,config}
PUT    /api/v1/cms/pages/{id}/sections/{sid}      cms:manage
DELETE /api/v1/cms/pages/{id}/sections/{sid}      cms:manage
POST   /api/v1/cms/pages/{id}/preview             cms:manage
POST   /api/v1/cms/pages/{id}/publish             cms:manage
GET    /api/v1/cms/pages/{id}/versions            cms:manage
POST   /api/v1/cms/pages/{id}/rollback/{vid}      cms:manage
POST   /api/v1/cms/announcements                  cms:manage                 # {title,content}
POST   /api/v1/cms/announcements/{id}/publish     cms:manage
POST   /api/v1/cms/announcements/{id}/offline     cms:manage
POST   /api/v1/cms/banners                        cms:manage                 # {title,image_url,link_type,link_url,sort,enabled}
PUT    /api/v1/cms/banners/{banner_id}            cms:manage
```

**使用红线**：

1. 管理端**不能**用消费者接口看非公开状态数据：
   - `GET /products/{id}` 只返回审核通过且上架商品；草稿/待审会 404。
   - `GET /green/products/{id}` 只返回 `approved` 绿色资料；待审看不到。
   - `GET /orders/{id}`、`GET /orders/{id}/refunds`、`GET /logistics/{order_id}` 都校验 `order.user_id == current_user`，管理员调用会 404。
2. 管理端**不能**用 `/client/*` 做 CMS 管理，它只返回已发布内容。
3. 所有写操作必须带 Bearer；401 刷新一次；403 不清 token。

### 8.2 必须新增/改造的接口（按优先级）

| ID | 方法与路径 | 类型 | 权限 | 用途 | 优先级 |
|---|---|---|---|---|---|
| N01 | `GET /admin/me` | 新增 | 登录且具管理角色 | 返回当前管理员角色/权限/is_super | P0 |
| N02 | `GET /admin/dashboard/overview` | 新增 | `dashboard:read` | KPI + 待办 + 趋势 + 分布 + Top | P0 |
| N03 | `GET /admin/products` | 改造 | `product:read` | 增加 keyword/category/date；返回 `AdminProductRow` | P0 |
| N04 | `GET /admin/products/{id}` | 新增 | `product:read` | 管理端商品详情（含 SKU/图/审核记录） | P0 |
| N05 | `GET /admin/orders` | 改造 | `order:read` | 增加 keyword/store/date；返回 `AdminOrderRow` + summary | P0 |
| N06 | `GET /admin/orders/{id}` | 改造 | `order:read` | 补买家、店铺名、物流、退款、状态时间线 | P0 |
| N07 | `GET /admin/refunds` | 改造 | `order:read` | 增加 order_id/order_no/store/date；补字段 | P0 |
| N08 | `GET /admin/finance/settlements` | 改造 | `finance:read` | 增加 store/period；补 store_name/item_count | P0 |
| N09 | `GET /admin/finance/settlements/{id}` | 新增 | `finance:read` | 结算明细（含 settlement_items） | P0 |
| N10 | `GET /admin/finance/settlements/preview` | 新增 | `finance:manage` | 生成前预览，不落库 | P0 |
| N11 | `GET /admin/finance/ledger` | 改造 | `finance:read` | 增加 date/order/store；补 store_name/order_no | P1 |
| N12 | `GET /admin/green/profiles` | 改造 | `green:review` | 补商品名/店铺/最新评估 id | P1 |
| N13 | `GET /admin/green/profiles/{id}` | 新增 | `green:review` | 资料详情 + 认证 + 核验记录 | P1 |
| N14 | `GET /admin/aid/cooperatives` | 新增 | `aid:manage` | 合作社列表（项目创建前置） | P0 |
| N15 | `GET /admin/aid/projects` | 改造 | `aid:manage` | 补合作社名/资助数/进度 | P1 |
| N16 | `GET /admin/cms/banners` | 新增 | `cms:manage` | 管理端 Banner 列表（含停用/过期） | P1 |
| N17 | `GET /admin/cms/announcements` | 新增 | `cms:manage` | 管理端公告列表（含草稿/下线） | P1 |
| N18 | `GET /admin/users` | 改造 | `user:read` | 增加 status/role/date；补昵称/角色/订单数 | P1 |
| N19 | `GET /admin/users/{id}` | 新增 | `user:read` | 会员详情 + 积分余额 + 最近订单 | P1 |
| N20 | `GET /admin/points/accounts` | 新增 | `points:manage` | 按邮箱/昵称查账户余额 | P1 |
| N21 | `GET /admin/points/transactions` | 新增 | `points:manage` | 管理端查任意用户积分流水 | P1 |
| N22 | `GET /admin/export/{dataset}.csv` | 新增 | 按数据集 | 订单/退款/结算/台账/商品/会员/积分/审计导出 | P1 |
| N23 | `POST /admin/uploads` | 新增 | `cms:manage` | Banner/封面图片上传 | P1 |
| N24 | `GET /admin/reports/{report_key}` | 新增 | 按报表 | 固定报表数据 | P2 |
| N25 | `GET /admin/audit/*` | 改造 | `audit:read` | 增加 date_from/date_to/user_id/success | P1 |
| N26 | `GET /admin/merchants` | 改造 | `merchant:read` | 增加 keyword/date；补 owner_email/store_count | P1 |
| N27 | `GET /admin/stores` | 改造 | `store:read` | 增加 keyword/merchant_id；补 merchant_name | P1 |
| N28 | `scripts/reset_admin_password.py` | 新增脚本 | — | 重置开发库管理员密码 | P0 |

### 8.3 关键接口契约

#### N01 `GET /api/v1/admin/me`

```json
{
  "code": "OK",
  "message": "success",
  "data": {
    "user": {
      "id": "0c1f...",
      "email": "ops@tanhui.example.com",
      "is_active": true,
      "mfa_enabled": false
    },
    "roles": [
      { "code": "ops_admin", "name": "运营管理员", "is_super": false }
    ],
    "permissions": [
      "user:read", "user:ban", "merchant:read", "store:read",
      "order:read", "cms:manage", "aid:manage", "audit:read", "dashboard:read"
    ],
    "is_super": false
  },
  "request_id": "..."
}
```

约束：

- 无任何 `kind='admin'` 角色 → `403 FORBIDDEN`。
- `is_super=true` 时 `permissions` 返回全部 20 个权限码（展开），同时保留 `is_super` 标志；前端不要只依赖 `permissions` 判断超管。
- 该接口只读，不写审计。

#### N02 `GET /api/v1/admin/dashboard/overview`

Query：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `date_from` | `YYYY-MM-DD` | 是 | 本地日（Asia/Shanghai），含当天 |
| `date_to` | `YYYY-MM-DD` | 是 | 本地日，含当天；范围 ≤ 366 天 |
| `granularity` | `day / week / month` | 否 | 默认 `day`；趋势聚合粒度 |

Response：

```json
{
  "code": "OK",
  "data": {
    "range": { "date_from": "2026-10-26", "date_to": "2026-11-24", "timezone": "Asia/Shanghai" },
    "generated_at": "2026-11-24T04:18:00Z",
    "kpis": {
      "gmv_pay": "1234567.89",
      "gmv_items": "1180000.00",
      "net_gmv": "1209000.00",
      "paid_orders": 1280,
      "created_orders": 1876,
      "aov": "964.51",
      "pay_rate": 0.6823,
      "refund_amount": "25567.89",
      "refund_rate": 0.0207,
      "new_users": 36,
      "active_buyers": 642
    },
    "todos": {
      "product_audits": 12,
      "merchant_reviews": 3,
      "refunds": 5,
      "green_reviews": 8,
      "carbon_unverified": 4,
      "settlements_pending": 2,
      "stock_alerts": 6
    },
    "trend": [
      { "date": "2026-11-01", "gmv_pay": "42310.00", "paid_orders": 42 }
    ],
    "order_status": [
      { "status": "paid", "count": 31 }
    ],
    "category_top": [
      { "category_id": "...", "name": "新鲜果蔬", "amount": "52310.00", "quantity": 320 }
    ],
    "store_top": [
      { "store_id": "...", "name": "陇原甄选旗舰店", "amount": "82310.00", "orders": 96 }
    ],
    "aid": { "projects": 4, "raised": "32000.00", "goal": "150000.00" },
    "green": { "green_products": 6, "listed_products": 7, "ratio": 0.8571 },
    "points": { "balance_total": 128000, "earned": 52000, "spent": 31000, "reversed": 2000, "adjusted": 500 },
    "warnings": [],
    "mock": false
  }
}
```

实现约束：

- 一次请求返回全部区块，避免前端 6 个并发请求；单区块查询失败时该区块返回 `null` 并在 `warnings` 中说明，不要整页 500。
- 趋势最多 366 个点；超过 90 天建议 `granularity=week`。
- 金额一律字符串；比率 0–1。
- 待办数实时 count，不要硬编码。
- `mock: false` 表示数据来自真实库；若某指标为仿真口径，需在 `notes` 中说明。

#### N03 `GET /api/v1/admin/products`（改造）

Query：

`status`、`store_id`、`category_id`、`keyword`（标题/副标题）、`date_from`、`date_to`、`page`、`page_size`。

Response `PageOut<AdminProductRow>`：

```json
{
  "id": "...",
  "title": "静宁红富士苹果",
  "subtitle": "高原红富士·脆甜多汁",
  "store_id": "...",
  "store_name": "陇原甄选旗舰店",
  "category_id": "...",
  "category_name": "新鲜果蔬",
  "status": "pending_review",
  "is_listed": false,
  "min_price": "68.00",
  "cover_url": "/uploads/demo/products/jingning-apple.webp",
  "sku_count": 2,
  "stock_total": 700,
  "created_at": "2026-11-20T02:10:00Z",
  "audited_at": null,
  "audit_reason": null
}
```

实现要点：

- 批量查询 `min(price)`、`min(image.url)`、`count(sku)`、`sum(inventory.total - reserved)`、店铺名、分类名；避免 N+1。
- 列表不要返回 `skus/images` 全量；详情单独接口。
- `status` 为空表示全部；`keyword` 用 `LIKE`（SQLite/PG 均可），后续量大再上全文索引。

#### N05 `GET /api/v1/admin/orders`（改造）

Query：

`status`、`keyword`（订单号/收货电话）、`user_id`、`store_id`、`date_from`、`date_to`、`page`、`page_size`。

Response `PageOut<AdminOrderRow>` + `summary`：

```json
{
  "items": [
    {
      "id": "...",
      "order_no": "TH202611240001",
      "status": "paid",
      "user_id": "...",
      "user_email": "buyer@tanhui.example.com",
      "receiver_name_masked": "王*",
      "receiver_phone_masked": "138****0001",
      "items_total": "128.00",
      "shipping_fee": "8.00",
      "points_deduct": "0.00",
      "pay_amount": "136.00",
      "refund_amount": "0.00",
      "item_count": 3,
      "store_ids": ["..."],
      "store_names": ["陇原甄选旗舰店"],
      "created_at": "2026-11-24T02:10:00Z",
      "paid_at": "2026-11-24T02:12:00Z"
    }
  ],
  "pagination": { "page": 1, "page_size": 20, "total": 128, "total_pages": 7 },
  "summary": { "count": 128, "pay_amount": "12345.00", "refund_amount": "120.00" }
}
```

注意：

- `summary` 是**当前筛选条件下全量**的汇总，不是本页；用于列表页底部与导出对账。
- `user_email` 仅 `user:read` 角色返回；否则返回 `null`，前端显示 `—`。
- 收货人/电话默认脱敏；详情页再按权限返回全量。

#### N06 `GET /api/v1/admin/orders/{id}`（改造）

在现有 `OrderOut` 基础上增加：

```json
{
  "buyer": { "id": "...", "email": "buyer@tanhui.example.com", "nickname": "体验用户" },
  "store_orders": [
    {
      "store_id": "...",
      "store_name": "陇原甄选旗舰店",
      "refundable_amount": "136.00",
      "items": []
    }
  ],
  "refunds": [],
  "shipments": [],
  "status_logs": [
    { "from_status": null, "to_status": "pending_payment", "action": "create", "note": null, "created_at": "..." }
  ]
}
```

实现要点：

- `refundable_amount = store_order.pay_amount - store_order.refund_amount`。
- `shipments` 由 `shipments/shipment_tracks` 组装；管理员不受消费者 `user_id` 限制。
- `status_logs` 按 `created_at ASC`。

#### N07 `GET /api/v1/admin/refunds`（改造）

Query：`status`、`order_id`、`order_no`、`store_id`、`date_from`、`date_to`、`page`、`page_size`。

Response `PageOut<AdminRefundRow>`：

```json
{
  "id": "...",
  "refund_no": "RF202611240001",
  "order_id": "...",
  "order_no": "TH202611240001",
  "store_order_id": "...",
  "store_order_no": "SO202611240001",
  "store_id": "...",
  "store_name": "陇原甄选旗舰店",
  "user_id": "...",
  "user_email": "buyer@tanhui.example.com",
  "amount": "68.00",
  "reason": "商品破损",
  "status": "requested",
  "requested_by": "...",
  "handled_by": null,
  "handled_at": null,
  "result_note": null,
  "created_at": "2026-11-24T03:00:00Z"
}
```

注意：`Refund.status` 实际只写 `requested/refunded/rejected`；模型注释里的 `processing/approved` 未使用。前端状态字典以实际值为准，并预留 `approved` 兼容。

#### N09/N10 结算明细与预览

`GET /admin/finance/settlements/{id}`：

```json
{
  "id": "...",
  "store_id": "...",
  "store_name": "陇原甄选旗舰店",
  "period_start": "2026-10-31T16:00:00Z",
  "period_end": "2026-11-15T16:00:00Z",
  "status": "pending",
  "orders_total": "12800.00",
  "commission_total": "640.00",
  "payable_total": "12160.00",
  "item_count": 32,
  "items": [
    {
      "store_order_id": "...",
      "store_order_no": "SO202611010001",
      "order_id": "...",
      "order_no": "TH202611010001",
      "order_amount": "400.00",
      "commission_amount": "20.00"
    }
  ],
  "generated_by": "...",
  "confirmed_at": null,
  "paid_at": null,
  "created_at": "..."
}
```

`GET /admin/finance/settlements/preview?store_id=&period_start=&period_end=`：

```json
{
  "store_id": "...",
  "store_name": "...",
  "order_count": 32,
  "items_total": "12800.00",
  "commission_total": "640.00",
  "payable_total": "12160.00",
  "skipped_settled_count": 3,
  "sample_items": []
}
```

实现要点：

- `period_start/period_end` 均为 ISO 8601 UTC；`period_start` 含、`period_end` 排他。前端负责把本地日「含首尾」转换为 `[首日 00:00+08, 末日次日 00:00+08)`；展示时再把 `period_end` 减 1 天转本地日，避免把排他上界显示成周期末日。
- 预览与生成必须使用同一段查询逻辑，避免「预览 32 单、生成 30 单」。
- 生成仍保留唯一约束兜底，重复返回 `CONFLICT`。

#### N12/N13 绿色资料

`GET /admin/green/profiles` 行增加：

```json
{
  "product_id": "...",
  "product_title": "静宁红富士苹果",
  "store_id": "...",
  "store_name": "陇原甄选旗舰店",
  "origin": "甘肃静宁",
  "planting_mode": "绿色种植",
  "status": "pending_review",
  "latest_assessment": {
    "id": "...",
    "co2e_per_unit": "0.4200",
    "unit": "kg",
    "methodology": "估算",
    "verified": false,
    "created_at": "..."
  },
  "updated_at": "..."
}
```

`GET /admin/green/profiles/{id}` 再返回 `certifications`、`description`、`verification_records[]`。

注意：列表必须带 `latest_assessment.id`，否则「碳核验」页面无法定位要核验的记录。

#### N14 合作社列表

`GET /admin/aid/cooperatives?keyword=&page=1&page_size=20`

```json
{
  "items": [
    {
      "id": "...",
      "name": "定西薯都合作社",
      "region": "甘肃省定西市",
      "description": "马铃薯标准化种植合作社（仿真）",
      "contact": "13800000000",
      "project_count": 2,
      "published_project_count": 1,
      "created_at": "2026-11-01T02:00:00Z"
    }
  ],
  "pagination": { "page": 1, "page_size": 20, "total": 4, "total_pages": 1 }
}
```

同时建议把现有 `POST /admin/aid/cooperatives` 从 query 参数改为 JSON body（`{name, region, description?, contact?}`），并保留 query 兼容一个版本，避免前端两套写法。

#### N22 导出

`GET /api/v1/admin/export/{dataset}.csv`

| 参数 | 说明 |
|---|---|
| `dataset` | `orders`、`refunds`、`settlements`、`ledger`、`products`、`members`、`points_transactions`、`audit_logs` |
| 其余 query | 与对应列表接口一致；导出不分页 |
| 权限 | 对应列表的读权限；`members` 还需 `user:read` |
| 响应头 | `Content-Type: text/csv; charset=utf-8`；`Content-Disposition: attachment; filename*=UTF-8''orders_20261124.csv` |
| 编码 | UTF-8 BOM，保证 Excel 中文不乱码 |
| 上限 | 5 万行；超过 `409 EXPORT_TOO_LARGE` |
| 审计 | 写 `operation_logs`：`action="export.orders"`，`detail={filters,row_count}` |
| 脱敏 | 默认脱敏手机号/邮箱；超管可选择全量，但仍记审计 |

#### N23 上传

`POST /api/v1/admin/uploads`，`multipart/form-data`：

- 字段：`file`；可选 `scene`（`banner|product_cover|aid_cover`）。
- 校验：MIME + 魔数 + 大小（≤5MB）+ 扩展名白名单（jpg/jpeg/png/webp）。
- 返回：`{ "url": "/uploads/admin/2026/11/xxx.webp", "size": 12345, "mime": "image/webp" }`。
- 复用 `app/modules/catalog/storage.py` 的本地存储适配层；生产切 S3 时只改适配层。

### 8.4 数据来源矩阵

> 所有指标来自后端 OLTP 库（SQLite 开发 / PostgreSQL 生产），**无外部数据源**；不接第三方统计 SDK、不做埋点上报。报表数据由后端聚合，前端不直连数据库。

| 页面/指标 | 主表 | 关联表 | 关键字段/公式 |
|---|---|---|---|
| 商品审核队列 | `products` | `stores`、`categories`、`product_skus`、`product_images` | `status='pending_review'`；`min(price)`、`min(image.url)`、`count(sku)` |
| 商品库存 | `inventories` | `product_skus`、`products` | `quantity_total - quantity_reserved` |
| 订单列表 | `orders` | `store_orders`、`order_items`、`users` | `pay_amount`、`Σ refund_amount`、`Σ quantity` |
| 订单详情 | `orders` | `store_orders`、`order_items`、`refunds`、`shipments`、`order_status_logs` | 子单/条目快照/状态时间线 |
| 退款列表 | `refunds` | `orders`、`store_orders`、`users` | `amount`、`status`、`handled_at` |
| 结算 | `merchant_settlements` | `settlement_items`、`store_orders`、`stores` | `orders_total`、`commission_total`、`payable_total` |
| 台账 | `platform_ledger` | `orders`、`stores` | `entry_type`、`amount`（正负） |
| 绿色资料 | `product_green_profiles` | `products`、`stores`、`carbon_assessments` | `status`、`verified`、`co2e_per_unit` |
| 助农项目 | `aid_projects` | `cooperatives`、`aid_donations` | `raised_amount/goal_amount`、资助人数 |
| 会员 | `users` | `user_profiles`、`user_roles`、`orders`、`point_accounts` | `created_at`、角色、`Σ pay_amount` |
| 积分 | `point_accounts` | `point_transactions` | `balance`、按 `type` 汇总 `amount` |
| 审计 | `operation_logs` | `login_logs`、`security_events` | `action`、`created_at`、`user_id` |
| GMV 趋势 | `orders` | — | 按 `paid_at` 本地日分组，`SUM(pay_amount)` |
| 品类 Top | `order_items` | `products`、`categories`、`store_orders`、`orders` | `SUM(order_items.subtotal)`，按 `category_id` |
| 店铺 Top | `store_orders` | `stores`、`orders` | `SUM(items_total)`，按 `store_id` |
| 支付转化 | `orders` | — | 创建 cohort 中 `paid_at IS NOT NULL` 占比 |

### 8.5 接口调用与契约变更约束

1. **先查 `openapi.yaml` 再写代码**；新增接口必须先更新后端 OpenAPI，再生成前端类型。
2. 所有列表接口必须服务端分页；前端不得 `page_size=1000` 全量拉取后切片（CMS 页面列表除外，页面数量少）。
3. 金额字段统一 `MoneyOut` 字符串；发现 `Decimal`/数字类型时，先在联调记录中标注，不要在前端 `Number()` 后回写。
4. 时间参数统一：列表筛选用 `date_from/date_to`（`YYYY-MM-DD`，本地日）；已有接口用 ISO UTC 的保持原样。ISO 时间带 `+08:00` 时必须 URL 编码，推荐统一用 `Z` 结尾的 UTC，避免 `+` 被解码成空格。
5. 新增接口必须返回 `ApiResponse` 信封；不要返回裸 JSON（CMS 客户端接口是历史例外）。
6. 新增错误码必须登记到 `docs/conventions.md`：
   - `EXPORT_TOO_LARGE`（409）
   - `INVALID_DATE_RANGE`（422）
   - `MEDIA_TYPE_INVALID`（422，如复用现有 `FILE_TYPE_INVALID` 则不必新增）
7. 每次接口变更后执行：
   ```bash
   cd tanhui-backend
   python -m scripts.export_openapi
   ```
   并更新 `docs/api-list.md`、`docs/admin-console-spec.md` §8、`docs/admin-page-api-map.md`。
8. 前端增加 `scripts/contract-check.mjs`：读取 `openapi.yaml`，断言 §8.2 中 P0/P1 接口均存在；缺失则 CI/交付失败。

---

## 9. 技术栈与组件依赖

### 9.1 选型结论

| 层 | 选型 | 理由 | 不选什么 |
|---|---|---|---|
| 框架 | Vue 3.5 + TypeScript 5.9 | 与消费者端一致，团队零迁移成本 | 不引入 React/ Angular |
| 构建 | Vite 7 | 与现有工程一致，配置简单 | 不上 Nuxt/SSR，管理端无需 SEO |
| 路由 | Vue Router 4.5 | 动态路由 + 权限守卫成熟 | 不上自研路由 |
| 状态 | Pinia 3 | 只存 auth/app，轻量 | 不引入 Vuex |
| UI 组件 | Element Plus 2.x（按需引入） | 表格、表单、日期范围、抽屉、分页最全，中文文档好 | 不同时引入 Ant Design Vue/Naive UI |
| 图标 | `@element-plus/icons-vue` | 与 Element Plus 配套 | 不引第三方图标库 |
| 图表 | ECharts 5.x + `vue-echarts` 7.x | 中文标签、双轴、环形、按需 tree-shaking | 不用 Chart.js（复杂图表能力弱） |
| 日期 | dayjs 1.x | Element Plus 已依赖，体积极小 | 不用 moment |
| HTTP | 原生 `fetch` + 复用 `http.ts` | 已有信封解析/401 刷新/错误码 | 不引入 axios，避免重复拦截器 |
| 类型生成 | `openapi-typescript`（dev） | 从 `openapi.yaml` 生成接口类型，减少漂移 | 不手写全部后端类型 |
| 测试 | Playwright 1.65（脚本） | 与现有 `scripts/smoke.mjs` 一致 | P0 不引入 Cypress |
| 质量 | ESLint 10 + Prettier 3 + vue-tsc 3 | 与现有工程一致 | 不引入 TSLint |
| 样式 | CSS 变量 + scoped CSS | 复用设计 Token，避免第二套体系 | 不引入 Tailwind/UnoCSS，减少构建复杂度 |

### 9.2 依赖清单

| 包 | 版本策略 | 用途 |
|---|---|---|
| `vue` | `^3.5.0` | 框架 |
| `vue-router` | `^4.5.0` | 路由 |
| `pinia` | `^3.0.0` | 状态 |
| `element-plus` | `2.x`，安装时锁定 | UI 组件 |
| `@element-plus/icons-vue` | `2.x` | 图标 |
| `echarts` | `5.x` | 图表 |
| `vue-echarts` | `7.x` | Vue 封装 |
| `dayjs` | `1.x` | 日期 |
| `unplugin-auto-import` | 当前稳定版 | Element Plus 按需自动导入 |
| `unplugin-vue-components` | 当前稳定版 | 组件按需注册 |
| `openapi-typescript` | 当前稳定版（dev） | 生成 `schema.d.ts` |
| `typescript` | `~5.9.0`（dev） | 类型 |
| `vite` | `^7.1.0`（dev） | 构建 |
| `vue-tsc` | `^3.0.0`（dev） | 类型检查 |
| `eslint` / `prettier` | 与消费者端一致（dev） | 质量 |
| `playwright` | `^1.65.0`（dev） | 冒烟 |

`package.json` scripts 草案：

```json
{
  "scripts": {
    "dev": "vite --host 127.0.0.1 --port 5176",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview --host 127.0.0.1 --port 4174",
    "typecheck": "vue-tsc --noEmit",
    "lint": "eslint .",
    "format": "prettier --write \"src/**/*.{ts,vue,css}\"",
    "test:smoke": "node scripts/admin-smoke.mjs",
    "test:contract": "node scripts/contract-check.mjs"
  }
}
```

### 9.3 组件清单

| 组件 | 职责 | 关键 props/事件 |
|---|---|---|
| `AdminLayout` | 侧边栏 + 顶栏 + 内容区 | `collapsed` |
| `SideNav` | 分组菜单、权限过滤、折叠 | `items`、`collapsed` |
| `TopBar` | 面包屑、环境标识、刷新、用户菜单 | `title`、`env` |
| `PageHeader` | 页面标题、描述、右侧操作 | `title`、`description`、`actions` slot |
| `FilterBar` | 筛选布局、查询/重置、折叠 | `loading`、`@search`、`@reset` |
| `DataTable` | 列配置、加载/空/错、行点击、分页 | `columns`、`rows`、`loading`、`error`、`total` |
| `StatusTag` | 枚举 → 中文 + 色点 | `type`、`value` |
| `MoneyText` | 金额字符串格式化、正负色 | `value`、`signed` |
| `DateTimeText` | UTC → Asia/Shanghai 显示 | `value`、`mode` |
| `MaskedText` | 手机号/邮箱/地址脱敏 | `value`、`kind`、`reveal` |
| `KpiCard` | 指标卡、环比、点击跳转 | `label`、`value`、`hint`、`to` |
| `ChartCard` | 图表容器、标题、加载/空 | `title`、`loading` |
| `TrendChart` | 双轴折线+柱 | `data`、`height` |
| `DonutChart` | 环形分布 | `data` |
| `BarChart` | 横向/纵向条形 | `data`、`horizontal` |
| `DetailDrawer` | 720px 抽屉、底部操作栏 | `open`、`title`、`loading` |
| `ReasonDialog` | 原因输入、快捷原因、必填校验 | `open`、`title`、`minLength` |
| `PermissionGate` | 按权限码渲染插槽 | `code`、`fallback` |
| `ExportButton` | 导出、加载、错误提示 | `dataset`、`filters` |
| `AuditTimeline` | 状态/审核时间线 | `items` |
| `AddressBlock` | 收货信息展示/脱敏 | `address`、`reveal` |
| `EmptyState` / `ErrorState` / `ForbiddenState` | 统一兜底 | `message`、`@retry` |

### 9.4 构建与部署

开发：

```bash
cd tanhui-admin
npm install
npm run dev   # http://127.0.0.1:5176
```

`vite.config.ts` 关键配置：

```ts
// import { defineConfig } from 'vite'
// import vue from '@vitejs/plugin-vue'
// import AutoImport from 'unplugin-auto-import/vite'
// import Components from 'unplugin-vue-components/vite'
// import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  base: '/admin/',
  plugins: [vue(), AutoImport({ resolvers: [ElementPlusResolver()] }), Components({ resolvers: [ElementPlusResolver()] })],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 5176,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true }
    }
  }
})
```

生产（同源部署，推荐）：

```nginx
# 构建产物放 /var/www/admin/（vite base='/admin/'）
location /admin/ {
    root /var/www;
    try_files $uri $uri/ /admin/index.html;
}
location /api/ {
    proxy_pass http://127.0.0.1:8000;
}
location /uploads/ {
    proxy_pass http://127.0.0.1:8000;
}
```

- 同源部署可避免 CORS 与 cookie 问题；管理端与消费者端共用 `/api`。
- Vue Router 必须用 `createWebHistory(import.meta.env.BASE_URL)`，与 Vite `base:'/admin/'` 对齐；否则刷新 `/admin/orders` 会 404。
- Element Plus 全局 locale 设为 `zh-cn`（`ElConfigProvider`），避免日期选择/分页出现英文。
- 如使用独立子域 `admin.example.com`，需在 `TANHUI_CORS_ORIGINS` 加该域名，并设置 `VITE_API_BASE_URL=https://api.example.com/api/v1`。
- 开发端口 5176 需要时加入 CORS 白名单；使用 Vite proxy 时不受 CORS 限制。

环境变量：

```bash
# .env.example
VITE_API_BASE_URL=/api/v1
VITE_FILE_BASE_URL=
VITE_PROXY_TARGET=http://127.0.0.1:8000
VITE_APP_ENV=dev
```

### 9.5 性能预算

| 项 | 预算 | 测量方式 |
|---|---|---|
| 首屏 JS（gzip，不含图表） | ≤ 350 KB | `vite build` 报告 |
| 图表 chunk（gzip，懒加载） | ≤ 250 KB | 路由级 `import()` |
| 单路由 chunk | ≤ 80 KB | 构建报告 |
| 列表接口 p95 | ≤ 800 ms（1 万订单/5 千商品） | 后端日志/压测 |
| 工作台接口 p95 | ≤ 1.5 s（90 天范围） | 后端日志 |
| 导出 5 万行 | ≤ 10 s（流式） | 手工计时 |
| 表格首屏渲染 | ≤ 1 s（100 行内） | Performance 面板 |
| 单页初始请求数 | ≤ 4 个（工作台除外） | Network 面板 |

> 压测数据：用独立脚本生成 1 万订单 / 5 千商品 / 2 万积分流水的测试库，不污染开发库；性能结论必须在该数据量下复测，不能用当前 7 笔订单的库下结论。

---

## 10. 潜在改造点

### 10.1 后端 P0 阻塞项（不补则前端无法开工/验收）

| # | 改造点 | 现状/证据 | 建议方案 | 影响 | 风险 |
|---|---|---|---|---|---|
| B01 | 管理员密码不可得 | `tanhui-backend/scripts/seed.py` 用 `secrets.token_urlsafe(12)` 随机生成，仅创建时打印；现库 5 个管理员密码通常未留存 | 新增 `scripts/reset_admin_password.py`；或 seed 支持 `TANHUI_SEED_ADMIN_PASSWORD`（仅 dev） | 无法登录联调 | 低 |
| B02 | 无管理员身份/权限接口 | `app/modules/users/router.py` 的 `GET /users/me` 返回 `MeOut(user, profile)`；`core/security.py` 的 JWT 只有 `sub/sid/typ/iat/exp/jti`，无 roles | 新增 `GET /admin/me`，返回 roles + permissions + is_super | 菜单/路由无法做权限 | 低 |
| B03 | 工作台指标不足且权限错误 | `app/modules/admin/router.py` 的 `dashboard()`：5 个标量；`require_permissions("order:read","user:read")`；`pending_product_audits: 0` | 新增 `GET /admin/dashboard/overview`；新增 `dashboard:read`；待办实时 count | 工作台打不开/无信息 | 中 |
| B04 | 商品列表无价格/封面/店铺 | `app/modules/catalog/admin_router.py` 用 `ProductDetailOut.model_validate(p)`；`Product` 无 `skus/images` 关系，`min_price/cover_url` 未装饰 | 新建 `AdminProductRow`，批量聚合 `min(price)`、封面、SKU 数、库存、店铺/分类名 | 商品审核页无法判断 | 低 |
| B05 | 订单/退款列表字段与筛选不足 | `orders/admin_router.py` 订单列表只返回 6 个字段；退款列表无 `order_no/store_name`；两者仅 `status` 筛选 | 增加 keyword/store/date/user 筛选；补买家、店铺、件数、退款额；详情补物流与状态时间线 | 运营无法定位与判断 | 中 |
| B06 | 结算/台账 DTO 不足，无预览/明细 | `finance/admin_router.py`：结算列表无 `store_name`；台账只返回 id/entry_type/ref_type/order_id/amount/note/created_at，无 `store_id/store_name/ref_id/order_no`；无结算 preview/detail | 新增 preview/detail；列表 join `stores`；台账补 `store_id/store_name/order_no/ref_id`；统一 preview 与 generate 查询 | 财务盲生成、无法对账 | 中 |
| B07 | 合作社无法列出 | `aid/router.py` 只有 `POST /admin/aid/cooperatives`，没有 GET | 新增 `GET /admin/aid/cooperatives`（分页/关键词/项目数） | 助农项目无法创建（拿不到 cooperative_id） | 低 |
| B08 | 管理端 CORS/端口 | `app/core/config.py` 默认只允许 5173–5175 | 加 5176 或使用同源代理 | 直连 API 时被浏览器拦截 | 低 |

### 10.2 后端 P1 正确性/体验项

| # | 改造点 | 现状/证据 | 建议方案 | 影响 |
|---|---|---|---|---|
| B09 | CMS Banner/公告无管理列表 | `cms/router.py` 只有创建/更新/发布/下线；`GET /client/*` 只返回已发布 | 新增 `GET /admin/cms/banners`、`GET /admin/cms/announcements`（含停用/草稿/过期） | 运营只能盲创建，无法管理 |
| B10 | Banner/公告缺少定时字段 | `cms/schemas.py` 的 `BannerIn`、`AnnouncementIn` 无 `start_at/end_at`，但模型有 | 补字段并在客户端过滤生效时间 | 无法做定时上线 |
| B11 | 公告无编辑接口 | 只有 create/publish/offline | 增加 `PUT /cms/announcements/{id}`（仅 draft） | 改错只能新建 |
| B12 | Banner 无删除 | 只有 create/update | 增加 `DELETE /cms/banners/{id}`（或仅 `enabled=false`） | 无法清理 |
| B13 | 绿色列表缺商品/评估 id | `green/router.py` 的 `GreenProfileOut` 只有资料字段 | 补 `product_title/store_name/latest_assessment.id`；或新增 detail | 碳核验无法定位记录 |
| B14 | 助农列表缺合作社/资助统计 | `aid/router.py` 的 `ProjectOut` 无 `cooperative_name`、资助人数 | 补字段；新增项目资助名单 | 运营看不到项目全貌 |
| B15 | 会员列表字段少 | `admin/router.py` 的 `AdminUserOut` 只有 5 个字段 | 补昵称、角色、订单数、累计实付、最近登录 | 客服无法判断用户 |
| B16 | 会员详情/积分流水缺失 | 无 `/admin/users/{id}`、无管理端积分流水 | 新增 detail、`/admin/points/accounts`、`/admin/points/transactions` | 封禁/调分缺依据 |
| B17 | 审计日志无时间/用户筛选 | `audit/admin_router.py` 只有 action/resource/email/kind | 加 `date_from/date_to/user_id/success` | 无法查时段事件 |
| B18 | 驳回原因未强制 | `catalog/service.py` 驳回默认「不符合规范」；`merchants/service.py` 默认「不符合入驻要求」；退款 reject 备注可选 | 后端对 `reject/remove` 强制 `reason` 非空（422） | 审计追溯质量差 |
| B19 | 权限 AND 语义易误用 | `core/deps.py` 的 `require_permissions` 全部满足才放行；商品审核要求 `approve + remove` | 增加 `require_any_permission`；商品审核按 action 分权限 | 角色配置稍变就 403 |
| B20 | 金额类型不一致 | `orders/admin_router.py` 的 `RefundOut.amount` 是 `Decimal`，其余是 `MoneyOut` 字符串 | 统一 `MoneyOut`；联调确认 JSON 类型 | 前端类型/展示不一致 |
| B21 | 管理员密码/MFA 生产配置 | `MFA_REQUIRED_FOR_ADMIN_LOGIN=False`、`MOCK_MFA_CODE=123456` | 生产置 `True`、清空 mock code；开发保留 | 管理端安全 |
| B22 | 报表索引不足 | `orders.paid_at`、`orders.completed_at`、`refunds.handled_at` 未建索引 | 加复合索引：`(status, paid_at)`、`(store_id, completed_at)`、`(status, handled_at)` | 报表/列表变慢 |
| B23 | `dict` 响应导致类型退化 | 多个管理接口 `response_model=ApiResponse[dict]` | 改为显式 Pydantic DTO | OpenAPI 生成类型不可用 |
| B24 | 结算/台账无汇总 | 列表只有分页 items | 增加 `summary`（count/金额合计） | 财务无法对账 |
| B25 | OpenAPI 未同步 | 新增接口后需手工导出 | 把 `python -m scripts.export_openapi` 放进交付清单/CI | 前端类型漂移 |
| B26 | 结算未扣减退款 | `finance/service.py` 的 `generate_settlement` 对 `partially_refunded` 子单仍按 `items_total` 全额结算，未减 `refund_amount` | 财务确认口径：若按净额结算，改为 `items_total - refund_amount`，佣金同步按净额重算；预览与明细必须显示扣减项 | 商家多结/平台少收 |

> B26 虽列在 P1 表，但属于结算上线前必须确认的口径；若按净额结算，N09/N10 契约需增加 `refund_deduct` 字段并在预览/明细中展示。

### 10.3 前端架构决策（避免踩坑）

| # | 决策 | 说明 |
|---|---|---|
| F01 | 独立 `tanhui-admin` 应用 | 不修改消费者端构建；避免 Element Plus/ECharts 进入消费者包 |
| F02 | 复制 `http.ts` 而不是抽公共包 | 两端仅 ~300 行，复制成本低于 monorepo 配置；文件头注明「同步自 consumer」 |
| F03 | token key 加前缀 | `tanhui_admin_access_token` / `tanhui_admin_refresh_token`，避免同源与消费者端冲突 |
| F04 | 路由即菜单 | 单一 `routes.ts` 维护 `meta.nav/permission/group`，不再写第二份菜单配置 |
| F05 | `useTableQuery` 统一列表状态 | URL 同步、分页、筛选、刷新、末页回退只写一次，多个列表页复用 |
| F06 | `DataTable` 统一列配置 | 禁止每页手写 `<el-table>` 的 loading/empty/error/分页 |
| F07 | 图表懒加载 | `defineAsyncComponent(() => import('vue-echarts'))`，仅工作台/报表加载 |
| F08 | 类型分两层 | `api/types.ts` 存后端 DTO；`views/*/types.ts` 存 ViewModel；不混用 |
| F09 | 不复制 7146 行 `main.css` | 只抽 tokens + base；管理端样式独立，避免选择器冲突 |
| F10 | 不做暗色模式 P0 | 减少验收面；P2 再评估 |
| F11 | token 先沿用 localStorage + CSP + 短 TTL | 与现有后端 Bearer 一致；P2 再评估 httpOnly cookie/BFF，不在首版改认证链路 |

### 10.4 明确不建议的改造

| 不建议 | 原因 |
|---|---|
| 重写后端 / 换框架 | 55 个管理接口已可用，重写只会引入回归 |
| 引入微前端/模块联邦 | 只有一个管理端，收益为零 |
| 引入 GraphQL/BFF | 现有 REST 契约稳定，BFF 增加一层维护 |
| 引入 WebSocket 实时大屏 | 管理端不需要秒级；工作台 60 秒缓存足够 |
| 做拖拽式页面搭建器 | CMS 已有白名单组件，拖拽会突破校验边界 |
| 做自定义报表 SQL/维度拖拽 | 安全与口径风险高；固定报表足够 |
| 做区域/店铺行级权限 | 需要改 RBAC 模型与所有查询；首版明确不做 |
| 做地图大屏 | 合规底图/审图号成本高；条形图足够 |
| 做批量审核/批量退款 | 误操作风险高；P2 再评估，且必须逐条确认 |
| 商家工作台 / Android 端 | 独立产品与交互形态，不在本管理端范围；共享后端 API 即可 |

---

## 11. 非功能要求

| 维度 | 要求 | 验证方式 |
|---|---|---|
| 性能 | 见 §9.5；列表/工作台/导出达标 | 构建报告 + 后端日志 + 手工计时 |
| 可靠性 | 写操作防重；409 不自动重试；GET 最多重试 1 次；失败不改变本地权威状态 | 断网/重复点击/409 演练 |
| 一致性 | 金额只展示服务端字符串；全量汇总用后端 `summary`；工作台与列表同筛选对账差异 0.00 | 对账脚本/手工核对 |
| 安全 | 后端 RBAC 权威；无 `v-html`；链接协议白名单；CSP；token 命名空间；敏感操作二次确认；导出审计 | 代码扫描 + 渗透自查 |
| 隐私 | 列表脱敏手机号/邮箱/地址；导出默认脱敏；不在日志/URL 放个人信息 | 抽查 + 导出样本 |
| 审计 | 所有写操作展示操作者/时间/结果；导出写审计；错误 Toast 带 `request_id` | 操作后查 `operation_logs` |
| 可用性 | 1440×900 基准；1280 可用；1024 表格横向滚动；Chrome/Edge 最近两个大版本 | 截图 + 手工 |
| 可访问性 | 键盘可达；抽屉/弹窗焦点陷阱；Esc 关闭；表格表头语义；状态不只靠颜色；对比度 ≥4.5:1 | axe/手工 |
| 可维护性 | 类型生成；页面-API 对照；统一组件；无重复请求逻辑；中文文案集中 | Code Review |
| 可观测性 | 全局错误边界；未捕获 Promise 提示；可选 Sentry（脱敏）；开发环境请求耗时日志 | 手工触发错误 |
| 兼容性 | 不做 IE；不做移动端适配（<1024 提示桌面端） | 浏览器矩阵 |
| 国际化 | 仅 zh-CN；日期/数字用 `Intl`/dayjs 中文本地化 | 文案检查 |
| 数据新鲜度 | 工作台缓存 ≤60s；列表不缓存；写后刷新当前页 | 手工 |
| Mock 透明 | 支付/物流/积分兑换/碳数据必须标注「仿真/未核验」 | 页面走查 |

> CSP 草案：`default-src 'self'; img-src 'self' data: https:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' https:; frame-ancestors 'none'`。Element Plus 需要 `style-src 'unsafe-inline'`，不要开 `unsafe-eval`。

---

## 12. 交付项（按优先级）

### 12.1 里程碑总表

| 里程碑 | 范围 | 产出 | 验收 | 净估算 | 依赖 |
|---|---|---|---|---|---|
| M0 基础设施与阻塞项 | 工程脚手架、Element Plus/ECharts、tokens、`http.ts`、auth store、路由守卫、布局、登录、403/404、`/admin/me`、密码重置、30 天演示数据 | 可登录、菜单按权限渲染、演示数据足够 | 5 个角色账号均能登录/被正确拦截 | 2 人天 | B01/B02/B08 |
| M1 P0 交易闭环 | 工作台、商品审核、商家审核、订单列表/详情、退款、结算、台账 | 9 条 P0 路由（8 项能力） | 见 §12.5 用例 1–8 | 6 人天 | B03–B07、B26、N04、N09–N10 |
| M2 P1 治理 | 商品库、商家与店铺、绿色、助农、CMS Banner/公告、会员、积分、RBAC、审计、导出 | P1 页面（商品库/店铺/绿色/助农/CMS Banner+公告/会员/积分/RBAC/审计） | 见 §12.5 用例 9–14 | 7 人天 | B09–B20、N11–N23 |
| M3 P2 报表与优化 | 报表中心、7 张固定报表、CMS 页面编辑器、系统设置、索引/汇总、性能与视觉打磨 | 报表页 + CMS 页面编辑器 + 设置页 + 优化记录 | 报表与列表对账一致；性能达标 | 5 人天 | B22–B25、N24 |

- **P0 MVP：M0 + M1 = 8 人天净开发**；含联调/自测约 **9–10 人天**。
- **P0 + P1：15 人天净开发**；含联调/自测约 **17 人天**。
- **完整交付：20 人天净开发**；含 buffer 约 **23 人天**。

建议施工顺序（减少等待）：

1. 后端先做 B01/B02（密码重置 + `/admin/me`），前端并行搭脚手架、登录页、权限路由。
2. 后端做 B03/B04/B05/B07，前端做工作台、商品审核、订单、商家审核。
3. 后端做 B06/B26/N09/N10，前端做退款、结算、台账。
4. P1 按 §3.3 页面清单从左到右推进；每完成一个域，补 `admin-page-api-map.md` 与 smoke 断言。
- 估算假设：1 名熟悉 Vue 的开发者 + AI 辅助，**含本文列出的后端 DTO/筛选/聚合小改造**；不含后端报表引擎、真实支付/物流对接、合规审查。

### 12.2 P0 最小可用范围（建议先交付）

必须包含：

1. `/admin/login` + `/admin/me` + 权限路由 + 403。
2. `/admin/dashboard`：6 KPI + 7 待办 + 趋势 + 订单状态分布。
3. `/admin/products/review`：列表 + 抽屉 + 通过/驳回 + 审核历史。
4. `/admin/merchants/review`：列表 + 抽屉 + 通过/驳回。
5. `/admin/orders` + `/admin/orders/:id`：筛选 + 表格 + 详情 + 子单/金额/退款。
6. `/admin/refunds`：待处理队列 + 通过/驳回。
7. `/admin/finance/settlements`：预览 + 生成 + 确认 + 打款 + 明细。
8. `/admin/finance/ledger`：只读流水 + 筛选。

P0 暂不做：商品库全量、店铺管理、绿色、助农、CMS、会员、积分、RBAC、审计、报表、导出。

### 12.3 完整交付范围

在 P0 基础上增加：

- 商品库（全状态、筛选、详情）。
- 商家与店铺（冻结/解冻、店铺停业/恢复/关闭）。
- 绿色资料审核 + 碳评估核验。
- 助农项目/合作社。
- CMS Banner/公告（列表、创建、编辑、发布/下线）；CMS 页面编辑器 P2。
- 会员列表/详情/封禁；积分规则/调整/流水。
- RBAC 角色查看 + 用户角色授予/移除。
- 审计三类日志 + 时间/用户筛选。
- 系统设置。
- 导出（订单/退款/结算/台账/商品/会员/积分/审计）。
- 报表中心（7 张固定报表）。

### 12.4 Definition of Done

交付物清单：`tanhui-admin/` 源码、`docs/admin-page-api-map.md`、本文档、`artifacts/` 截图、`scripts/admin-smoke.mjs`、后端 `openapi.yaml` / `api-list.md` 更新。

- [ ] `npm run typecheck` 0 error。
- [ ] `npm run lint` 0 error / 0 warning。
- [ ] `npm run build` 通过。
- [ ] `npm run test:smoke` 通过（登录 → 工作台 → 商品审核 → 商家审核 → 订单 → 退款 → 结算 → 导出）。
- [ ] 5 个 seed 角色账号逐一验证：菜单、路由、按钮、403 页面符合 §4.2。
- [ ] 所有 P0 路由具备 loading / empty / error / forbidden 四态。
- [ ] 工作台数字与同筛选列表 `summary` 对账，金额差异 0.00。
- [ ] 导出 CSV 在 Excel 打开无乱码，金额两位小数，时间 GMT+8，导出行为可在审计日志查到。
- [ ] 无 `v-html`；无 `javascript:` 链接；无 `console.log` 进入生产构建。
- [ ] 无页面内硬编码 mock 数据；演示数据只来自后端 seed。
- [ ] 新增接口已更新 `openapi.yaml`、`api-list.md`、`admin-page-api-map.md`。
- [ ] README 增加管理端启动/构建/账号说明。
- [ ] 1440 与 1280 截图入 `artifacts/`。

### 12.5 验收用例

| # | 场景 | 步骤 | 预期 |
|---|---|---|---|
| 1 | 非管理员登录 | 用 `buyer@tanhui.example.com` 登录管理端 | 提示「非管理账号」，不进入；token 清理 |
| 2 | 运营菜单 | 用 `ops@tanhui.example.com` 登录 | 可见工作台/订单/商家/店铺/CMS/助农/审计；不可见商品审核/财务/积分/设置 |
| 3 | 商品驳回 | 待审商品 → 驳回不填原因 | 表单阻止；填写后成功，队列少 1，审核历史新增 |
| 4 | 商家通过 | 待审商家 → 通过 → 查看店铺 | 自动生成店铺，owner 绑定；店铺列表可见 |
| 5 | 订单筛选 | 选日期 2026-11-01~2026-11-24 + 状态已支付 | 列表 total 与 DB 一致；分页正确；切换筛选回第 1 页 |
| 6 | 退款通过 | 待处理退款 → 通过 | 退款单 `refunded`；子单 `refund_amount` 增加；台账新增退款；积分冲正；通知生成 |
| 7 | 重复结算 | 同店同周期生成两次 | 第二次 `409`，提示「该店铺此周期已生成结算单」 |
| 8 | 绿色核验 | 待审绿色 → 通过资料；再核验碳评估 | 资料 `approved`；碳评估 `verified=true`；核验记录可查 |
| 9 | 封禁 | 会员列表 → 封禁 → 用该用户 token 调 `/users/me` | 封禁成功；该 token 返回 401/403；会话被撤销 |
| 10 | 积分调整 | 选用户 → +100 → 原因「活动补发」 | 余额 +100；流水 `adjust`；审计有记录 |
| 11 | 导出订单 | 筛选 30 天 → 导出 CSV | Excel 正常；金额两位小数；时间 GMT+8；审计有 `export.orders` |
| 12 | 越权访问 | 运营直接访问 `/admin/settings` | 403 页面；不登出；返回工作台可用 |
| 13 | 日期边界 | 筛选 `2026-11-24` 当天 | 包含 `2026-11-23T16:00:00Z`–`2026-11-24T15:59:59Z` 的订单；不包含 `2026-11-23T15:30:00Z`（本地 11-23 23:30）与 `2026-11-24T16:00:00Z`（本地 11-25 00:00） |
| 14 | 403 不登出 | 财务访问 `/admin/products` | 403 页面；侧边栏仍可用；token 保留 |

---

## 13. AI 开发约束（必须遵守）

1. **契约优先**：只调用 `openapi.yaml` / `api-list.md` 中存在的接口；缺接口先写「接口需求」并等待后端，不得在前端造路径。
2. **类型两层**：后端 DTO 用生成/手写类型；页面 ViewModel 单独定义；禁止 `any` 蔓延。
3. **金额只格式化**：所有金额按字符串处理；禁止 `parseFloat` 后回写、禁止前端计算权威总额。
4. **服务端分页**：列表必须传 `page/page_size`；禁止全量拉取后前端切片（CMS 页面列表除外）。
5. **写操作三件套**：二次确认 + 提交锁 + 成功后刷新；金额/状态不允许乐观更新。
6. **禁止 `v-html`**：CMS 内容按纯文本渲染；链接只允许 `/` 开头站内路径或 `https://`。
7. **四态齐全**：每个列表/详情必须有 loading、empty、error、forbidden；403 不清 token。
8. **时区集中**：所有本地日 ↔ UTC 转换走 `utils/dateRange.ts`；禁止页面里手写 `new Date()` 拼接。
9. **权限只做 UX**：前端隐藏/禁用不替代后端校验；收到 403 按页面级处理。
10. **Mock 必须标注**：支付、物流、积分兑换、碳评估未核验，页面必须显示「仿真/未核验」。
11. **不复制消费者样式**：只抽 tokens；不引入 maplibre/deck.gl；不把消费者页面组件搬进管理端。
12. **依赖克制**：不引入 axios/moment/jQuery/Tailwind；新增依赖需在 PR 说明体积与替代方案。
13. **禁止页面内假数据**：需要 fixture 时放 `src/mocks/` 并由 `VITE_API_FIXTURES=1` 显式开启，生产构建必须关闭。
14. **文案统一**：状态、角色、模块名放 `constants/labels.ts`；不在模板里散落中文枚举。
15. **错误可追溯**：错误 Toast 展示 `request_id` 并可复制；500 不吞错。
16. **每次新增页面**：更新 `docs/admin-page-api-map.md`，并在 `scripts/admin-smoke.mjs` 加一条断言。
17. **交付前跑门禁**：typecheck、lint、build、smoke、contract-check 全绿。
18. **遵守不做清单**：§10.4 列出的内容未经确认不得开工。

---

## 14. 风险与未决事项

### 14.1 风险登记

| # | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R1 | 管理员密码不可得，联调卡住 | 高 | 高 | D0 重置脚本；seed 支持环境变量 |
| R2 | 后端新增接口与前端契约漂移 | 中 | 高 | OpenAPI 生成类型 + `contract-check.mjs` |
| R3 | 指标口径未确认，报表数字被质疑 | 高 | 中 | §5.1 口径签字；工作台与列表对账脚本 |
| R4 | 时区处理错误，日切数据偏差 | 高 | 高 | `dateRange.ts` 统一转换；用例 13 |
| R5 | 角色配置与业务预期不符，页面 403 | 高 | 中 | §4.2 矩阵确认；先按最小权限上线 |
| R6 | 数据量增长后报表变慢 | 中 | 中 | 复合索引；P2 加 `daily_metrics` 汇总表 |
| R7 | 导出泄露个人信息 | 中 | 高 | 权限 + 默认脱敏 + 审计 + 行数上限 |
| R8 | 管理端 XSS 窃取 token | 中 | 高 | 无 `v-html` + CSP + 短 access TTL；P2 评估 httpOnly |
| R9 | 演示数据太少，图表验收看不出问题 | 高 | 低 | D0 生成 ≥200 笔/30 天数据 |
| R10 | `dict` 响应导致类型/字段遗漏 | 高 | 中 | 改显式 DTO；联调逐字段核对 |
| R11 | 退款状态注释与实现不一致 | 中 | 低 | 前端按实际值 + 预留 `approved` |
| R12 | Mock MFA/支付被误当真实 | 中 | 中 | 环境标识 + 页面标注 + 生产配置检查 |

### 14.2 未决事项（附建议默认值）

| # | 事项 | 建议默认 | 影响 | 决策人 |
|---|---|---|---|---|
| D1 | 运营是否拥有商家审核 | 是，给 `ops_admin` 加 `merchant:review` | 运营能否独立完成入驻审核 | 业务负责人 |
| D2 | 运营是否处理退款 | 否，退款归财务/客服 | 退款时效与职责 | 业务负责人 |
| D3 | 财务如何看店铺名 | DTO 补 `store_name`，不扩 `store:read` | 结算/台账可读性 | 后端 |
| D4 | 工作台主 GMV 口径 | 实付 GMV；商品 GMV 作为副指标 | 对外口径 | 业务/财务 |
| D5 | 退款率口径 | 同期退款额 ÷ 同期实付 GMV | 报表口径 | 财务 |
| D6 | 结算周期边界 | 本地日 `[start 00:00, end+1 00:00)` | 结算金额 | 财务 |
| D7 | 是否做区域/店铺行级权限 | 首版不做 | 角色设计 | 业务 |
| D8 | 导出是否含个人信息 | 默认脱敏；超管可全量并审计 | 合规 | 合规/业务 |
| D9 | 是否计算平台减排总量 | 不计算；只展示已核验商品数与单位碳足迹 | 对外宣传 | 业务/合规 |
| D10 | 管理员 MFA 是否强制 | 生产 `True`，开发 `False` | 安全 | 运维 |
| D11 | CMS 页面编辑器是否首版 | 否，P2 | 范围/工期 | 业务 |
| D12 | 是否做批量审核/退款 | 否，P2 再评估 | 效率/风险 | 业务 |
| D13 | 结算是否扣减退款 | 按净额 `items_total - refund_amount`；佣金同基数 | 商家应结金额 | 财务 |

---

## 附录 A：状态与枚举字典

| 实体 | 字段 | 值 | 中文 | 备注 |
|---|---|---|---|---|
| 订单/子单 | `status` | `pending_payment` | 待付款 | 初始 |
| | | `paid` | 待发货 | 支付成功 |
| | | `shipped` | 待收货 | 已发货 |
| | | `completed` | 已完成 | 确认收货 |
| | | `cancelled` | 已取消 | 终态 |
| | | `refunding` | 退款中 | 有退款申请 |
| | | `refunded` | 已退款 | 终态 |
| | | `partially_refunded` | 部分退款 | 终态 |
| 退款 | `status` | `requested` | 待处理 | 实际写入 |
| | | `refunded` | 已退款 | 实际写入 |
| | | `rejected` | 已驳回 | 实际写入 |
| | | `processing` / `approved` | 处理中/已通过 | 模型注释预留，当前未写入 |
| 商品 | `status` | `draft` | 草稿 | 商家可编辑 |
| | | `pending_review` | 待审核 | 管理员队列 |
| | | `approved` | 已通过 | 可上下架 |
| | | `rejected` | 已驳回 | 可修改重提 |
| | | `removed` | 平台下架 | 终态；当前无恢复接口 |
| 商家 | `status` | `pending_review` | 待审核 | 入驻申请 |
| | | `approved` | 已通过 | 自动建店 |
| | | `rejected` | 已驳回 | 记录原因 |
| | | `frozen` | 已冻结 | 可解冻 |
| 店铺 | `status` | `active` | 正常 | — |
| | | `suspended` | 已暂停 | 平台暂停 |
| | | `closed` | 已关闭 | 不可再变更 |
| 绿色资料 | `status` | `draft` | 草稿 | — |
| | | `pending_review` | 待审核 | 管理员队列 |
| | | `approved` | 已通过 | 消费者可见 |
| | | `rejected` | 已驳回 | — |
| 碳评估 | `verified` | `true/false` | 已核验/未核验 | 默认 false |
| 助农项目 | `status` | `draft` | 草稿 | — |
| | | `pending_review` | 待审核 | 预留 |
| | | `published` | 已发布 | 消费者可见 |
| | | `offline` | 已下线 | — |
| CMS 页面 | `status` | `draft` | 草稿 | — |
| | | `reviewing` | 审核中 | 预留 |
| | | `published` | 已发布 | 有 current_version |
| 公告 | `status` | `draft` | 草稿 | — |
| | | `published` | 已发布 | 客户端可见 |
| | | `offline` | 已下线 | — |
| 结算 | `status` | `pending` | 待确认 | 生成后 |
| | | `confirmed` | 已确认 | 可打款 |
| | | `paid` | 已打款 | 仿真 |
| 积分流水 | `type` | `earn` | 发放 | 订单完成/助农 |
| | | `spend` | 消费 | 抵扣/兑换 |
| | | `reverse` | 冲正 | 退款 |
| | | `adjust` | 调整 | 管理员 |
| 支付单 | `status` | `pending` | 待支付 | — |
| | | `success` | 成功 | 回调 |
| | | `closed` | 已关闭 | 取消/超时 |
| | | `failed` | 失败 | 异常 |
| 用户 | `is_active` | `true/false` | 正常/封禁 | 封禁撤销会话 |
| 台账 | `entry_type` | `payment` | 支付入账 | 正 |
| | | `commission` | 佣金 | 支付时正、退款回退时负 |
| | | `refund` | 退款 | 负 |
| | | `adjustment` | 调整 | 正/负 |

## 附录 B：管理端 TypeScript 契约草案

```ts
export interface ApiResponse<T> {
  code: string
  message: string
  data: T
  request_id: string
}

export interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface PageData<T> {
  items: T[]
  pagination: Pagination
  summary?: Record<string, string | number>
}

export type PermissionCode =
  | 'user:read' | 'user:ban'
  | 'merchant:read' | 'merchant:review'
  | 'store:read' | 'store:manage'
  | 'product:read' | 'product:approve' | 'product:remove'
  | 'order:read' | 'refund:approve'
  | 'finance:read' | 'finance:manage'
  | 'points:manage'
  | 'cms:manage'
  | 'aid:manage'
  | 'green:review'
  | 'audit:read'
  | 'rbac:manage'
  | 'settings:manage'
  | 'dashboard:read'

export interface AdminMe {
  user: { id: string; email: string; is_active: boolean; mfa_enabled: boolean }
  roles: { code: string; name: string; is_super: boolean }[]
  permissions: PermissionCode[]
  is_super: boolean
}

export interface DashboardOverview {
  range: { date_from: string; date_to: string; timezone: 'Asia/Shanghai' }
  generated_at: string
  kpis: {
    gmv_pay: string
    gmv_items: string
    net_gmv: string
    paid_orders: number
    created_orders: number
    aov: string
    pay_rate: number
    refund_amount: string
    refund_rate: number
    new_users: number
    active_buyers: number
  }
  todos: {
    product_audits: number
    merchant_reviews: number
    refunds: number
    green_reviews: number
    carbon_unverified: number
    settlements_pending: number
    stock_alerts: number
  }
  trend: { date: string; gmv_pay: string; paid_orders: number }[]
  order_status: { status: string; count: number }[]
  category_top: { category_id: string; name: string; amount: string; quantity: number }[]
  store_top: { store_id: string; name: string; amount: string; orders: number }[]
  aid: { projects: number; raised: string; goal: string }
  green: { green_products: number; listed_products: number; ratio: number }
  points: { balance_total: number; earned: number; spent: number; reversed: number; adjusted: number }
  mock: boolean
}

export interface AdminOrderRow {
  id: string
  order_no: string
  status: string
  user_id: string
  user_email: string | null
  receiver_name_masked: string
  receiver_phone_masked: string
  items_total: string
  shipping_fee: string
  points_deduct: string
  pay_amount: string
  refund_amount: string
  item_count: number
  store_ids: string[]
  store_names: string[]
  created_at: string
  paid_at: string | null
}

export interface AdminRefundRow {
  id: string
  refund_no: string
  order_id: string
  order_no: string
  store_order_id: string
  store_order_no: string
  store_id: string
  store_name: string
  user_id: string
  user_email: string | null
  amount: string
  reason: string
  status: 'requested' | 'refunded' | 'rejected' | 'processing' | 'approved'
  requested_by: string
  handled_by: string | null
  handled_at: string | null
  result_note: string | null
  created_at: string
}

export interface AdminProductRow {
  id: string
  title: string
  subtitle: string | null
  store_id: string
  store_name: string
  category_id: string | null
  category_name: string | null
  status: 'draft' | 'pending_review' | 'approved' | 'rejected' | 'removed'
  is_listed: boolean
  min_price: string | null
  cover_url: string | null
  sku_count: number
  stock_total: number
  created_at: string
  audited_at: string | null
  audit_reason: string | null
}

export interface AdminSettlementRow {
  id: string
  store_id: string
  store_name: string
  period_start: string
  period_end: string
  status: 'pending' | 'confirmed' | 'paid'
  orders_total: string
  commission_total: string
  payable_total: string
  item_count: number
  generated_by: string
  confirmed_at: string | null
  paid_at: string | null
  created_at: string
}

export interface AdminGreenProfileRow {
  id: string
  product_id: string
  product_title: string
  store_id: string
  store_name: string
  origin: string
  planting_mode: string | null
  status: 'draft' | 'pending_review' | 'approved' | 'rejected'
  latest_assessment: {
    id: string
    co2e_per_unit: string
    unit: string
    methodology: string | null
    verified: boolean
    created_at: string
  } | null
  updated_at: string
}

export interface AdminUserRow {
  id: string
  email: string
  nickname: string | null
  is_active: boolean
  mfa_enabled: boolean
  roles: { code: string; name: string }[]
  order_count: number
  total_paid: string
  last_login_at: string | null
  created_at: string
}
```

## 附录 C：交付检查清单（可勾选）

- [ ] 后端 `/admin/me` 已上线，5 个角色返回正确权限。
- [ ] 后端工作台 `overview` 已上线，KPI/待办/趋势/分布可用。
- [ ] 后端商品/订单/退款/结算列表字段与筛选已补齐。
- [ ] 合作社 GET 接口已上线。
- [ ] 管理员密码已可重置，5 个账号可登录。
- [ ] 演示数据 ≥200 笔订单、覆盖 30 天。
- [ ] 管理端工程 `tanhui-admin` 可 `npm run dev`。
- [ ] 登录/登出/401 刷新/403 页面通过。
- [ ] 侧边栏按权限渲染，5 个角色逐一验证。
- [ ] P0 9 条路由四态齐全。
- [ ] 商品审核通过/驳回/审核历史通过。
- [ ] 商家审核通过自动建店通过。
- [ ] 订单筛选/详情/子单/金额通过。
- [ ] 退款通过/驳回及台账/积分/通知副作用通过。
- [ ] 结算预览/生成/确认/打款/明细通过。
- [ ] 台账筛选/正负色/汇总通过。
- [ ] P1 页面（商品库/店铺/绿色/助农/CMS/会员/积分/RBAC/审计）通过。
- [ ] 导出 CSV 在 Excel 打开正常，审计可查。
- [ ] 工作台与列表对账差异 0.00。
- [ ] 1440/1280 截图入 `artifacts/`。
- [ ] `openapi.yaml`、`api-list.md`、`admin-page-api-map.md`、README 已更新。
- [ ] typecheck/lint/build/smoke/contract-check 全绿。


