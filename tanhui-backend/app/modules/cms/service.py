"""CMS 服务：页面/区块管理、预览、发布（快照版本）、回滚、公告、Banner。"""
import uuid

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.base import utcnow
from app.core.errors import AppError
from app.modules.audit import service as audit_service
from app.modules.cms.models import (
    CmsAnnouncement,
    CmsBanner,
    CmsPage,
    CmsPageVersion,
    CmsPublishRecord,
    CmsSection,
)
from app.modules.cms.schemas import SECTION_TYPES, AnnouncementIn, BannerIn, PageCreateIn, SectionIn


def create_page(db: Session, payload: PageCreateIn, operator_id: uuid.UUID) -> CmsPage:
    dup = db.execute(
        select(CmsPage).where(CmsPage.page_key == payload.page_key)
    ).scalar_one_or_none()
    if dup is not None:
        raise AppError("CONFLICT", "page_key 已存在")
    page = CmsPage(page_key=payload.page_key, title=payload.title, status="draft")
    db.add(page)
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action="cms.create_page",
        resource="cms_page", resource_id=str(page.id), request=None,
    )
    return page


def get_page(db: Session, page_id: uuid.UUID) -> CmsPage:
    page = db.get(CmsPage, page_id)
    if page is None:
        raise AppError("NOT_FOUND", "页面不存在")
    return page


def list_pages(db: Session) -> list[CmsPage]:
    return list(db.execute(select(CmsPage).order_by(CmsPage.created_at.desc())).scalars())


def sections_of(db: Session, page_id: uuid.UUID) -> list[CmsSection]:
    return list(
        db.execute(
            select(CmsSection)
            .where(CmsSection.page_id == page_id)
            .order_by(CmsSection.sort, CmsSection.created_at)
        ).scalars()
    )


def replace_section(
    db: Session, page_id: uuid.UUID, section_id: uuid.UUID | None, payload: SectionIn
) -> CmsSection:
    """新增或更新区块（保存前强校验白名单配置）。"""
    config = payload.validate_config()
    get_page(db, page_id)
    if section_id is None:
        section = CmsSection(
            page_id=page_id,
            section_type=payload.section_type,
            sort=payload.sort,
            enabled=payload.enabled,
            config=config,
        )
        db.add(section)
    else:
        section = db.get(CmsSection, section_id)
        if section is None or section.page_id != page_id:
            raise AppError("NOT_FOUND", "区块不存在")
        section.section_type = payload.section_type
        section.sort = payload.sort
        section.enabled = payload.enabled
        section.config = config
    db.flush()
    return section


def delete_section(db: Session, page_id: uuid.UUID, section_id: uuid.UUID) -> None:
    section = db.get(CmsSection, section_id)
    if section is None or section.page_id != page_id:
        raise AppError("NOT_FOUND", "区块不存在")
    db.delete(section)
    db.flush()


def _snapshot(db: Session, page: CmsPage) -> dict:
    return {
        "page_key": page.page_key,
        "title": page.title,
        "sections": [
            {
                "section_type": s.section_type,
                "sort": s.sort,
                "enabled": s.enabled,
                "config": s.config,
            }
            for s in sections_of(db, page.id)
        ],
        "snapshot_at": utcnow().isoformat(),
    }


def preview(db: Session, page_id: uuid.UUID) -> dict:
    """草稿预览（不鉴权变化，仅管理员可调用）：返回当前草稿快照。"""
    page = get_page(db, page_id)
    return _snapshot(db, page)


def publish(db: Session, page_id: uuid.UUID, operator_id: uuid.UUID) -> CmsPage:
    """发布：当前区块整体快照为不可变新版本，页面状态 → published。"""
    page = get_page(db, page_id)
    last = db.execute(
        select(CmsPageVersion.version)
        .where(CmsPageVersion.page_id == page.id)
        .order_by(CmsPageVersion.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    version_no = (last or 0) + 1
    version = CmsPageVersion(
        page_id=page.id, version=version_no, snapshot=_snapshot(db, page), created_by=operator_id
    )
    db.add(version)
    db.flush()
    page.status = "published"
    page.current_version_id = version.id
    db.add(
        CmsPublishRecord(
            page_id=page.id, version_id=version.id, action="publish", operator_id=operator_id
        )
    )
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action="cms.publish",
        resource="cms_page", resource_id=str(page.id),
        detail={"version": version_no},
    )
    return page


def rollback(
    db: Session, page_id: uuid.UUID, version_id: uuid.UUID, operator_id: uuid.UUID
) -> CmsPage:
    """回滚：目标版本快照原样重建为新版本（版本号继续递增，历史不被篡改）。"""
    page = get_page(db, page_id)
    target = db.get(CmsPageVersion, version_id)
    if target is None or target.page_id != page.id:
        raise AppError("NOT_FOUND", "目标版本不存在")
    last = db.execute(
        select(CmsPageVersion.version)
        .where(CmsPageVersion.page_id == page.id)
        .order_by(CmsPageVersion.version.desc())
        .limit(1)
    ).scalar_one()
    version = CmsPageVersion(
        page_id=page.id,
        version=last + 1,
        snapshot=target.snapshot,
        created_by=operator_id,
    )
    db.add(version)
    db.flush()
    page.current_version_id = version.id
    page.status = "published"
    db.add(
        CmsPublishRecord(
            page_id=page.id,
            version_id=version.id,
            action="rollback",
            operator_id=operator_id,
            note=f"回滚至版本 {target.version}",
        )
    )
    db.flush()
    audit_service.log_operation(
        db, operator_id=operator_id, action="cms.rollback",
        resource="cms_page", resource_id=str(page.id),
        detail={"rollback_to": target.version},
    )
    return page


def list_versions(db: Session, page_id: uuid.UUID) -> list[CmsPageVersion]:
    return list(
        db.execute(
            select(CmsPageVersion)
            .where(CmsPageVersion.page_id == page_id)
            .order_by(CmsPageVersion.version.desc())
        ).scalars()
    )


def client_config(db: Session, page_key: str) -> tuple[dict, str]:
    """客户端读取已发布页面（未知组件安全降级跳过）。返回 (config, etag)。"""
    page = db.execute(
        select(CmsPage).where(CmsPage.page_key == page_key)
    ).scalar_one_or_none()
    if page is None or page.status != "published" or page.current_version_id is None:
        raise AppError("CMS_PAGE_NOT_PUBLISHED")
    version = db.get(CmsPageVersion, page.current_version_id)
    snapshot = dict(version.snapshot)
    # 安全降级：跳过白名单之外的组件（数据异常时也不向前端下发未知内容）
    sections = [
        s for s in snapshot.get("sections", []) if s.get("section_type") in SECTION_TYPES
    ]
    etag = f'"v{version.version}"'
    config = {
        "page": {
            "page_key": page.page_key,
            "title": page.title,
            "version": version.version,
        },
        "sections": sections,
    }
    return config, etag


# ---------------- 公告 ----------------
def create_announcement(db: Session, payload: AnnouncementIn) -> CmsAnnouncement:
    a = CmsAnnouncement(title=payload.title, content=payload.content, status="draft")
    db.add(a)
    db.flush()
    return a


def publish_announcement(db: Session, ann_id: uuid.UUID) -> CmsAnnouncement:
    a = db.get(CmsAnnouncement, ann_id)
    if a is None:
        raise AppError("NOT_FOUND", "公告不存在")
    a.status = "published"
    a.published_at = utcnow()
    db.flush()
    return a


def offline_announcement(db: Session, ann_id: uuid.UUID) -> CmsAnnouncement:
    a = db.get(CmsAnnouncement, ann_id)
    if a is None:
        raise AppError("NOT_FOUND", "公告不存在")
    a.status = "offline"
    db.flush()
    return a


def client_notices(db: Session) -> list[CmsAnnouncement]:
    now = utcnow()
    return list(
        db.execute(
            select(CmsAnnouncement)
            .where(CmsAnnouncement.status == "published")
            .order_by(CmsAnnouncement.published_at.desc())
            .limit(20)
        ).scalars()
    )


# ---------------- Banner ----------------
def upsert_banner(db: Session, banner_id: uuid.UUID | None, payload: BannerIn) -> CmsBanner:
    if banner_id is None:
        b = CmsBanner(**payload.model_dump())
        db.add(b)
    else:
        b = db.get(CmsBanner, banner_id)
        if b is None:
            raise AppError("NOT_FOUND", "Banner 不存在")
        for k, v in payload.model_dump().items():
            setattr(b, k, v)
    db.flush()
    return b


def client_banners(db: Session) -> list[CmsBanner]:
    now = utcnow()
    stmt = (
        select(CmsBanner)
        .where(CmsBanner.enabled == True)  # noqa: E712
        .order_by(CmsBanner.sort)
    )
    return [
        b
        for b in db.execute(stmt).scalars()
        if (b.start_at is None or b.start_at <= now) and (b.end_at is None or b.end_at >= now)
    ]
