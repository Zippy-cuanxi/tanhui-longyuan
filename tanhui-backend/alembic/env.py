"""Alembic 迁移环境：读取应用配置，自定义类型渲染。"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 导入全部模型（注册到 Base.metadata）
import app.modules.models_registry  # noqa: F401
from app.core.base import Base
from app.core.config import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """自定义类型（GUID/JSONBType/UTCDatetime/Amount）渲染为可导入的构造。"""
    if type_ == "type":
        mod = getattr(obj, "__module__", "")
        if mod == "app.core.types":
            autogen_context.imports.add("from app.core import types")
            return f"types.{obj.__class__.__name__}()"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=render_item,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
