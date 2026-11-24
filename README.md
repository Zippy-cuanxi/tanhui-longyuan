# 碳惠陇原 · 消费者商城 Web

基于设计稿与后端交接手册实现的甘肃特色农产品绿色电商平台消费者端。技术栈：**Vue 3 + TypeScript + Vite + Pinia + Vue Router**。

> 本轮范围：**仅消费者商城 Web**。商家工作台、管理员后台、Android 端不在本轮范围内。

---

## 1. 快速启动

### 1.1 环境要求

- Node.js 22+（本机验证使用 Node 26）
- npm 10+
- Python 3.12+（仅用于补齐演示数据与生成 Web 素材）
- 后端 `tanhui-backend` 可运行

### 1.2 后端

当前联调使用本机 **8000** 后端，实际运行目录为：

```text
C:\Users\85046\Desktop\碳惠陇原统一后端-tanhui-backend\tanhui-backend
```

该实例已补齐设计稿演示数据，并已应用助农接口序列化修复；其开发库已备份为 `tanhui_dev.db.bak-20261124`。

启动/重启 8000：

```bash
cd "C:/Users/85046/Desktop/碳惠陇原统一后端-tanhui-backend/tanhui-backend"
# 使用该目录原有 Python 环境（当前由你启动的 anaconda 实例运行）
uvicorn app.main:app --reload --port 8000
```

> 也可以使用交接提供的 `C:\Users\85046\Desktop\tanhui-backend`（同样已修复并补齐数据）另起 8001 作为备用：
>
> ```bash
> cd C:/Users/85046/Desktop/tanhui-backend
> C:/Users/85046/Desktop/tanhui-backend-fixed/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
> ```
>
> 8001 是额外 Python 进程，内存紧张时可能被系统回收；日常优先使用 8000。

**重要后端修复**：`app/modules/aid/router.py` 的 `ProjectOut.goal_amount/raised_amount` 原声明为 `str`，但 ORM 字段是 `Decimal`，导致 `GET /api/v1/aid/projects` 返回 500。已改为 `MoneyOut`（序列化为两位小数字符串），与 OpenAPI 契约一致。该修复已同时应用到 8000 实际运行目录和交接的 `tanhui-backend`。

### 1.3 补齐演示数据（已执行，可幂等重跑）

前提：后端开发库已执行 `python -m scripts.seed`（空库会建表并写入基础账号/分类）。演示数据通过后端 ORM 写入，不修改后端接口与业务代码。

对**当前 8000 运行目录**补齐：

```bash
cd C:/Users/85046/Desktop/碳惠陇原
TANHUI_BACKEND_DIR="C:/Users/85046/Desktop/碳惠陇原统一后端-tanhui-backend/tanhui-backend" \
C:/Users/85046/Desktop/tanhui-backend-fixed/.venv/Scripts/python.exe scripts/seed_demo.py
```

对交接的 `tanhui-backend` 补齐（默认路径）：

```bash
cd C:/Users/85046/Desktop/tanhui-backend
C:/Users/85046/Desktop/tanhui-backend-fixed/.venv/Scripts/python.exe "C:/Users/85046/Desktop/碳惠陇原/scripts/seed_demo.py"
```

脚本会补齐：6 个设计稿分类、7 个设计稿商品与 SKU/库存/4 张详情图、绿色资料（审核通过，不虚构认证）、CMS 首页（Banner + 精选商品）、4 个助农项目、买家演示地址、绿色积分、3 笔示例订单。全部为演示数据。联调过程中还创建了若干测试订单、退款申请与积分兑换记录，均保留在开发库中。

### 1.4 前端

```bash
cd C:/Users/85046/Desktop/碳惠陇原
npm install
npm run dev
```

- `.env.local` 已将代理指向 `http://127.0.0.1:8000`。
- 默认访问 `http://127.0.0.1:5173`。
- 如 5173 已被旧进程占用，可直接再起一个端口：

```bash
npx vite --host 127.0.0.1 --port 5174
```

访问 `http://127.0.0.1:5174`。本次已在该端口验证通过。

如需临时切换其他后端：

```bash
# Git Bash
VITE_PROXY_TARGET=http://127.0.0.1:8001 npm run dev
```

```powershell
# PowerShell
$env:VITE_PROXY_TARGET="http://127.0.0.1:8001"; npm run dev
```

> 注意：`.env.local` 的优先级高于进程环境变量；如果切换目标，请同步修改 `.env.local` 或删除它。

**演示账号**：`buyer@tanhui.example.com` / `Passw0rd!123`（登录页提供“填入演示账号”按钮）。

### 1.5 素材生成（可选）

素材包已转换为 Web 体积资源（WebP/PNG），如需重新生成：

```bash
python scripts/prepare_assets.py
```

需要 Pillow。脚本会同时写入前端 `public/assets` 与后端 `uploads/demo`。

---

### 1.6 常见问题

- **`npm install` 提示 esbuild install scripts 未执行**：执行 `npm rebuild esbuild` 后重新 `npm run dev`。
- **页面请求 404/网络错误**：确认后端已启动；`.env.local` 当前指向 `http://127.0.0.1:8000`。如改用 8001，请同步修改 `.env.local`（它的优先级高于进程环境变量）。
- **5173 仍显示空白/接口 500**：5173 可能是在旧环境变量（8001）下启动的；在运行 Vite 的终端按 `Ctrl+C` 后重新 `npm run dev`，或直接使用 `npx vite --host 127.0.0.1 --port 5174`。
- **助农项目 500**：确认运行目录的 `app/modules/aid/router.py` 已使用 `MoneyOut`，并让 `--reload` 后端完成重载。
- **8001 被系统回收**：8001 是额外 Python 进程，内存紧张时可能被停止；日常优先使用已在运行的 8000。

## 2. 已实现页面

| 模块 | 路由 | 说明 |
|---|---|---|
| 首页 | `/` | CMS Banner/精选商品、快捷分类、甘肃产地地图、绿色消费专区；CMS 失败时静态降级 |
| 全部商品 | `/products` | 关键词/分类/排序/分页；加载/空/错误状态 |
| 商品详情 | `/products/:id` | 图集、SKU、数量、绿色资料、助农项目、产地关联商品、规格参数 |
| 购物车 | `/cart` | 按店铺分组、勾选、改量、删除、服务端小计 |
| 确认订单 | `/checkout` | 地址选择/新增、服务端预览计价、积分抵扣开关、备注、幂等下单 |
| 订单支付 | `/pay/:orderId` | 支付单状态、Mock 沙箱支付、支付结果 |
| 登录/注册 | `/login`、`/register` | 演示账号、表单校验、MFA 错误分支 |
| 个人中心 | `/account` | 概览、订单状态统计、最近订单、快捷入口 |
| 我的订单 | `/account/orders` | 状态筛选、分页、取消/确认收货/退款/物流 |
| 订单详情 | `/account/orders/:id` | 状态时间线、金额明细、店铺子单、退款记录 |
| 物流详情 | `/account/orders/:id/logistics` | 发货单与轨迹（明确标注 Mock） |
| 申请退款 | `/account/orders/:id/refund` | 按店铺子单退款、金额校验、退款记录 |
| 收货地址 | `/account/addresses` | 增删改、默认地址、结算页复用 |
| 绿色积分 | `/account/points` | 余额、流水筛选、兑换（Mock 权益）、凭证码 |
| 个人资料 | `/account/profile` | 昵称/性别/生日/简介/头像地址 |
| 消息通知 | `/account/notifications` | 未读筛选、单条已读、全部已读 |
| 甘肃产地 | `/origin` | 产地横幅、产区入口、产地商品 |
| 品牌故事 | `/brand` | 品牌横幅、三段品牌叙事、品牌好物商品卡 |
| 助农项目 | `/aid`、`/aid/:id` | 项目进度、项目详情、演示数据声明 |
| 绿色消费专区 | `/green` | 绿色资料商品、产地信息、核验状态说明 |
| 平台公告 | `/notices`、`/notices/:id` | CMS 公告列表与纯文本详情 |
| 帮助中心 | `/help` | 下单/支付/配送/售后/积分 FAQ |
| 404 | 任意未知路由 | 404 页面 |

---

## 3. 前后端衔接要点

- 统一响应：`{ code, message, data, request_id }`；错误码按 `docs/conventions.md` 分支处理。
- 认证：`Authorization: Bearer <access>`；`401` 时静默 `POST /auth/refresh` 并重放一次；刷新失败才清理会话并跳登录。
- 金额：全部按后端字符串直显（`utils/format.ts` 的 `money()`），**不做价格/运费/积分抵扣的前端运算**。
- 分页：`page/page_size` → `data.items + data.pagination`。
- 商家数据范围：消费者端不涉及 `store_id` 越权；`store_id` 仅用于商品筛选。
- CMS：`GET /client/config/{page_key}`、`/client/notices`、`/client/banners` 返回**裸 JSON**（不包 `ApiResponse`），请求层单独处理；首页只渲染白名单组件，未知组件安全降级。
- 支付：`/payments/{order_id}/init` → `/payments/mock/pay`，页面明确标注 **Mock 沙箱，未接入真实支付**。
- 物流：后端轨迹为 Mock，页面明确标注。
- 积分兑换：后端返回 `mock: true`，页面标注“Mock 权益”。
- 绿色资料：未核验碳数据明确显示“未核验”，不冒充已核验；演示商品不虚构认证。

详细页面→API→DTO 对照见 [`docs/page-api-map.md`](docs/page-api-map.md)。

---

## 4. 目录结构

```
碳惠陇原/
├─ public/assets/            # 设计素材（商品图/横幅/分类图标/Logo/登录背景）
├─ scripts/
│  ├─ prepare_assets.py      # 素材转换与裁切（系统 Python + Pillow）
│  ├─ seed_demo.py           # 演示数据补齐（后端 ORM）
│  ├─ smoke.mjs              # 全流程 Playwright 冒烟
│  ├─ buynow.mjs             # 立即购买直达结算验证
│  ├─ refund.mjs             # 退款申请验证
│  ├─ points.mjs             # 积分兑换验证
│  └─ visual.mjs             # 指定页面截图（支持 MOBILE=1）
├─ src/
│  ├─ api/                   # http.ts（统一请求/刷新/CMS 裸 JSON）、index.ts、types.ts
│  ├─ assets/main.css        # 设计 Token、组件、页面、响应式
│  ├─ components/            # Header/Footer/ProductCard/StateBlock/CMS 区块等
│  ├─ composables/           # useOrderActions
│  ├─ router/                # 路由与登录守卫
│  ├─ stores/                # auth/cart/checkout/points/toast/confirm
│  ├─ utils/                 # 金额/日期/状态文案/CMS 安全解析
│  └─ views/                 # 消费者端页面与 account 子页
├─ docs/                     # 架构、页面-API 对照、后端说明、测试记录
├─ .env.example
├─ eslint.config.js
├─ .prettierrc.json
└─ vite.config.ts
```

---

## 5. 质量检查

```bash
npm run typecheck     # vue-tsc，0 error
npm run lint          # ESLint，0 error / 0 warning
npm run build         # 生产构建
npm run dev           # 开发
node scripts/smoke.mjs  # 需要 5173 开发服务
```

本次验证结果：

- `typecheck`：通过
- `lint`：0 error / 0 warning
- `build`：通过（Vite 生产构建）
- Playwright（系统 Edge）全流程：
  - 首页 4 个精选商品、价格 `¥59.90` 等正确
  - 商品列表 6 个/页、2 页、分类侧栏 7 项（全部 + 6 分类）
  - 商品详情 4 张图、2 个 SKU、5 个关联商品、绿色资料标签
  - 登录 → 加购 → 购物车 → 结算预览 → 提交订单 → Mock 沙箱支付成功
  - 订单列表、积分流水、退款申请、积分兑换凭证
  - 1440px 与 390px 均无横向溢出；控制台 0 error、页面 0 error

截图位于 `artifacts/`（已加入 `.gitignore`，不属于构建产物）。

---

## 6. 未实现 / 依赖与限制

- **管理员端、商家端、Android**：本轮未做（按确认范围）。
- **评价/评分、销量、优惠券、收藏、浏览足迹、在线客服、发票**：后端无对应接口，页面未虚构相关功能。
- **真实支付/原路退款/物流轨迹/积分兑换权益**：均为 Mock/仿真，页面已标注。
- **CMS 首页区块**：后端只提供 `banner/product_grid/rich_text` 等白名单组件；设计稿中的快捷分类、产地地图、绿色专区由前端静态模块与 API 组合呈现，CMS 富文本区块当前未启用。
- **商品详情接口缺少 `min_price/cover_url`**：后端 `GET /products/{id}` 未回填这两个列表字段；首页 CMS 精选商品改用列表接口按 ID 映射，详情页使用 SKU 价格与图片列表，不受影响。
- **管理员密码**：后端 seed 随机生成，消费者端不需要；如后续做管理端需重置开发库或提供密码。
- **演示数据**：商品名称/价格/描述/产地/助农金额均为演示数据，不代表真实商品、认证或募捐。
- **业务策略**：运费/佣金/积分比例/退款时限等以后端仿真配置与 `pending-decisions.md` 为准；前端不写死。
- **浏览器兼容**：现代 Chromium/Edge/Chrome；未测试旧版 IE。

---

## 7. 说明

- 本仓库不包含支付密钥、服务端密钥或真实凭证。
- Access/Refresh Token 存于 `localStorage`（消费者端），刷新即轮换；退出登录会调用后端撤销当前会话。
- 设计素材来自 `图片素材包`，商品图在没有后端 `cover_url` 时使用设计稿对应素材兜底，并在代码中标注为“设计稿视觉兜底”，不冒充后端上传图片。
