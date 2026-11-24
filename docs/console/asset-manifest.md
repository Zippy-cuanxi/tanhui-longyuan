# 后台静态资源与图标映射（补齐说明）

源素材未提供 `assets/console/manifest.md`，本文件根据实际可用图标/图片与菜单用途整理，作为后台侧栏图标和页面空态的映射依据。资源均位于 `public/console-assets/`，页面只引用站内路径，无外部链接。

## 图标（每项同时提供 gray / green）

| 图标基名 | 菜单/用途 |
| --- | --- |
| `workbench` | 工作台 |
| `goods` | 商品列表 / 商品管理 |
| `audit` | 发布商品、商品审核、入驻审核 |
| `orders` | 订单管理 |
| `aftersale` | 售后处理、售后仲裁 |
| `settlement` | 结算中心 |
| `shop` | 店铺管理 |
| `data` | 数据看板 / 数据概览 |
| `bell` | 消息通知 |
| `user` | 用户管理、商家子账号 |
| `points` | 绿色积分、绿色消费专区 |
| `review` | 评价管理 |
| `export` | 批量导入/发货、导出 |
| `help` | 帮助中心 |
| `merchant` | 商家列表 |
| `content` | 分类/公告/Banner 等运营内容 |
| `origin` | 产地管理 |
| `finance` | 财务管理 |
| `system` | 系统设置 |
| `log` | 操作日志 |
| `charity` | 助农标签/公益 |
| `message` | 消息相关（备用） |
| `search` / `filter` | 搜索/筛选（备用） |

侧栏通过 `/console-assets/icons/{icon}-{gray|green}.svg` 切换普通/选中态。

## 图片

| 文件 | 用途 |
| --- | --- |
| `login-bg.png` | 登录页梯田背景（01a 分栏风格） |
| `apple.png` `potato.png` `melon.png` `goji.png` `jujube.png` `lily.png` `danggui.png` | 演示商品图（静宁苹果、定西马铃薯、民勤蜜瓜、甘肃枸杞、临泽小枣、兰州百合、岷县当归） |
| `shop-logo-1.png` ~ `shop-logo-3.png` | 店铺 Logo / 资质占位演示 |
| `avatar-merchant.png` / `avatar-admin.png` | 商家/管理员头像 |
| `state-pending.png` | 入驻审核中状态页 |
| `state-rejected.png` | 入驻驳回状态页 |
| `state-frozen.png` | 商家冻结状态页 |
| `coming-soon.png` | 二期功能占位页 |
| `no-permission.png` | 403 无权限页 |
| `error-404.png` | 加载失败/404 状态 |
| `empty-list.png` | 通用列表空态 |
| `empty-goods.png` | 商品空态 |
| `empty-orders.png` | 订单/售后空态 |
| `empty-search.png` | 搜索空态 |
| `image-empty.png` | 商品图片缺失占位 |
| `icons-overview.png` | 图标总览参考 |

## 设计图

- 已提供并已使用：`design/console/00-design-spec.png`（色彩/圆角/间距/组件规范）、`design/console/01a-login-merchant.png`（登录分栏、品牌、卡片）。
- 未提供：`02`–`16` 页面设计图。页面按 00 规范板与规格文档的业务结构实现，表格、图表的密度与信息层级为规范化推导。
