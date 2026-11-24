# 前端架构说明

## 1. 分层

```
views（页面）
  ├─ components（通用组件 + CMS 区块）
  ├─ composables（订单动作等跨页逻辑）
  ├─ stores（Pinia：auth/cart/checkout/points/toast/confirm）
  └─ api（service 层：index.ts → http.ts → 后端 /api/v1）
```

- **页面不直接 fetch**；所有请求集中在 `src/api/index.ts`。
- `http.ts` 统一处理：信封 `{code,message,data,request_id}`、Bearer、401 刷新与重放、错误码、超时、请求 ID。
- `requestRaw` 单独处理 CMS 的裸 JSON 接口与 ETag。
- 金额、日期、状态文案集中在 `src/utils/format.ts`。

## 2. 认证

- 登录：`POST /auth/login` → 保存 access/refresh → `GET /users/me`。
- 401：最多静默刷新一次并重放；刷新失败清理 token、广播 `auth:expired`、路由守卫跳登录。
- 刷新令牌轮换由后端负责；前端不缓存用户权限结论。
- 路由守卫只做体验层：`requiresAuth` / `guestOnly`；不替代后端权限。
- 消费者端不涉及商家 `store_id` 数据范围；商品 `store_id` 仅用于筛选。

## 3. 状态

| Store | 职责 |
|---|---|
| `auth` | 用户/资料、登录注册、登出、会话失效 |
| `cart` | 购物车、勾选/改量/删除、角标、服务端小计 |
| `checkout` | “立即购买”直购条目（sessionStorage 保持刷新） |
| `points` | 绿色积分余额（跨页同步） |
| `toast` | 全局提示、request_id 复制 |
| `confirm` | Promise 化二次确认（删除/取消/确认收货/兑换） |

## 4. CMS 渲染

- 读取 `GET /client/config/{page_key}`（裸 JSON）。
- 只渲染白名单：`banner`、`product_grid`、`rich_text`、`points_panel`、`aid_project`、`navigation`。
- 未知组件跳过，不影响整页。
- 跳转仅允许站内 `/` 路由或 `https://` 外链（前端再次校验）。
- 价格、库存、订单、积分仍调用权威业务 API，不依赖 CMS。
- 首页设计稿中 CMS 没有的模块（快捷分类、产地地图、绿色专区）由静态设计模块 + 业务 API 组合，保证视觉完整。

## 5. 五态与边界

- 统一 `StateBlock`：loading / error / empty / forbidden（组件支持）/ success。
- 列表页：骨架/加载、空态、错误重试、分页。
- 表单：必填/格式校验、提交禁用、错误提示、成功 Toast。
- 关键操作：二次确认 + 结果反馈 + 刷新数据。
- 401 静默刷新；422 展示首条字段错误；409 业务码分支提示。
- 断点：1440 / 768 / 390；375px 以下不横向溢出。
- 金额一律字符串直显，不做前端权威运算；`checkout` 的可退金额仅用于输入约束，最终以服务端校验为准。

## 6. 设计 Token

`src/assets/main.css` 顶部集中定义：

- 森林绿 `#064b31/#075d3b/#0b7146/#18a05f`
- 米白 `#faf7ee/#f3edda`
- 丰收金 `#c9a227/#f2e5c2`
- 价格红 `#d93a42`
- 字体：正文 `PingFang SC / Microsoft YaHei`；展示标题 `Songti SC / STSong / Noto Serif SC`
- 圆角、阴影、容器 1280px、Header 82px、断点 1180/900/640

## 7. 素材策略

- 设计素材包2 → `public/images` 的 WebP/PNG（商品 900px 卡片 + 1200px 详情图；横幅 2000–2200px；Logo/分类图标为透明 PNG；4 张菜品图 WebP）。
- 同一份商品图写入后端 `uploads/demo`，API 的 `cover_url/image_url` 指向上传路径，避免前端伪造图片字段。
- 无 `cover_url` 时按商品名映射设计稿素材，代码中标注为视觉兜底。
- 助农卡片、首页产地卡片从横幅中裁切，避开画面内的大字文案。

## 8. 目录职责

```
src/api       service + types + http
src/components  通用组件、CMS 区块
src/composables 订单动作
src/stores    Pinia
src/utils     格式化、CMS 安全解析
src/views     页面（account 子目录为个人中心）
src/assets    设计 Token 与全局样式
```

## 9. 测试

- `npm run typecheck` / `npm run lint` / `npm run build`。
- `scripts/smoke.mjs`：首页→列表→详情→登录→加购→结算→下单→沙箱支付→订单→积分，并检查 1440/390 溢出与控制台错误。
- `scripts/buynow.mjs`、`refund.mjs`、`points.mjs`：直购、退款、积分兑换专项验证。
- `scripts/visual.mjs`：按路由截图，`MOBILE=1` 输出 390px 版本。
