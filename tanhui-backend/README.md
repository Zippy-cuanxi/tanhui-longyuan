# 碳惠陇原统一后端（tanhui-backend）

面向甘肃特色农产品的多商家助农电商平台统一后端。**当前所有业务策略参数（佣金/运费/积分/支付等）均为仿真配置**，修改入口见下方「仿真参数」。

## 技术栈

Python 3.12+ · FastAPI · SQLAlchemy 2.x · Alembic · PostgreSQL（开发默认 SQLite）· Redis（可选，未配置时进程内存后备）· Celery（未配置 broker 时任务同步执行）

## 快速开始（本地开发）

```bash
# 1) 安装依赖（建议虚拟环境）
pip install -r requirements.txt -r requirements-dev.txt

# 2) 初始化仿真数据（空库自动建表 + 种子数据，幂等）
python -m scripts.seed
#   正式部署请改用: alembic upgrade head

# 3) 启动
uvicorn app.main:app --reload --port 8000
#   交互式文档: http://localhost:8000/docs
```

**演示账号**（种子数据，均可直接登录）：

| 角色 | 账号 | 密码 |
|---|---|---|
| 消费者 | buyer@tanhui.example.com | Passw0rd!123 |
| 商家 | merchant1@tanhui.example.com | Passw0rd!123 |
| 管理员×5 | admin@ / ops@ / auditor@ / finance@ / cs@tanhui.example.com | 随机生成（见 seed 输出，重跑 `python -m scripts.seed` 不会重复创建） |

## 运行测试

```bash
python -m pytest tests/ -q          # 33 个用例全通过
```

覆盖：认证/刷新轮换/复用检测、RBAC 与商家隔离（IDOR）、商品审核状态机、
**库存并发防超卖（20线程抢10库存）**、多商家拆单/服务端计价/快照/幂等/防篡改、
**支付回调验签+金额核对+幂等**、退款与绿豆冲正、CMS 白名单/发布/回滚/安全降级、
OpenAPI 一致性、Alembic 迁移有效性。

## Docker 部署（含 PostgreSQL + Redis + Worker）

```bash
docker compose up -d --build     # api:8000，首启自动执行迁移
```

## 仿真参数（业务未定策略，集中可改）

全部位于 `app/core/config.py` 与 `.env.example`，标注【仿真参数】：

| 参数 | 默认值 | 说明 |
|---|---|---|
| SHIPPING_FLAT_FEE / FREE_THRESHOLD | 8.00 / 99.00 | 单店运费/包邮门槛（元） |
| COMMISSION_RATE | 5% | 平台佣金（按订单实付） |
| SETTLEMENT_PERIOD_DAYS | 15 | 结算周期（天） |
| POINTS_EARN_RATE | 1 | 每消费 1 元发 1 绿豆 |
| POINTS_DEDUCT_RATE / MAX_PERCENT | 100:1 / 50% | 绿豆抵扣比例与上限 |
| ORDER_PAY_EXPIRE_MINUTES | 30 | 支付超时自动关单 |
| MOCK_PAYMENT_SECRET / MERCHANT_NO | 见配置 | 沙箱支付签名密钥/商户号 |

修改方式：环境变量（`TANHUI_` 前缀）或 `.env`，无需改代码。

## 文档索引（docs/）

| 文件 | 内容 |
|---|---|
| openapi.yaml / openapi.json | OpenAPI 3.1 契约（134 接口，前端据此生成 client） |
| api-list.md | 三端 API 清单（按 tag 分组） |
| er-diagram.md | ER 图（Mermaid，57 表） |
| field-dictionary.md | 字段字典（自动生成） |
| conventions.md | 错误码/分页/时间/金额/ID 规范 |
| state-machines.md | 订单/支付/退款/商品/商家/CMS 状态机 |
| pending-decisions.md | 待业务确认事项清单 |
| implementation-status.md | 已实现/未实现/Mock/风险清单 |

## 重要安全与设计约定

- 统一响应 `{code, message, data, request_id}`；金额一律字符串两位小数；时间 ISO8601 UTC
- 密码 Argon2id；Access/Refresh 双令牌，刷新即轮换，复用检测撤销整链
- 商家数据范围 100% 服务端推导（store_members），客户端 store_id 仅作选择并强校验
- 库存防超卖：条件 UPDATE 原子预占（不依赖应用锁）
- 支付为 **Mock 沙箱**（mock_sandbox），回调处理链路与真实渠道一致，未接入真实渠道
- CMS 组件白名单 + 配置 Pydantic 校验，未知组件客户端安全降级

## Celery 定时任务

```bash
# 配置 TANHUI_CELERY_BROKER_URL 后：
celery -A app.worker.celery_app worker -B --loglevel=info
# 任务：释放超时库存预占、关闭支付超时订单（每 1-2 分钟）
```
