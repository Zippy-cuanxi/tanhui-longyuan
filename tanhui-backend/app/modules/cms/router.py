"""CMS 接口：管理端（/cms/*，需 cms:manage 权限）与客户端（/client/*，公开只读）。"""
import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permissions
from app.core.responses import ApiResponse
from app.modules.cms import service
from app.modules.cms.schemas import (
    AnnouncementIn,
    AnnouncementOut,
    BannerIn,
    BannerOut,
    PageCreateIn,
    PageOut,
    SectionIn,
    SectionOut,
    VersionOut,
)

admin_router = APIRouter(prefix="/cms", tags=["cms-admin"])


@admin_router.get("/pages", response_model=ApiResponse[list[PageOut]], summary="页面列表")
def list_pages(_admin=Depends(require_permissions("cms:manage")), db: Session = Depends(get_db)):
    pages = service.list_pages(db)
    out = []
    for p in pages:
        po = PageOut(
            id=p.id, page_key=p.page_key, title=p.title, status=p.status,
            current_version_id=p.current_version_id, created_at=p.created_at,
        )
        po.sections = [
            SectionOut(
                id=s.id, section_type=s.section_type, sort=s.sort,
                enabled=s.enabled, config=s.config,
            )
            for s in service.sections_of(db, p.id)
        ]
        out.append(po)
    return ApiResponse(data=out)


@admin_router.post("/pages", response_model=ApiResponse[PageOut], summary="创建页面")
def create_page(
    payload: PageCreateIn,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    page = service.create_page(db, payload, admin.id)
    return ApiResponse(data=PageOut(id=page.id, page_key=page.page_key, title=page.title,
                                    status=page.status, current_version_id=None,
                                    created_at=page.created_at, sections=[]))


@admin_router.post(
    "/pages/{page_id}/sections", response_model=ApiResponse[SectionOut], summary="新增区块"
)
def add_section(
    page_id: uuid.UUID,
    payload: SectionIn,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    s = service.replace_section(db, page_id, None, payload)
    return ApiResponse(data=SectionOut(id=s.id, section_type=s.section_type, sort=s.sort,
                                       enabled=s.enabled, config=s.config))


@admin_router.put(
    "/pages/{page_id}/sections/{section_id}", response_model=ApiResponse[SectionOut], summary="更新区块"
)
def update_section(
    page_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: SectionIn,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    s = service.replace_section(db, page_id, section_id, payload)
    return ApiResponse(data=SectionOut(id=s.id, section_type=s.section_type, sort=s.sort,
                                       enabled=s.enabled, config=s.config))


@admin_router.delete(
    "/pages/{page_id}/sections/{section_id}", response_model=ApiResponse[None], summary="删除区块"
)
def delete_section(
    page_id: uuid.UUID,
    section_id: uuid.UUID,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    service.delete_section(db, page_id, section_id)
    return ApiResponse(message="已删除")


@admin_router.post(
    "/pages/{page_id}/preview", response_model=ApiResponse[dict], summary="草稿预览（快照）"
)
def preview_page(
    page_id: uuid.UUID,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    return ApiResponse(data=service.preview(db, page_id))


@admin_router.post(
    "/pages/{page_id}/publish", response_model=ApiResponse[dict], summary="发布（生成不可变版本）"
)
def publish_page(
    page_id: uuid.UUID,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    from app.modules.cms.models import CmsPageVersion

    page = service.publish(db, page_id, admin.id)
    version = db.get(CmsPageVersion, page.current_version_id)
    return ApiResponse(data={
        "id": str(version.id),
        "version": version.version,
        "page_key": page.page_key,
        "status": page.status,
    })


@admin_router.get(
    "/pages/{page_id}/versions", response_model=ApiResponse[list[VersionOut]], summary="版本历史"
)
def list_versions(
    page_id: uuid.UUID,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    vs = service.list_versions(db, page_id)
    return ApiResponse(data=[VersionOut(id=v.id, page_id=v.page_id, version=v.version,
                                        snapshot=v.snapshot, created_by=v.created_by,
                                        created_at=v.created_at) for v in vs])


@admin_router.post(
    "/pages/{page_id}/rollback/{version_id}", response_model=ApiResponse[dict], summary="回滚到指定版本"
)
def rollback_page(
    page_id: uuid.UUID,
    version_id: uuid.UUID,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    from app.modules.cms.models import CmsPageVersion

    page = service.rollback(db, page_id, version_id, admin.id)
    version = db.get(CmsPageVersion, page.current_version_id)
    return ApiResponse(data={
        "id": str(version.id),
        "version": version.version,
        "rolled_back_to": str(version_id),
        "page_key": page.page_key,
        "status": page.status,
    })


# ---------------- 公告 / Banner ----------------
@admin_router.post("/announcements", response_model=ApiResponse[AnnouncementOut], summary="创建公告（草稿）")
def create_announcement(
    payload: AnnouncementIn,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    a = service.create_announcement(db, payload)
    return ApiResponse(data=AnnouncementOut(id=a.id, title=a.title, content=a.content,
                                            status=a.status, published_at=None,
                                            created_at=a.created_at))


@admin_router.post("/announcements/{ann_id}/publish", response_model=ApiResponse[AnnouncementOut], summary="发布公告")
def publish_announcement(
    ann_id: uuid.UUID,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    a = service.publish_announcement(db, ann_id)
    return ApiResponse(data=AnnouncementOut(id=a.id, title=a.title, content=a.content,
                                            status=a.status, published_at=a.published_at,
                                            created_at=a.created_at))


@admin_router.post("/announcements/{ann_id}/offline", response_model=ApiResponse[AnnouncementOut], summary="下线公告")
def offline_announcement(
    ann_id: uuid.UUID,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    a = service.offline_announcement(db, ann_id)
    return ApiResponse(data=AnnouncementOut(id=a.id, title=a.title, content=a.content,
                                            status=a.status, published_at=a.published_at,
                                            created_at=a.created_at))


@admin_router.post("/banners", response_model=ApiResponse[BannerOut], summary="新增 Banner")
def create_banner(
    payload: BannerIn,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    b = service.upsert_banner(db, None, payload)
    return ApiResponse(data=BannerOut(**{**payload.model_dump(), "id": b.id}))


@admin_router.put("/banners/{banner_id}", response_model=ApiResponse[BannerOut], summary="更新 Banner")
def update_banner(
    banner_id: uuid.UUID,
    payload: BannerIn,
    admin=Depends(require_permissions("cms:manage")),
    db: Session = Depends(get_db),
):
    b = service.upsert_banner(db, banner_id, payload)
    return ApiResponse(data=BannerOut(**{**payload.model_dump(), "id": b.id}))


# ==================== 客户端（公开只读）====================
client_router = APIRouter(prefix="/client", tags=["cms-client"])


@client_router.get("/config/{page_key}", summary="读取已发布页面配置（ETag 缓存）")
def client_config(page_key: str, response: Response, db: Session = Depends(get_db)):
    config, etag = service.client_config(db, page_key)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "no-cache"
    return config


@client_router.get("/notices", summary="公告列表（已发布）")
def client_notices(db: Session = Depends(get_db)):
    items = service.client_notices(db)
    return [
        {"id": str(a.id), "title": a.title, "content": a.content,
         "published_at": a.published_at}
        for a in items
    ]


@client_router.get("/banners", summary="Banner 列表（生效中）")
def client_banners(db: Session = Depends(get_db)):
    items = service.client_banners(db)
    return [
        {"id": str(b.id), "title": b.title, "image_url": b.image_url,
         "link_type": b.link_type, "link_url": b.link_url}
        for b in items
    ]
