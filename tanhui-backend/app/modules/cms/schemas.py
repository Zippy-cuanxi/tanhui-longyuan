"""CMS Schema：组件白名单与配置校验。

白名单组件（可按业务扩展，扩展时同步更新前端渲染组件库）：
- banner          轮播图（图片 + 站内路由/HTTPS 外链）
- product_grid    商品宫格（商品 ID 列表，服务端发布时校验存在性）
- aid_project     助农项目卡片
- points_panel    绿豆积分面板（纯展示配置）
- rich_text       富文本（仅纯文本，禁止脚本）
- navigation      导航配置（图标 + 路由）
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _validate_link(link_type: str, link_url: str) -> str:
    """跳转目标安全校验：站内路由必须以 / 开头；外链必须 https。"""
    if link_type == "internal":
        if not link_url.startswith("/") or link_url.startswith("//"):
            raise ValueError("站内路由必须以单个 / 开头")
    else:
        if not link_url.startswith("https://"):
            raise ValueError("外链必须为 https")
    return link_url


class BannerConfig(BaseModel):
    title: str = Field(..., max_length=128)
    image_url: str = Field(..., max_length=512)
    link_type: Literal["internal", "external"] = "internal"
    link_url: str = Field(..., max_length=512)

    @field_validator("link_url")
    @classmethod
    def _link(cls, v, info):
        lt = info.data.get("link_type", "internal")
        return _validate_link(lt, v)


class ProductGridConfig(BaseModel):
    title: str = Field(..., max_length=128)
    product_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=50)


class AidProjectConfig(BaseModel):
    title: str = Field(..., max_length=128)
    project_id: uuid.UUID


class PointsPanelConfig(BaseModel):
    title: str = Field(..., max_length=128)
    description: str | None = Field(None, max_length=255)


class RichTextConfig(BaseModel):
    title: str = Field(..., max_length=128)
    text: str = Field(..., max_length=5000)

    @field_validator("text")
    @classmethod
    def no_script(cls, v: str) -> str:
        low = v.lower()
        if "<script" in low or "javascript:" in low or "onerror=" in low:
            raise ValueError("文本包含不允许的脚本内容")
        return v


class NavigationConfig(BaseModel):
    title: str = Field(..., max_length=64)
    icon_url: str | None = Field(None, max_length=512)
    link_type: Literal["internal", "external"] = "internal"
    link_url: str = Field("/", max_length=512)

    @field_validator("link_url")
    @classmethod
    def _link(cls, v, info):
        lt = info.data.get("link_type", "internal")
        return _validate_link(lt, v)


# 组件类型 → 配置模型 映射（新增组件在此登记）
SECTION_TYPES: dict[str, type[BaseModel]] = {
    "banner": BannerConfig,
    "product_grid": ProductGridConfig,
    "aid_project": AidProjectConfig,
    "points_panel": PointsPanelConfig,
    "rich_text": RichTextConfig,
    "navigation": NavigationConfig,
}


class SectionIn(BaseModel):
    section_type: str
    sort: int = 0
    enabled: bool = True
    config: dict

    def validate_config(self) -> dict:
        model_cls = SECTION_TYPES.get(self.section_type)
        if model_cls is None:
            from app.core.errors import AppError

            raise AppError(
                "CMS_COMPONENT_UNKNOWN",
                f"未知的组件类型: {self.section_type}（白名单: {', '.join(SECTION_TYPES)}）",
            )
        try:
            return model_cls(**self.config).model_dump(mode="json")
        except Exception as e:  # pydantic ValidationError → 统一错误码
            from app.core.errors import AppError

            raise AppError(
                "VALIDATION_ERROR",
                f"组件配置不合法（{self.section_type}）: {e}",
            ) from e


class PageCreateIn(BaseModel):
    page_key: str = Field(..., max_length=64, pattern=r"^[a-z0-9_]+$")
    title: str = Field(..., max_length=128)


class SectionOut(BaseModel):
    id: uuid.UUID
    section_type: str
    sort: int
    enabled: bool
    config: dict


class PageOut(BaseModel):
    id: uuid.UUID
    page_key: str
    title: str
    status: str
    current_version_id: uuid.UUID | None = None
    created_at: datetime
    sections: list[SectionOut] = []


class VersionOut(BaseModel):
    id: uuid.UUID
    page_id: uuid.UUID
    version: int
    snapshot: dict
    created_by: uuid.UUID | None = None
    created_at: datetime


class AnnouncementIn(BaseModel):
    title: str = Field(..., max_length=128)
    content: str = Field(..., max_length=5000)


class AnnouncementOut(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    status: str
    published_at: datetime | None = None
    created_at: datetime


class BannerIn(BaseModel):
    title: str = Field(..., max_length=128)
    image_url: str = Field(..., max_length=512)
    link_type: Literal["internal", "external"] = "internal"
    link_url: str = Field(..., max_length=512)
    sort: int = 0
    enabled: bool = True

    @field_validator("link_url")
    @classmethod
    def _link(cls, v, info):
        lt = info.data.get("link_type", "internal")
        return _validate_link(lt, v)


class BannerOut(BannerIn):
    id: uuid.UUID
