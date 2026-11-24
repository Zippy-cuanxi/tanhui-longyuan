# 数据库字段字典（自动生成，请勿手改）

共 57 张表。通用约定：
- 主键 `id` UUID；`created_at`/`updated_at` TIMESTAMPTZ(UTC)
- 金额 NUMERIC(12,2)；JSONB 用于审计详情/规则配置/页面快照

## aid_projects

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| cooperative_id | UUID | 否 |  | → cooperatives.id，索引 |
| title | VARCHAR(128) | 否 |  |  |
| cover_url | VARCHAR(512) | 是 |  |  |
| description | TEXT | 是 |  |  |
| goal_amount | NUMERIC(12,2) | 是 |  |  |
| raised_amount | NUMERIC(12,2) | 否 | 0 |  |
| status | VARCHAR(16) | 否 | draft | 索引 |
| reviewed_by | UUID | 是 |  |  |
| published_at | TIMESTAMPTZ | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9ae7a60> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9ae7ce0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9ae7d80> |  |

## aid_records

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| project_id | UUID | 否 |  | 索引 |
| user_id | UUID | 是 |  | 索引 |
| order_id | UUID | 是 |  | 索引 |
| amount | NUMERIC(12,2) | 否 |  |  |
| kind | VARCHAR(16) | 否 | order |  |
| note | VARCHAR(255) | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9ae7b00> |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9b211c0> | 主键 |

## carbon_assessments

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| product_id | UUID | 否 |  | 索引 |
| co2e_per_unit | NUMERIC(12, 4) | 否 |  |  |
| unit | VARCHAR(16) | 否 | kg |  |
| methodology | VARCHAR(255) | 是 |  |  |
| verified | BOOLEAN | 否 | False |  |
| verifier_id | UUID | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b99f3240> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b99f3420> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b99f34c0> |  |

## cart_items

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| cart_id | UUID | 否 |  | → carts.id，索引 |
| sku_id | UUID | 否 |  | → product_skus.id，索引 |
| quantity | INTEGER | 否 | 1 |  |
| checked | BOOLEAN | 否 | True |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9b577e0> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b579c0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b57a60> |  |

## carts

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| user_id | UUID | 否 |  | → users.id，唯一 |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9b565c0> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b567a0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b56840> |  |

## categories

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| parent_id | UUID | 是 |  | → categories.id，索引 |
| name | VARCHAR(64) | 否 |  |  |
| icon_url | VARCHAR(512) | 是 |  |  |
| sort | INTEGER | 否 | 0 | 索引 |
| is_active | BOOLEAN | 否 | True |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9b84a40> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b84c20> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b84cc0> |  |

## cms_announcements

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| title | VARCHAR(128) | 否 |  |  |
| content | TEXT | 否 |  |  |
| status | VARCHAR(16) | 否 | draft |  |
| published_at | TIMESTAMPTZ | 是 |  |  |
| start_at | TIMESTAMPTZ | 是 |  |  |
| end_at | TIMESTAMPTZ | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9805440> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9805620> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b98056c0> |  |

## cms_banners

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| title | VARCHAR(128) | 否 |  |  |
| image_url | VARCHAR(512) | 否 |  |  |
| link_type | VARCHAR(16) | 否 | internal |  |
| link_url | VARCHAR(512) | 否 |  |  |
| sort | INTEGER | 否 | 0 |  |
| enabled | BOOLEAN | 否 | True |  |
| start_at | TIMESTAMPTZ | 是 |  |  |
| end_at | TIMESTAMPTZ | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9804360> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9804540> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b98045e0> |  |

## cms_page_versions

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| page_id | UUID | 否 |  | 索引 |
| version | INTEGER | 否 |  |  |
| snapshot | JSONB | 否 |  |  |
| created_by | UUID | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97cd620> |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b97ce660> | 主键 |

## cms_pages

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| page_key | VARCHAR(64) | 否 |  | 唯一 |
| title | VARCHAR(128) | 否 |  |  |
| status | VARCHAR(16) | 否 | draft |  |
| current_version_id | UUID | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b97cc400> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97cc5e0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97cc680> |  |

## cms_publish_records

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| page_id | UUID | 否 |  | 索引 |
| version_id | UUID | 否 |  | 索引 |
| action | VARCHAR(16) | 否 |  |  |
| operator_id | UUID | 是 |  |  |
| note | VARCHAR(255) | 是 |  |  |
| published_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97ce700> |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b97cf420> | 主键 |

## cms_sections

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| page_id | UUID | 否 |  | → cms_pages.id，索引 |
| section_type | VARCHAR(32) | 否 |  |  |
| sort | INTEGER | 否 | 0 |  |
| enabled | BOOLEAN | 否 | True |  |
| config | JSONB | 否 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b97cd580> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97cd760> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97cd800> |  |

## cooperatives

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| name | VARCHAR(128) | 否 |  | 唯一 |
| region | VARCHAR(64) | 否 |  |  |
| description | TEXT | 是 |  |  |
| contact | VARCHAR(64) | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9ae6980> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9ae6b60> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9ae6c00> |  |

## data_scopes

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| code | VARCHAR(32) | 否 |  | 唯一 |
| name | VARCHAR(64) | 否 |  |  |
| description | VARCHAR(255) | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9970e00> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9970fe0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9971080> |  |

## inventories

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| sku_id | UUID | 否 |  | → product_skus.id，唯一，索引 |
| quantity_total | INTEGER | 否 | 0 |  |
| quantity_reserved | INTEGER | 否 | 0 |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9a19260> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a19440> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a194e0> |  |

## inventory_logs

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| sku_id | UUID | 否 |  | 索引 |
| change_type | VARCHAR(32) | 否 |  |  |
| delta_total | INTEGER | 否 | 0 |  |
| delta_reserved | INTEGER | 否 | 0 |  |
| ref_type | VARCHAR(32) | 是 |  |  |
| ref_id | UUID | 是 |  |  |
| reason | TEXT | 是 |  |  |
| operator_id | UUID | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a1a480> | 索引 |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9a1b740> | 主键 |

## inventory_reservations

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| sku_id | UUID | 否 |  | → product_skus.id，索引 |
| store_order_id | UUID | 否 |  | → store_orders.id，索引 |
| quantity | INTEGER | 否 |  |  |
| status | VARCHAR(16) | 否 | held | 索引 |
| expires_at | TIMESTAMPTZ | 否 |  |  |
| released_at | TIMESTAMPTZ | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9a1a3e0> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a1a5c0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a1a660> |  |

## login_logs

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| user_id | UUID | 是 |  | 索引 |
| email | VARCHAR(255) | 否 |  |  |
| success | BOOLEAN | 否 |  |  |
| message | VARCHAR(255) | 是 |  |  |
| ip | VARCHAR(64) | 是 |  |  |
| user_agent | VARCHAR(255) | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b232e0> | 索引 |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9b23420> | 主键 |

## merchant_settlements

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| store_id | UUID | 否 |  | 索引 |
| period_start | TIMESTAMPTZ | 否 |  |  |
| period_end | TIMESTAMPTZ | 否 |  |  |
| status | VARCHAR(16) | 否 | pending |  |
| orders_total | NUMERIC(12,2) | 否 |  |  |
| commission_total | NUMERIC(12,2) | 否 |  |  |
| payable_total | NUMERIC(12,2) | 否 |  |  |
| generated_by | UUID | 是 |  |  |
| confirmed_at | TIMESTAMPTZ | 是 |  |  |
| paid_at | TIMESTAMPTZ | 是 |  |  |
| note | TEXT | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b99b6ac0> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b99b6ca0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b99b6d40> |  |

## merchant_users

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| merchant_id | UUID | 否 |  | → merchants.id，索引 |
| user_id | UUID | 否 |  | → users.id，索引 |
| role | VARCHAR(16) | 否 | owner |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9a4bf60> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a80180> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a80220> |  |

## merchants

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| status | VARCHAR(32) | 否 | pending_review | 索引 |
| company_name | VARCHAR(128) | 否 |  | 唯一 |
| license_no | VARCHAR(64) | 否 |  |  |
| license_url | VARCHAR(512) | 是 |  |  |
| legal_person | VARCHAR(64) | 否 |  |  |
| contact_phone | VARCHAR(32) | 否 |  |  |
| region | VARCHAR(64) | 是 |  |  |
| initial_store_name | VARCHAR(64) | 是 |  |  |
| reject_reason | VARCHAR(255) | 是 |  |  |
| reviewed_by | UUID | 是 |  |  |
| reviewed_at | TIMESTAMPTZ | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9a4a8e0> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a4aac0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a4ab60> |  |

## notifications

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| user_id | UUID | 否 |  | 索引 |
| type | VARCHAR(32) | 否 |  | 索引 |
| title | VARCHAR(128) | 否 |  |  |
| content | TEXT | 否 |  |  |
| read_at | TIMESTAMPTZ | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9a81080> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a81260> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a81300> |  |

## operation_logs

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| user_id | UUID | 是 |  | 索引 |
| action | VARCHAR(64) | 否 |  | 索引 |
| resource | VARCHAR(64) | 否 |  | 索引 |
| resource_id | VARCHAR(64) | 是 |  |  |
| detail | JSONB | 是 |  |  |
| ip | VARCHAR(64) | 是 |  |  |
| user_agent | VARCHAR(255) | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b21260> | 索引 |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9b22200> | 主键 |

## order_items

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| store_order_id | UUID | 否 |  | → store_orders.id，索引 |
| sku_id | UUID | 否 |  | 索引 |
| product_id | UUID | 否 |  | 索引 |
| title | VARCHAR(128) | 否 |  |  |
| spec | VARCHAR(128) | 否 |  |  |
| image_url | VARCHAR(512) | 是 |  |  |
| unit_price | NUMERIC(12,2) | 否 |  |  |
| quantity | INTEGER | 否 |  |  |
| subtotal | NUMERIC(12,2) | 否 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b98c1940> | 主键 |

## order_status_logs

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| order_id | UUID | 否 |  | 索引 |
| store_order_id | UUID | 是 |  | 索引 |
| from_status | VARCHAR(24) | 是 |  |  |
| to_status | VARCHAR(24) | 否 |  |  |
| action | VARCHAR(32) | 否 |  |  |
| operator_id | UUID | 是 |  |  |
| note | TEXT | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b98c19e0> | 索引 |
| id | UUID | 否 | <function uuid4 at 0x7fd7b98c2ac0> | 主键 |

## orders

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| order_no | VARCHAR(32) | 否 |  | 唯一，索引 |
| user_id | UUID | 否 |  | → users.id，索引 |
| status | VARCHAR(24) | 否 | pending_payment | 索引 |
| receiver_name | VARCHAR(64) | 否 |  |  |
| receiver_phone | VARCHAR(32) | 否 |  |  |
| address | VARCHAR(512) | 否 |  |  |
| items_total | NUMERIC(12,2) | 否 |  |  |
| shipping_fee | NUMERIC(12,2) | 否 |  |  |
| points_deduct | NUMERIC(12,2) | 否 |  |  |
| points_used | INTEGER | 否 | 0 |  |
| pay_amount | NUMERIC(12,2) | 否 |  |  |
| currency | VARCHAR(8) | 否 | CNY |  |
| remark | VARCHAR(255) | 是 |  |  |
| cancel_reason | VARCHAR(255) | 是 |  |  |
| paid_at | TIMESTAMPTZ | 是 |  |  |
| completed_at | TIMESTAMPTZ | 是 |  |  |
| cancelled_at | TIMESTAMPTZ | 是 |  |  |
| idempotency_key | VARCHAR(64) | 是 |  |  |
| idempotency_payload_hash | VARCHAR(64) | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9a82340> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a82520> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a825c0> |  |

## payment_callbacks

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| pay_no | VARCHAR(32) | 否 |  | 索引 |
| provider_trade_no | VARCHAR(64) | 否 |  | 索引 |
| payload | JSONB | 否 |  |  |
| signature | VARCHAR(256) | 是 |  |  |
| status | VARCHAR(16) | 否 |  | 索引 |
| message | TEXT | 是 |  |  |
| received_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b98ed260> |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b98ee0c0> | 主键 |

## payment_orders

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| pay_no | VARCHAR(32) | 否 |  | 唯一，索引 |
| order_id | UUID | 否 |  | → orders.id，索引 |
| amount | NUMERIC(12,2) | 否 |  |  |
| currency | VARCHAR(8) | 否 | CNY |  |
| status | VARCHAR(16) | 否 | pending | 索引 |
| provider | VARCHAR(32) | 否 | mock_sandbox |  |
| trade_no | VARCHAR(64) | 是 |  | 唯一 |
| expires_at | TIMESTAMPTZ | 否 |  |  |
| paid_at | TIMESTAMPTZ | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b98c3c40> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b98c3e20> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b98c3ec0> |  |

## payment_transactions

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| payment_order_id | UUID | 否 |  | 索引 |
| provider_trade_no | VARCHAR(64) | 否 |  | 唯一 |
| amount | NUMERIC(12,2) | 否 |  |  |
| currency | VARCHAR(8) | 否 |  |  |
| status | VARCHAR(16) | 否 |  |  |
| raw | JSONB | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b98c3ce0> |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b98ed1c0> | 主键 |

## permissions

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| code | VARCHAR(64) | 否 |  | 唯一 |
| name | VARCHAR(64) | 否 |  |  |
| resource | VARCHAR(32) | 否 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9949da0> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9949f80> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b994a020> |  |

## platform_ledger

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| entry_type | VARCHAR(16) | 否 |  | 索引 |
| ref_type | VARCHAR(32) | 否 |  |  |
| ref_id | UUID | 否 |  | 索引 |
| store_id | UUID | 是 |  | 索引 |
| order_id | UUID | 是 |  | 索引 |
| amount | NUMERIC(12,2) | 否 |  |  |
| note | TEXT | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b99f00e0> | 索引 |
| id | UUID | 否 | <function uuid4 at 0x7fd7b99f0e00> | 主键 |

## point_accounts

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| user_id | UUID | 否 |  | → users.id，唯一 |
| balance | INTEGER | 否 | 0 |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9918860> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9918a40> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9918ae0> |  |

## point_rule_versions

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| rule_id | UUID | 否 |  | → point_rules.id，索引 |
| version | INTEGER | 否 |  |  |
| config | JSONB | 否 |  |  |
| effective_from | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b991ba60> |  |
| created_by | UUID | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b991bb00> |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b991be20> | 主键 |

## point_rules

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| code | VARCHAR(32) | 否 |  | 唯一 |
| name | VARCHAR(64) | 否 |  |  |
| description | VARCHAR(255) | 是 |  |  |
| current_version_id | UUID | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b991aca0> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b991ae80> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b991af20> |  |

## point_transactions

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| account_id | UUID | 否 |  | 索引 |
| user_id | UUID | 否 |  | 索引 |
| type | VARCHAR(16) | 否 |  | 索引 |
| amount | INTEGER | 否 |  |  |
| balance_after | INTEGER | 否 |  |  |
| source_type | VARCHAR(32) | 是 |  |  |
| source_id | UUID | 是 |  |  |
| idempotency_key | VARCHAR(64) | 是 |  |  |
| rule_version_id | UUID | 是 |  |  |
| note | TEXT | 是 |  |  |
| operator_id | UUID | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9918900> | 索引 |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9919940> | 主键 |

## product_audit_records

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| product_id | UUID | 否 |  | 索引 |
| action | VARCHAR(32) | 否 |  |  |
| reason | VARCHAR(255) | 是 |  |  |
| operator_id | UUID | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b99b4ea0> |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b99b5e40> | 主键 |

## product_green_profiles

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| product_id | UUID | 否 |  | 唯一，索引 |
| origin | VARCHAR(128) | 否 |  |  |
| planting_mode | VARCHAR(128) | 是 |  |  |
| certifications | JSONB | 是 |  |  |
| description | TEXT | 是 |  |  |
| status | VARCHAR(16) | 否 | draft |  |
| reviewed_by | UUID | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b99f1f80> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b99f2160> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b99f2200> |  |

## product_images

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| product_id | UUID | 否 |  | → products.id，索引 |
| url | VARCHAR(512) | 否 |  |  |
| sort | NUMERIC(12,2) | 否 | 0 |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b99b4e00> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b99b4fe0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b99b5080> |  |

## product_skus

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| product_id | UUID | 否 |  | → products.id，索引 |
| spec | VARCHAR(128) | 否 |  |  |
| code | VARCHAR(64) | 是 |  |  |
| price | NUMERIC(12,2) | 否 |  |  |
| is_active | BOOLEAN | 否 | True |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9b879c0> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b87ba0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b87c40> |  |

## products

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| store_id | UUID | 否 |  | → stores.id，索引 |
| category_id | UUID | 是 |  | → categories.id，索引 |
| aid_project_id | UUID | 是 |  | 索引 |
| title | VARCHAR(128) | 否 |  | 索引 |
| subtitle | VARCHAR(255) | 是 |  |  |
| description | TEXT | 是 |  |  |
| status | VARCHAR(32) | 否 | draft | 索引 |
| is_listed | BOOLEAN | 否 | False |  |
| audit_reason | VARCHAR(255) | 是 |  |  |
| audited_by | UUID | 是 |  |  |
| audited_at | TIMESTAMPTZ | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9b85f80> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b86160> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b86200> |  |

## refunds

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| refund_no | VARCHAR(32) | 否 |  | 唯一 |
| order_id | UUID | 否 |  | → orders.id，索引 |
| store_order_id | UUID | 否 |  | 索引 |
| amount | NUMERIC(12,2) | 否 |  |  |
| reason | VARCHAR(255) | 否 |  |  |
| status | VARCHAR(16) | 否 | requested | 索引 |
| requested_by | UUID | 否 |  |  |
| handled_by | UUID | 是 |  |  |
| handled_at | TIMESTAMPTZ | 是 |  |  |
| result_note | TEXT | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b98ef100> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b98ef2e0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b98ef380> |  |

## role_permissions

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| role_id | UUID | 否 |  | → roles.id，索引 |
| permission_id | UUID | 否 |  | → permissions.id，索引 |
| id | UUID | 否 | <function uuid4 at 0x7fd7b994ae80> | 主键 |

## roles

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| code | VARCHAR(64) | 否 |  | 唯一 |
| name | VARCHAR(64) | 否 |  |  |
| kind | VARCHAR(16) | 否 | admin |  |
| is_super | BOOLEAN | 否 | False |  |
| description | VARCHAR(255) | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9948e00> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9948fe0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9949080> |  |

## security_events

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| kind | VARCHAR(64) | 否 |  | 索引 |
| user_id | UUID | 是 |  | 索引 |
| detail | JSONB | 是 |  |  |
| ip | VARCHAR(64) | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b540e0> | 索引 |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9b54400> | 主键 |

## sessions

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| user_id | UUID | 否 |  | → users.id，索引 |
| refresh_token_hash | VARCHAR(64) | 否 |  |  |
| user_agent | VARCHAR(255) | 是 |  |  |
| ip | VARCHAR(64) | 是 |  |  |
| expires_at | TIMESTAMPTZ | 否 |  |  |
| revoked_at | TIMESTAMPTZ | 是 |  |  |
| rotated_from_id | UUID | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9b55260> |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9b55580> | 主键 |

## settlement_items

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| settlement_id | UUID | 否 |  | 索引 |
| store_order_id | UUID | 否 |  | 索引 |
| order_amount | NUMERIC(12,2) | 否 |  |  |
| commission_amount | NUMERIC(12,2) | 否 |  |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b99b7ce0> |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b99f0040> | 主键 |

## shipment_tracks

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| shipment_id | UUID | 否 |  | 索引 |
| status | VARCHAR(32) | 否 |  |  |
| description | TEXT | 是 |  |  |
| occurred_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a48900> |  |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a498a0> |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9a49bc0> | 主键 |

## shipments

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| store_order_id | UUID | 否 |  | → store_orders.id，唯一，索引 |
| carrier | VARCHAR(64) | 否 |  |  |
| tracking_no | VARCHAR(64) | 否 |  | 索引 |
| status | VARCHAR(16) | 否 | shipped |  |
| shipped_by | UUID | 是 |  |  |
| shipped_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a48540> |  |
| delivered_at | TIMESTAMPTZ | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9a48860> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a48a40> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9a48ae0> |  |

## store_members

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| store_id | UUID | 否 |  | → stores.id，索引 |
| user_id | UUID | 否 |  | → users.id，索引 |
| role | VARCHAR(16) | 否 | staff |  |
| invited_by | UUID | 是 |  |  |
| status | VARCHAR(16) | 否 | active |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9973380> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9973560> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9973600> |  |

## store_orders

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| store_order_no | VARCHAR(32) | 否 |  | 唯一 |
| order_id | UUID | 否 |  | → orders.id，索引 |
| store_id | UUID | 否 |  | → stores.id，索引 |
| status | VARCHAR(24) | 否 | pending_payment | 索引 |
| items_total | NUMERIC(12,2) | 否 |  |  |
| shipping_fee | NUMERIC(12,2) | 否 |  |  |
| pay_amount | NUMERIC(12,2) | 否 |  |  |
| refund_amount | NUMERIC(12,2) | 否 | 0 |  |
| shipped_at | TIMESTAMPTZ | 是 |  |  |
| completed_at | TIMESTAMPTZ | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b98c00e0> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b98c02c0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b98c0360> |  |

## stores

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| merchant_id | UUID | 否 |  | → merchants.id，索引 |
| name | VARCHAR(64) | 否 |  | 唯一 |
| logo_url | VARCHAR(512) | 是 |  |  |
| description | VARCHAR(1024) | 是 |  |  |
| region | VARCHAR(64) | 是 |  |  |
| status | VARCHAR(16) | 否 | active | 索引 |
| is_closed_temporarily | BOOLEAN | 否 | False |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9971d00> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9971ee0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9971f80> |  |

## system_settings

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| key | VARCHAR(64) | 否 |  | 唯一 |
| value | JSONB | 否 |  |  |
| description | VARCHAR(255) | 是 |  |  |
| updated_by | UUID | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9ae4f40> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9ae5120> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b9ae51c0> |  |

## user_addresses

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| user_id | UUID | 否 |  | → users.id，索引 |
| receiver | VARCHAR(64) | 否 |  |  |
| phone | VARCHAR(32) | 否 |  |  |
| province | VARCHAR(32) | 否 |  |  |
| city | VARCHAR(32) | 否 |  |  |
| district | VARCHAR(32) | 是 |  |  |
| detail | VARCHAR(255) | 否 |  |  |
| is_default | BOOLEAN | 否 | False |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b97ab100> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97ab2e0> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97ab380> |  |

## user_profiles

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| user_id | UUID | 否 |  | → users.id，唯一，索引 |
| nickname | VARCHAR(64) | 是 |  |  |
| avatar_url | VARCHAR(512) | 是 |  |  |
| gender | VARCHAR(16) | 是 |  |  |
| birthday | DATE | 是 |  |  |
| bio | VARCHAR(255) | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b97a9da0> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97a9f80> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97aa020> |  |

## user_roles

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| user_id | UUID | 否 |  | → users.id，索引 |
| role_id | UUID | 否 |  | → roles.id，索引 |
| granted_by | UUID | 是 |  |  |
| granted_at | TIMESTAMPTZ | 否 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b994bec0> | 主键 |

## users

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| email | VARCHAR(255) | 否 |  | 唯一，索引 |
| phone | VARCHAR(32) | 是 |  | 索引 |
| password_hash | VARCHAR(255) | 否 |  |  |
| is_active | BOOLEAN | 否 | True |  |
| is_email_verified | BOOLEAN | 否 | False |  |
| mfa_enabled | BOOLEAN | 否 | False |  |
| mfa_secret | VARCHAR(64) | 是 |  |  |
| banned_until | TIMESTAMPTZ | 是 |  |  |
| ban_reason | VARCHAR(255) | 是 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b97a89a0> | 主键 |
| created_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97a8b80> |  |
| updated_at | TIMESTAMPTZ | 否 | <function utcnow at 0x7fd7b97a8c20> |  |

## verification_records

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| assessment_id | UUID | 否 |  | 索引 |
| result | VARCHAR(16) | 否 |  |  |
| notes | TEXT | 是 |  |  |
| verifier_id | UUID | 是 |  |  |
| created_at | TIMESTAMPTZ | 否 |  |  |
| id | UUID | 否 | <function uuid4 at 0x7fd7b9a182c0> | 主键 |
