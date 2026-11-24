# 「全部商品」页改版与素材迁移说明

> 本次在现有消费者商城上做增量改造：不改业务规则、API 契约、路由与权限；保留购物车/加购/登录/订单等既有实现。
> 视觉参考：用户提供的「全部商品」目标版式截图 + 文字说明。

---

## 1. 改动文件清单

### 全部商品页与商品展示

| 文件 | 改动 |
|---|---|
| `src/views/CatalogView.vue` | 重构顶部 5 分类导航（线性图标 + 选中绿色胶囊 + 右侧蓝天梯田小卡）；左侧「甘肃产地」列表；右侧商品网格；保留分页/筛选/排序；新增好评推荐区块（本地 Mock，显著标注） |
| `src/components/ProductCard.vue` | 新增 `variant="catalog"`：生鲜用商品主图，带推荐吃法的食材用菜品图；加「推荐吃法」金色标记；加载失败回退商品主图 |
| `src/views/ProductDetailView.vue` | 新增「推荐吃法」模块（4 道菜品图）；图片懒加载与失败回退 |
| `src/utils/productMedia.ts` | **新增**：商品 → 菜品图映射（土豆炖牛腩/枣夹核桃/枸杞银耳羹/西芹炒百合） |
| `src/utils/format.ts` | 图片路径迁移到 `/images`；新增线性分类图标映射；商品图/详情图回退路径更新 |
| `src/assets/main.css` | 设计 Token 微调（圆角/阴影/丰收金）；新增全部商品 v2、分类小卡、产地列表、菜品标记、吃法模块、Mock 徽标、三档响应式样式 |
| `index.html` | favicon 指向 `/images/logo/favicon.png` |

### 全局素材路径迁移（代码中不再引用桌面路径/旧 assets）

| 文件 | 改动 |
|---|---|
| `src/components/SiteHeader.vue` | Logo → `/images/logo/logo.png` |
| `src/components/SiteFooter.vue` | Logo → `/images/logo/logo.png`，懒加载 |
| `src/components/sections/BannerSection.vue` | 懒加载 + 加载失败回退 |
| `src/components/sections/AidProjectSection.vue` | 助农卡片图回退到 `/images/banners/aid-card-farmer.webp` |
| `src/views/HomeView.vue` | 5 个分类改用扁平 PNG；首页主视觉/产地卡/绿色通栏路径更新；图片懒加载 |
| `src/views/LoginView.vue` / `RegisterView.vue` | 登录背景 → `/images/backgrounds/login-bg.webp`；Logo → `/images/logo/logo.png` |
| `src/views/OriginView.vue` | 顶部横幅 → `/images/banners/origin-map.webp` |
| `src/views/AidView.vue` / `AidDetailView.vue` | 顶部横幅/项目图回退路径更新 |
| `src/views/BrandView.vue` | 品牌横幅/三段故事图使用新素材 |
| `src/views/GreenView.vue` | 绿色专区横幅 → `/images/banners/green.webp` |
| `src/views/account/OrderDetailView.vue` | 订单商品图懒加载 |

### 素材/验证脚本

| 文件 | 用途 |
|---|---|
| `scripts/prepare_images2.py` | **新增**：把「图片素材包2」转换为 `public/images`，并同步到运行中后端的 `uploads/demo` |
| `scripts/catalog-redesign.mjs` | **新增**：1440/768/390 全部商品页视觉验收、分类切换、排序、吃法模块、图片加载检查 |

### 运行中后端的必要修复（不改契约）

| 文件 | 改动 |
|---|---|
| `…/碳惠陇原统一后端-tanhui-backend/tanhui-backend/app/modules/catalog/service.py` | 修复 `price_asc` 排序被默认 `created_at DESC` 覆盖的问题；仅让 `price_asc` / `created_desc` 各自生效 |
| `…/tanhui-backend/app/modules/aid/router.py` | 之前已修复 `ProjectOut.goal_amount/raised_amount` 的 Decimal→MoneyOut 序列化（助农 500） |

> 运行中后端开发库已备份：`tanhui_dev.db.bak-20261124`；演示数据通过 `scripts/seed_demo.py` 写入。

---

## 2. 素材引用对照表

> 源目录：`C:\Users\85046\Desktop\图片素材包2`
> 前端统一使用 `/images/...` 相对路径；后端 API 图片使用同步后的 `/uploads/demo/...`。

| 源文件 | 前端输出 | 用途 | 格式 |
|---|---|---|---|
| `Logo与背景/碳惠陇原Logo_透明底.png` | `public/images/logo/logo.png` | 顶部导航、页脚、登录/注册 Logo | 透明 PNG |
| 同上（左侧山峰裁切） | `public/images/logo/favicon.png` | favicon | 透明 PNG |
| `Logo与背景/登录页背景.png` | `public/images/backgrounds/login-bg.webp` | 登录/注册全屏背景 | WebP |
| `横幅/首页主视觉横幅.png` | `public/images/banners/home-hero.webp`；后端 `uploads/demo/banners/home-hero.webp` | 首页首帧 / CMS Banner | WebP |
| `横幅/绿色消费专区横幅.png` | `public/images/banners/green.webp`；派生 `green-card.webp` | 首页绿色通栏、绿色页横幅、品牌故事卡片 | WebP |
| `横幅/产地地图横幅.png` | `public/images/banners/origin-map.webp`；派生 `origin-map-card.webp` | 甘肃产地页横幅、首页产地小卡 | WebP |
| `横幅/助农项目横幅.png` | `public/images/banners/aid.webp`；派生 `aid-card-farmer.webp` | 助农页横幅、品牌故事卡片、项目图回退 | WebP |
| `横幅/品牌故事横幅.png` | `public/images/banners/brand.webp` | 品牌故事页横幅 | WebP |
| `横幅/产地合作社横幅.png` | `public/images/banners/origin-coop.webp`；派生 `aid-card-farm.webp` | 合作社/品牌故事/助农项目卡片 | WebP |
| `横幅/商品页横幅.png` | `public/images/banners/catalog-banner.webp` | 保留备用（新版全部商品页以分类导航为顶部，不强制使用） | WebP |
| `横幅/分类区蓝天梯田小卡.png` | `public/images/banners/category-card.webp` | 全部商品页分类区右侧小卡 | WebP |
| `分类图标/新鲜水果.png` 等 5 张（扁平） | `public/images/categories/flat/{fruit,grains,food,culture,points}.png`；后端 `uploads/demo/categories/*.webp` | 首页 5 个分类入口 | 透明 PNG |
| `分类图标/线性_*.png` 5 张 | `public/images/categories/linear/{fruit,grains,food,culture,points}.png` | 全部商品页顶部分类导航 | 透明 PNG |
| `商品主图/静宁苹果.png` 等 7 张 | `public/images/products/{slug}.webp` + `-1..4.webp`；后端 `uploads/demo/products/*` | 商品卡、详情主图/图集、左侧产地缩略图 | WebP |
| `菜品图/土豆炖牛腩.png` | `public/images/dishes/potato-beef.webp` | 定西马铃薯商品卡 + 详情吃法 | WebP |
| `菜品图/枣夹核桃.png` | `public/images/dishes/jujube-walnut.webp` | 临泽小枣商品卡 + 详情吃法 | WebP |
| `菜品图/枸杞银耳羹.png` | `public/images/dishes/goji-soup.webp` | 甘肃枸杞商品卡 + 详情吃法 | WebP |
| `菜品图/西芹炒百合.png` | `public/images/dishes/lily-stirfry.webp` | 兰州百合商品卡 + 详情吃法 | WebP |

**图片规则**：所有展示图片均有 `alt`；非首屏图片 `loading="lazy"` + `decoding="async"`；商品卡/产地列表/横幅均有加载失败回退。Banner 使用 `object-fit: cover`，移动端通过 `object-position` 保住主体。

---

## 3. 全部商品页结构

```
顶部标题（全部商品 / 共 N 件）
├─ 白色大圆角分类导航
│  ├─ 5 个分类胶囊（线性图标 + 名称；选中森林绿胶囊白字）
│  └─ 右侧「甘肃产地」蓝天梯田小卡
├─ 精选好评推荐（本地 Mock，显著标注）
├─ 左栏「甘肃产地」列表（5 条：缩略图 + 产地/品名 + 卖点 + 查看详情）
└─ 右栏商品网格（生鲜商品主图 / 4 个食材菜品图；价格 + 加购）
   └─ 分页
```

- 分类点击走既有 `GET /categories` + `GET /products?category_id=...`；再次点击当前分类可清除筛选。
- 左栏产地/卖点来自 `Product` 列表字段 + 既有 `GET /green/products/{id}` 的 `profile.origin`；无绿色资料时回退店铺名，不新增字段。
- 排序保留综合/价格；「销量优先」因后端无销量字段继续置灰。价格排序已在运行中 8000 后端修复。
- 加购/详情/登录复用既有 service 与路由，页面不新增请求散落。
- 推荐好评没有后端评价接口：分数为**本地 Mock**，页面显示「Mock 演示」「演示好评」，并注明“评价接口尚未接入，不代表真实评价”。

---

## 4. 验收结果

| 检查 | 1440 | 768 | 390 |
|---|---|---|---|
| 页面横向溢出 | 0 | 0 | 0 |
| 分类胶囊 | 5 | 5 | 5 |
| 线性图标 | 5 | 5 | 5 |
| 右侧小卡 | 显示（2 列布局） | 全宽显示（1 列布局） | 全宽显示 |
| 甘肃产地列表 | 5 条 | 5 条（2 列） | 5 条（1 列） |
| 商品卡 | 6（3 列） | 6（2 列） | 6（2 列） |
| 菜品图卡 | 4 | 4 | 4 |
| Mock 好评标记 | 显示 | 显示 | 显示 |
| 详情吃法模块 | 西芹炒百合，图片加载 | — | — |

- ESLint：0 error / 0 warning
- Prettier：`format:check` 通过
- TypeScript：`vue-tsc --noEmit` 通过
- Vite 生产构建通过
- 控制台/页面错误：0；图片失败请求：0

---

## 5. 未完成项与待确认项

| # | 事项 | 状态/说明 | 需要确认 |
|---|---|---|---|
| 1 | 精选好评推荐 | 无评价接口，当前为**明确标注的本地 Mock** | 目标截图若没有此模块，可移除；若有，是否后续接真实评价 API |
| 2 | 「甘味文创」分类 | 演示数据暂无文创商品，点击显示空态 | 是否需要补充文创商品与图片（当前素材包无对应商品图） |
| 3 | 销量优先 | 后端无销量字段，保持置灰 | 是否需要后端增加销量统计 |
| 4 | 分类小卡在平板/手机 | <=1100px 由“右侧”改为“分类下方全宽”，避免窄屏挤压 | 是否接受该响应式处理 |
| 5 | 「商品页横幅」素材 | 新版顶部改为分类导航，商品页横幅保留未用 | 是否需要在其他位置使用 |
| 6 | 旧 `public/assets` | 已无代码引用，可清理 | 是否删除以减小体积 |
| 7 | 真实评价/收藏/优惠券等 | 无后端接口，未新增 | 后续是否纳入 |
| 8 | 运行中后端 | 8000 目录已补数据/素材，并修复助农与价格排序；开发库已备份 | 若切换到其他后端副本，需要同步这两处修复与 `uploads/demo` |

---

## 6. 验证命令

```bash
npm run typecheck
npm run lint
npm run format:check
npm run build
node scripts/catalog-redesign.mjs   # SMOKE_BASE=http://127.0.0.1:5174
```

截图：`artifacts/catalog-v2-1440.png`、`catalog-v2-768.png`、`catalog-v2-390.png`、`catalog-v2-recipe.png`、`catalog-v2-category-1440.png`。
