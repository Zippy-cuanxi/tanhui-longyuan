"""CMS 域模型：cms_pages / cms_sections / cms_page_versions / cms_publish_records /
cms_banners / cms_announcements。

安全设计：
- 页面快照按版本不可变（cms_page_versions.snapshot 为发布时整体快照）；
- 组件类型白名单 + Pydantic 配置校验（见 schemas.py），未知组件：
  管理端保存时直接拒绝；客户端读取时安全降级跳过；
- 富文本仅存纯文本，前端按纯文本渲染，不执行任何 HTML/JS。
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.core.types import GUID, JSONBType, UTCDatetime


class CmsPage(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "cms_pages"

    page_key: Mapped[str] = mapped_column(String(64), unique=True)  # home/navigation/...
    title: Mapped[str] = mapped_column(String(128))
    # draft / reviewing / published
    status: Mapped[str] = mapped_column(String(16), default="draft")
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(GUID())


class CmsSection(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "cms_sections"

    page_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("cms_pages.id"), index=True)
    section_type: Mapped[str] = mapped_column(String(32))  # 白名单见 schemas.py
    sort: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSONBType())


class CmsPageVersion(UUIDPKMixin, Base):
    __tablename__ = "cms_page_versions"
    __table_args__ = (UniqueConstraint("page_id", "version", name="uq_page_version"),)

    page_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSONBType())  # 不可变快照
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID())
    created_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)


class CmsPublishRecord(UUIDPKMixin, Base):
    __tablename__ = "cms_publish_records"

    page_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    version_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True)
    action: Mapped[str] = mapped_column(String(16))  # publish / rollback
    operator_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    note: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime] = mapped_column(UTCDatetime(), default=utcnow)


class CmsBanner(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "cms_banners"

    title: Mapped[str] = mapped_column(String(128))
    image_url: Mapped[str] = mapped_column(String(512))
    # internal（站内路由，以 "/" 开头）/ external（https 外链）
    link_type: Mapped[str] = mapped_column(String(16), default="internal")
    link_url: Mapped[str] = mapped_column(String(512))
    sort: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    start_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    end_at: Mapped[datetime | None] = mapped_column(UTCDatetime())


class CmsAnnouncement(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "cms_announcements"

    title: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text)  # 纯文本，前端不做 HTML 渲染
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft/published/offline
    published_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    start_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
    end_at: Mapped[datetime | None] = mapped_column(UTCDatetime())
