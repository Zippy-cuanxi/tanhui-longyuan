# ER 图（自动生成，请勿手改）

> 关系连线由外键推导；金额列均为 NUMERIC(12,2)；主键统一 UUID。

```mermaid
erDiagram
    "aid_projects" {
        cooperative_id UUID FK
        title VARCHAR(128)
        cover_url VARCHAR(512)
        description TEXT
        goal_amount NUMERIC(12,2)
        raised_amount NUMERIC(12,2)
        status VARCHAR(16)
        reviewed_by UUID
        published_at TIMESTAMPTZ
        id UUID PK
    }
    cooperatives ||--o{ aid_projects : has
    "aid_records" {
        project_id UUID
        user_id UUID
        order_id UUID
        amount NUMERIC(12,2)
        kind VARCHAR(16)
        note VARCHAR(255)
        id UUID PK
    }
    "carbon_assessments" {
        product_id UUID
        co2e_per_unit NUMERIC(12, 4)
        unit VARCHAR(16)
        methodology VARCHAR(255)
        verified BOOLEAN
        verifier_id UUID
        id UUID PK
    }
    "cart_items" {
        cart_id UUID FK
        sku_id UUID FK
        quantity INTEGER
        checked BOOLEAN
        id UUID PK
    }
    carts ||--o{ cart_items : has
    product_skus ||--o{ cart_items : has
    "carts" {
        user_id UUID FK
        id UUID PK
    }
    users ||--o{ carts : has
    "categories" {
        parent_id UUID FK
        name VARCHAR(64)
        icon_url VARCHAR(512)
        sort INTEGER
        is_active BOOLEAN
        id UUID PK
    }
    categories ||--o{ categories : has
    "cms_announcements" {
        title VARCHAR(128)
        content TEXT
        status VARCHAR(16)
        published_at TIMESTAMPTZ
        start_at TIMESTAMPTZ
        end_at TIMESTAMPTZ
        id UUID PK
    }
    "cms_banners" {
        title VARCHAR(128)
        image_url VARCHAR(512)
        link_type VARCHAR(16)
        link_url VARCHAR(512)
        sort INTEGER
        enabled BOOLEAN
        start_at TIMESTAMPTZ
        end_at TIMESTAMPTZ
        id UUID PK
    }
    "cms_page_versions" {
        page_id UUID
        version INTEGER
        snapshot JSONB
        created_by UUID
        id UUID PK
    }
    "cms_pages" {
        page_key VARCHAR(64)
        title VARCHAR(128)
        status VARCHAR(16)
        current_version_id UUID
        id UUID PK
    }
    "cms_publish_records" {
        page_id UUID
        version_id UUID
        action VARCHAR(16)
        operator_id UUID
        note VARCHAR(255)
        published_at TIMESTAMPTZ
        id UUID PK
    }
    "cms_sections" {
        page_id UUID FK
        section_type VARCHAR(32)
        sort INTEGER
        enabled BOOLEAN
        config JSONB
        id UUID PK
    }
    cms_pages ||--o{ cms_sections : has
    "cooperatives" {
        name VARCHAR(128)
        region VARCHAR(64)
        description TEXT
        contact VARCHAR(64)
        id UUID PK
    }
    "data_scopes" {
        code VARCHAR(32)
        name VARCHAR(64)
        description VARCHAR(255)
        id UUID PK
    }
    "inventories" {
        sku_id UUID FK
        quantity_total INTEGER
        quantity_reserved INTEGER
        id UUID PK
    }
    product_skus ||--o{ inventories : has
    "inventory_logs" {
        sku_id UUID
        change_type VARCHAR(32)
        delta_total INTEGER
        delta_reserved INTEGER
        ref_type VARCHAR(32)
        ref_id UUID
        reason TEXT
        operator_id UUID
        id UUID PK
    }
    "inventory_reservations" {
        sku_id UUID FK
        store_order_id UUID FK
        quantity INTEGER
        status VARCHAR(16)
        expires_at TIMESTAMPTZ
        released_at TIMESTAMPTZ
        id UUID PK
    }
    product_skus ||--o{ inventory_reservations : has
    store_orders ||--o{ inventory_reservations : has
    "login_logs" {
        user_id UUID
        email VARCHAR(255)
        success BOOLEAN
        message VARCHAR(255)
        ip VARCHAR(64)
        user_agent VARCHAR(255)
        id UUID PK
    }
    "merchant_settlements" {
        store_id UUID
        period_start TIMESTAMPTZ
        period_end TIMESTAMPTZ
        status VARCHAR(16)
        orders_total NUMERIC(12,2)
        commission_total NUMERIC(12,2)
        payable_total NUMERIC(12,2)
        generated_by UUID
        confirmed_at TIMESTAMPTZ
        paid_at TIMESTAMPTZ
        note TEXT
        id UUID PK
    }
    "merchant_users" {
        merchant_id UUID FK
        user_id UUID FK
        role VARCHAR(16)
        id UUID PK
    }
    merchants ||--o{ merchant_users : has
    users ||--o{ merchant_users : has
    "merchants" {
        status VARCHAR(32)
        company_name VARCHAR(128)
        license_no VARCHAR(64)
        license_url VARCHAR(512)
        legal_person VARCHAR(64)
        contact_phone VARCHAR(32)
        region VARCHAR(64)
        initial_store_name VARCHAR(64)
        reject_reason VARCHAR(255)
        reviewed_by UUID
        reviewed_at TIMESTAMPTZ
        id UUID PK
    }
    "notifications" {
        user_id UUID
        type VARCHAR(32)
        title VARCHAR(128)
        content TEXT
        read_at TIMESTAMPTZ
        id UUID PK
    }
    "operation_logs" {
        user_id UUID
        action VARCHAR(64)
        resource VARCHAR(64)
        resource_id VARCHAR(64)
        detail JSONB
        ip VARCHAR(64)
        user_agent VARCHAR(255)
        id UUID PK
    }
    "order_items" {
        store_order_id UUID FK
        sku_id UUID
        product_id UUID
        title VARCHAR(128)
        spec VARCHAR(128)
        image_url VARCHAR(512)
        unit_price NUMERIC(12,2)
        quantity INTEGER
        subtotal NUMERIC(12,2)
        id UUID PK
    }
    store_orders ||--o{ order_items : has
    "order_status_logs" {
        order_id UUID
        store_order_id UUID
        from_status VARCHAR(24)
        to_status VARCHAR(24)
        action VARCHAR(32)
        operator_id UUID
        note TEXT
        id UUID PK
    }
    "orders" {
        order_no VARCHAR(32)
        user_id UUID FK
        status VARCHAR(24)
        receiver_name VARCHAR(64)
        receiver_phone VARCHAR(32)
        address VARCHAR(512)
        items_total NUMERIC(12,2)
        shipping_fee NUMERIC(12,2)
        points_deduct NUMERIC(12,2)
        points_used INTEGER
        pay_amount NUMERIC(12,2)
        currency VARCHAR(8)
        remark VARCHAR(255)
        cancel_reason VARCHAR(255)
        ... 其余字段见字段字典
    }
    users ||--o{ orders : has
    "payment_callbacks" {
        pay_no VARCHAR(32)
        provider_trade_no VARCHAR(64)
        payload JSONB
        signature VARCHAR(256)
        status VARCHAR(16)
        message TEXT
        received_at TIMESTAMPTZ
        id UUID PK
    }
    "payment_orders" {
        pay_no VARCHAR(32)
        order_id UUID FK
        amount NUMERIC(12,2)
        currency VARCHAR(8)
        status VARCHAR(16)
        provider VARCHAR(32)
        trade_no VARCHAR(64)
        expires_at TIMESTAMPTZ
        paid_at TIMESTAMPTZ
        id UUID PK
    }
    orders ||--o{ payment_orders : has
    "payment_transactions" {
        payment_order_id UUID
        provider_trade_no VARCHAR(64)
        amount NUMERIC(12,2)
        currency VARCHAR(8)
        status VARCHAR(16)
        raw JSONB
        id UUID PK
    }
    "permissions" {
        code VARCHAR(64)
        name VARCHAR(64)
        resource VARCHAR(32)
        id UUID PK
    }
    "platform_ledger" {
        entry_type VARCHAR(16)
        ref_type VARCHAR(32)
        ref_id UUID
        store_id UUID
        order_id UUID
        amount NUMERIC(12,2)
        note TEXT
        id UUID PK
    }
    "point_accounts" {
        user_id UUID FK
        balance INTEGER
        id UUID PK
    }
    users ||--o{ point_accounts : has
    "point_rule_versions" {
        rule_id UUID FK
        version INTEGER
        config JSONB
        effective_from TIMESTAMPTZ
        created_by UUID
        id UUID PK
    }
    point_rules ||--o{ point_rule_versions : has
    "point_rules" {
        code VARCHAR(32)
        name VARCHAR(64)
        description VARCHAR(255)
        current_version_id UUID
        id UUID PK
    }
    "point_transactions" {
        account_id UUID
        user_id UUID
        type VARCHAR(16)
        amount INTEGER
        balance_after INTEGER
        source_type VARCHAR(32)
        source_id UUID
        idempotency_key VARCHAR(64)
        rule_version_id UUID
        note TEXT
        operator_id UUID
        id UUID PK
    }
    "product_audit_records" {
        product_id UUID
        action VARCHAR(32)
        reason VARCHAR(255)
        operator_id UUID
        id UUID PK
    }
    "product_green_profiles" {
        product_id UUID
        origin VARCHAR(128)
        planting_mode VARCHAR(128)
        certifications JSONB
        description TEXT
        status VARCHAR(16)
        reviewed_by UUID
        id UUID PK
    }
    "product_images" {
        product_id UUID FK
        url VARCHAR(512)
        sort NUMERIC(12,2)
        id UUID PK
    }
    products ||--o{ product_images : has
    "product_skus" {
        product_id UUID FK
        spec VARCHAR(128)
        code VARCHAR(64)
        price NUMERIC(12,2)
        is_active BOOLEAN
        id UUID PK
    }
    products ||--o{ product_skus : has
    "products" {
        store_id UUID FK
        category_id UUID FK
        aid_project_id UUID
        title VARCHAR(128)
        subtitle VARCHAR(255)
        description TEXT
        status VARCHAR(32)
        is_listed BOOLEAN
        audit_reason VARCHAR(255)
        audited_by UUID
        audited_at TIMESTAMPTZ
        id UUID PK
    }
    stores ||--o{ products : has
    categories ||--o{ products : has
    "refunds" {
        refund_no VARCHAR(32)
        order_id UUID FK
        store_order_id UUID
        amount NUMERIC(12,2)
        reason VARCHAR(255)
        status VARCHAR(16)
        requested_by UUID
        handled_by UUID
        handled_at TIMESTAMPTZ
        result_note TEXT
        id UUID PK
    }
    orders ||--o{ refunds : has
    "role_permissions" {
        role_id UUID FK
        permission_id UUID FK
        id UUID PK
    }
    roles ||--o{ role_permissions : has
    permissions ||--o{ role_permissions : has
    "roles" {
        code VARCHAR(64)
        name VARCHAR(64)
        kind VARCHAR(16)
        is_super BOOLEAN
        description VARCHAR(255)
        id UUID PK
    }
    "security_events" {
        kind VARCHAR(64)
        user_id UUID
        detail JSONB
        ip VARCHAR(64)
        id UUID PK
    }
    "sessions" {
        user_id UUID FK
        refresh_token_hash VARCHAR(64)
        user_agent VARCHAR(255)
        ip VARCHAR(64)
        expires_at TIMESTAMPTZ
        revoked_at TIMESTAMPTZ
        rotated_from_id UUID
        id UUID PK
    }
    users ||--o{ sessions : has
    "settlement_items" {
        settlement_id UUID
        store_order_id UUID
        order_amount NUMERIC(12,2)
        commission_amount NUMERIC(12,2)
        id UUID PK
    }
    "shipment_tracks" {
        shipment_id UUID
        status VARCHAR(32)
        description TEXT
        occurred_at TIMESTAMPTZ
        id UUID PK
    }
    "shipments" {
        store_order_id UUID FK
        carrier VARCHAR(64)
        tracking_no VARCHAR(64)
        status VARCHAR(16)
        shipped_by UUID
        shipped_at TIMESTAMPTZ
        delivered_at TIMESTAMPTZ
        id UUID PK
    }
    store_orders ||--o{ shipments : has
    "store_members" {
        store_id UUID FK
        user_id UUID FK
        role VARCHAR(16)
        invited_by UUID
        status VARCHAR(16)
        id UUID PK
    }
    stores ||--o{ store_members : has
    users ||--o{ store_members : has
    "store_orders" {
        store_order_no VARCHAR(32)
        order_id UUID FK
        store_id UUID FK
        status VARCHAR(24)
        items_total NUMERIC(12,2)
        shipping_fee NUMERIC(12,2)
        pay_amount NUMERIC(12,2)
        refund_amount NUMERIC(12,2)
        shipped_at TIMESTAMPTZ
        completed_at TIMESTAMPTZ
        id UUID PK
    }
    orders ||--o{ store_orders : has
    stores ||--o{ store_orders : has
    "stores" {
        merchant_id UUID FK
        name VARCHAR(64)
        logo_url VARCHAR(512)
        description VARCHAR(1024)
        region VARCHAR(64)
        status VARCHAR(16)
        is_closed_temporarily BOOLEAN
        id UUID PK
    }
    merchants ||--o{ stores : has
    "system_settings" {
        key VARCHAR(64)
        value JSONB
        description VARCHAR(255)
        updated_by UUID
        id UUID PK
    }
    "user_addresses" {
        user_id UUID FK
        receiver VARCHAR(64)
        phone VARCHAR(32)
        province VARCHAR(32)
        city VARCHAR(32)
        district VARCHAR(32)
        detail VARCHAR(255)
        is_default BOOLEAN
        id UUID PK
    }
    users ||--o{ user_addresses : has
    "user_profiles" {
        user_id UUID FK
        nickname VARCHAR(64)
        avatar_url VARCHAR(512)
        gender VARCHAR(16)
        birthday DATE
        bio VARCHAR(255)
        id UUID PK
    }
    users ||--o{ user_profiles : has
    "user_roles" {
        user_id UUID FK
        role_id UUID FK
        granted_by UUID
        granted_at TIMESTAMPTZ
        id UUID PK
    }
    users ||--o{ user_roles : has
    roles ||--o{ user_roles : has
    "users" {
        email VARCHAR(255)
        phone VARCHAR(32)
        password_hash VARCHAR(255)
        is_active BOOLEAN
        is_email_verified BOOLEAN
        mfa_enabled BOOLEAN
        mfa_secret VARCHAR(64)
        banned_until TIMESTAMPTZ
        ban_reason VARCHAR(255)
        id UUID PK
    }
    "verification_records" {
        assessment_id UUID
        result VARCHAR(16)
        notes TEXT
        verifier_id UUID
        id UUID PK
    }
```
