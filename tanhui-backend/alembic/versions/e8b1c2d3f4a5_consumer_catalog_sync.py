"""consumer catalog mirror and product sync logs

Revision ID: e8b1c2d3f4a5
Revises: c3faf3a4b0e6
Create Date: 2026-11-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core import types

revision: str = "e8b1c2d3f4a5"
down_revision: Union[str, None] = "c3faf3a4b0e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consumer_categories",
        sa.Column("parent_id", types.GUID(), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("icon_url", sa.String(length=512), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("synced_at", types.UTCDatetime(), nullable=False),
        sa.Column("id", types.GUID(), nullable=False),
        sa.Column("created_at", types.UTCDatetime(), nullable=False),
        sa.Column("updated_at", types.UTCDatetime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("consumer_categories", schema=None) as batch_op:
        batch_op.create_index("ix_consumer_categories_parent_id", ["parent_id"], unique=False)
        batch_op.create_index("ix_consumer_categories_sort", ["sort"], unique=False)

    op.create_table(
        "consumer_products",
        sa.Column("store_id", types.GUID(), nullable=False),
        sa.Column("category_id", types.GUID(), nullable=True),
        sa.Column("aid_project_id", types.GUID(), nullable=True),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("subtitle", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_listed", sa.Boolean(), nullable=False),
        sa.Column("audit_reason", sa.String(length=255), nullable=True),
        sa.Column("audited_by", types.GUID(), nullable=True),
        sa.Column("audited_at", types.UTCDatetime(), nullable=True),
        sa.Column("sync_version", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=True),
        sa.Column("synced_at", types.UTCDatetime(), nullable=False),
        sa.Column("id", types.GUID(), nullable=False),
        sa.Column("created_at", types.UTCDatetime(), nullable=False),
        sa.Column("updated_at", types.UTCDatetime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("consumer_products", schema=None) as batch_op:
        batch_op.create_index("ix_consumer_products_store_id", ["store_id"], unique=False)
        batch_op.create_index("ix_consumer_products_category_id", ["category_id"], unique=False)
        batch_op.create_index(
            "ix_consumer_products_aid_project_id", ["aid_project_id"], unique=False
        )
        batch_op.create_index("ix_consumer_products_title", ["title"], unique=False)
        batch_op.create_index("ix_consumer_products_status", ["status"], unique=False)
        batch_op.create_index("ix_consumer_products_is_listed", ["is_listed"], unique=False)

    op.create_table(
        "consumer_product_skus",
        sa.Column("product_id", types.GUID(), nullable=False),
        sa.Column("spec", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("price", types.Amount(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("id", types.GUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("consumer_product_skus", schema=None) as batch_op:
        batch_op.create_index(
            "ix_consumer_product_skus_product_id", ["product_id"], unique=False
        )

    op.create_table(
        "consumer_product_images",
        sa.Column("product_id", types.GUID(), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("sort", types.Amount(), nullable=False),
        sa.Column("id", types.GUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("consumer_product_images", schema=None) as batch_op:
        batch_op.create_index(
            "ix_consumer_product_images_product_id", ["product_id"], unique=False
        )

    op.create_table(
        "product_sync_logs",
        sa.Column("product_id", types.GUID(), nullable=False),
        sa.Column("operator_id", types.GUID(), nullable=True),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("target_category_id", types.GUID(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=True),
        sa.Column("target_hash", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", types.UTCDatetime(), nullable=False),
        sa.Column("id", types.GUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("product_sync_logs", schema=None) as batch_op:
        batch_op.create_index("ix_product_sync_logs_product_id", ["product_id"], unique=False)
        batch_op.create_index(
            "ix_product_sync_logs_trigger_type", ["trigger_type"], unique=False
        )
        batch_op.create_index("ix_product_sync_logs_status", ["status"], unique=False)
        batch_op.create_index("ix_product_sync_logs_created_at", ["created_at"], unique=False)
        batch_op.create_index(
            "ix_product_sync_logs_product_created", ["product_id", "created_at"], unique=False
        )


def downgrade() -> None:
    op.drop_table("product_sync_logs")
    op.drop_table("consumer_product_images")
    op.drop_table("consumer_product_skus")
    op.drop_table("consumer_products")
    op.drop_table("consumer_categories")
