"""助农服务 + 接口：消费者浏览、管理员维护与发布（内容为仿真数据）。"""
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Mapped, Session

from app.core.database import get_db
from app.core.deps import get_current_user, page_params, require_permissions
from app.core.errors import AppError
from app.core.responses import ApiResponse, MoneyOut, PageOut, paginate
from app.modules.aid.models import AidDonation, AidProject, Cooperative
from app.modules.audit import service as audit_service
from app.modules.points import service as points_service
from app.modules.users.models import User
from app.core.base import utcnow

# ---------------- Schema ----------------


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cooperative_id: uuid.UUID
    title: str
    cover_url: str | None = None
    description: str | None = None
    goal_amount: MoneyOut | None = None
    raised_amount: MoneyOut
    status: str
    published_at: datetime | None = None


class ProjectIn(BaseModel):
    cooperative_id: uuid.UUID
    title: str = Field(..., max_length=128)
    cover_url: str | None = Field(None, max_length=512)
    description: str | None = Field(None, max_length=5000)
    goal_amount: str | None = None


class ReviewIn(BaseModel):
    action: str = Field(..., pattern="^(publish|offline)")


class DonationIn(BaseModel):
    amount: str = Field(..., max_length=20)
    display_mode: str = Field("anonymous", pattern="^(anonymous|named)$")
    display_name: str | None = Field(None, max_length=64)


class DonationOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_title: str | None = None
    amount: MoneyOut
    points_earned: int
    display_mode: str
    display_name: str | None = None
    created_at: datetime
    balance: int | None = None


class ProjectDonationOut(BaseModel):
    id: uuid.UUID
    donor: str
    display_mode: str
    amount: MoneyOut
    created_at: datetime


# ---------------- 消费者 ----------------
consumer_router = APIRouter(prefix="/aid", tags=["aid"])


@consumer_router.get("/projects", response_model=ApiResponse[PageOut[ProjectOut]], summary="助农项目列表（已发布）")
def list_projects(
    page_size_pair: tuple[int, int] = Depends(page_params), db: Session = Depends(get_db)
):
    stmt = select(AidProject).where(AidProject.status == "published").order_by(AidProject.published_at.desc())
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(data=PageOut(items=[ProjectOut.model_validate(i) for i in items], pagination=pagination))


@consumer_router.get("/projects/{project_id}", response_model=ApiResponse[ProjectOut], summary="助农项目详情")
def project_detail(project_id: uuid.UUID, db: Session = Depends(get_db)):
    p = db.get(AidProject, project_id)
    if p is None or p.status != "published":
        raise AppError("NOT_FOUND", "项目不存在或未发布")
    return ApiResponse(data=ProjectOut.model_validate(p))


@consumer_router.post(
    "/projects/{project_id}/donations",
    response_model=ApiResponse[DonationOut],
    summary="资助助农项目（仿真支付，按 1 元 = 3 积分发放绿色积分）",
)
def create_donation(
    project_id: uuid.UUID,
    payload: DonationIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.get(AidProject, project_id)
    if project is None or project.status != "published":
        raise AppError("NOT_FOUND", "项目不存在或未发布")
    try:
        amount = Decimal(payload.amount).quantize(Decimal("0.01"))
    except Exception:
        raise AppError("VALIDATION_ERROR", "请输入有效的资助金额")
    if not amount.is_finite() or amount <= 0:
        raise AppError("VALIDATION_ERROR", "请输入有效的资助金额")

    display_name = None
    if payload.display_mode == "named":
        display_name = (payload.display_name or "").strip() or user.email.split("@")[0]

    donation = AidDonation(
        user_id=user.id,
        project_id=project.id,
        amount=amount,
        display_mode=payload.display_mode,
        display_name=display_name,
        points_earned=0,
    )
    db.add(donation)
    db.flush()
    transaction = points_service.award_for_donation(db, user.id, donation.id, amount)
    donation.points_earned = transaction.amount if transaction else 0
    project.raised_amount = Decimal(str(project.raised_amount or 0)) + amount
    db.flush()
    balance = points_service.get_balance(db, user.id)
    return ApiResponse(
        data=DonationOut(
            id=donation.id,
            project_id=project.id,
            project_title=project.title,
            amount=donation.amount,
            points_earned=donation.points_earned,
            display_mode=donation.display_mode,
            display_name=donation.display_name,
            created_at=donation.created_at,
            balance=balance,
        )
    )


@consumer_router.get(
    "/donations/me",
    response_model=ApiResponse[list[DonationOut]],
    summary="我的助农资助记录",
)
def my_donations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = db.execute(
        select(AidDonation, AidProject.title)
        .join(AidProject, AidDonation.project_id == AidProject.id)
        .where(AidDonation.user_id == user.id)
        .order_by(AidDonation.created_at.desc())
        .limit(200)
    ).all()
    return ApiResponse(
        data=[
            DonationOut(
                id=donation.id,
                project_id=donation.project_id,
                project_title=title,
                amount=donation.amount,
                points_earned=donation.points_earned,
                display_mode=donation.display_mode,
                display_name=donation.display_name,
                created_at=donation.created_at,
            )
            for donation, title in rows
        ]
    )


@consumer_router.get(
    "/projects/{project_id}/donations",
    response_model=ApiResponse[list[ProjectDonationOut]],
    summary="项目资助名单（匿名展示）",
)
def project_donations(project_id: uuid.UUID, db: Session = Depends(get_db)):
    project = db.get(AidProject, project_id)
    if project is None or project.status != "published":
        raise AppError("NOT_FOUND", "项目不存在或未发布")
    donations = list(
        db.execute(
            select(AidDonation)
            .where(AidDonation.project_id == project_id)
            .order_by(AidDonation.created_at.desc())
            .limit(50)
        ).scalars()
    )
    return ApiResponse(
        data=[
            ProjectDonationOut(
                id=donation.id,
                donor="匿名爱心人士"
                if donation.display_mode == "anonymous"
                else (donation.display_name or "爱心用户"),
                display_mode=donation.display_mode,
                amount=donation.amount,
                created_at=donation.created_at,
            )
            for donation in donations
        ]
    )


# ---------------- 管理端 ----------------
admin_router = APIRouter(prefix="/admin/aid", tags=["admin-aid"])


@admin_router.get("/projects", response_model=ApiResponse[PageOut[ProjectOut]], summary="全部项目（含草稿）")
def admin_list(
    status: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("aid:manage")),
    db: Session = Depends(get_db),
):
    stmt = select(AidProject).order_by(AidProject.created_at.desc())
    if status:
        stmt = stmt.where(AidProject.status == status)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(data=PageOut(items=[ProjectOut.model_validate(i) for i in items], pagination=pagination))


@admin_router.post("/projects", response_model=ApiResponse[ProjectOut], summary="创建项目（草稿）")
def create_project(
    payload: ProjectIn,
    admin=Depends(require_permissions("aid:manage")),
    db: Session = Depends(get_db),
):
    if db.get(Cooperative, payload.cooperative_id) is None:
        raise AppError("NOT_FOUND", "合作社不存在")
    from decimal import Decimal

    p = AidProject(
        cooperative_id=payload.cooperative_id,
        title=payload.title,
        cover_url=payload.cover_url,
        description=payload.description,
        goal_amount=Decimal(payload.goal_amount) if payload.goal_amount else None,
        status="draft",
    )
    db.add(p)
    db.flush()
    return ApiResponse(data=ProjectOut.model_validate(p))


@admin_router.post(
    "/projects/{project_id}/review", response_model=ApiResponse[ProjectOut], summary="发布/下线项目"
)
def review_project(
    project_id: uuid.UUID,
    payload: ReviewIn,
    admin=Depends(require_permissions("aid:manage")),
    db: Session = Depends(get_db),
):
    p = db.get(AidProject, project_id)
    if p is None:
        raise AppError("NOT_FOUND", "项目不存在")
    if payload.action == "publish":
        if p.status not in ("draft", "offline"):
            raise AppError("CONFLICT", "当前状态不可发布")
        p.status = "published"
        p.published_at = utcnow()
    else:
        if p.status != "published":
            raise AppError("CONFLICT", "仅已发布项目可下线")
        p.status = "offline"
    p.reviewed_by = admin.id
    db.flush()
    audit_service.log_operation(
        db, operator_id=admin.id, action=f"aid.{payload.action}",
        resource="aid_project", resource_id=str(project_id),
    )
    return ApiResponse(data=ProjectOut.model_validate(p))


@admin_router.post("/cooperatives", response_model=ApiResponse[dict], summary="创建合作社")
def create_cooperative(
    name: str = Query(..., max_length=128),
    region: str = Query(..., max_length=64),
    description: str | None = Query(None),
    _admin=Depends(require_permissions("aid:manage")),
    db: Session = Depends(get_db),
):
    c = Cooperative(name=name, region=region, description=description)
    db.add(c)
    db.flush()
    return ApiResponse(data={"id": str(c.id), "name": c.name, "region": c.region})
