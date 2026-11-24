"""绿色资料服务 + 接口：商家提交、管理员审核与碳核验、消费者查询（带核验状态）。"""
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.base import utcnow
from app.core.database import get_db
from app.core.deps import get_current_user, page_params, require_permissions, resolve_store_ctx
from app.core.errors import AppError
from app.core.responses import ApiResponse, PageOut, paginate
from app.modules.audit import service as audit_service
from app.modules.green.models import CarbonAssessment, ProductGreenProfile, VerificationRecord
from app.modules.users.models import User


# ---------------- Schema ----------------
class GreenProfileIn(BaseModel):
    product_id: uuid.UUID
    origin: str = Field(..., max_length=128)
    planting_mode: str | None = Field(None, max_length=128)
    certifications: list[dict] | None = None
    description: str | None = Field(None, max_length=5000)
    # 碳评估（可选提交；未核验数据仅作参考）
    co2e_per_unit: str | None = Field(None, description="kg CO2e/件（估算值）")
    methodology: str | None = Field(None, max_length=255)


class GreenProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    origin: str
    planting_mode: str | None = None
    certifications: list | None = None
    description: str | None = None
    status: str


class AssessmentOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    co2e_per_unit: Decimal
    unit: str
    methodology: str | None = None
    verified: bool  # 【未核验标记】前端必须展示核验状态
    created_at: datetime


class ReviewIn(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)")
    reason: str | None = None


# ---------------- 消费者 ----------------
consumer_router = APIRouter(prefix="/green", tags=["green"])


@consumer_router.get(
    "/products/{product_id}", response_model=ApiResponse[dict], summary="商品绿色资料与碳评估（含核验状态）"
)
def green_detail(product_id: uuid.UUID, db: Session = Depends(get_db)):
    profile = db.execute(
        select(ProductGreenProfile).where(
            ProductGreenProfile.product_id == product_id,
            ProductGreenProfile.status == "approved",
        )
    ).scalar_one_or_none()
    if profile is None:
        raise AppError("NOT_FOUND", "暂无绿色资料")
    assessment = db.execute(
        select(CarbonAssessment)
        .where(CarbonAssessment.product_id == product_id)
        .order_by(CarbonAssessment.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return ApiResponse(
        data={
            "profile": GreenProfileOut.model_validate(profile).model_dump(),
            "carbon_assessment": (
                {
                    "co2e_per_unit": str(assessment.co2e_per_unit),
                    "unit": assessment.unit,
                    "methodology": assessment.methodology,
                    "verified": assessment.verified,  # 未核验数据必须带标记
                    "assessed_at": assessment.created_at,
                }
                if assessment
                else None
            ),
        }
    )


# ---------------- 商家 ----------------
merchant_router = APIRouter(prefix="/merchant/green", tags=["merchant-green"])


@merchant_router.post(
    "/profiles", response_model=ApiResponse[GreenProfileOut], summary="提交/更新绿色资料（进入审核）"
)
def submit_profile(
    payload: GreenProfileIn,
    store_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.modules.catalog.models import Product

    ctx = resolve_store_ctx(db, user, store_id, "green:submit")
    product = db.get(Product, payload.product_id)
    if product is None or product.store_id != ctx.store_id:
        raise AppError("NOT_FOUND", "商品不存在")
    profile = db.execute(
        select(ProductGreenProfile).where(ProductGreenProfile.product_id == payload.product_id)
    ).scalar_one_or_none()
    if profile is None:
        profile = ProductGreenProfile(product_id=payload.product_id)
        db.add(profile)
    profile.origin = payload.origin
    profile.planting_mode = payload.planting_mode
    profile.certifications = payload.certifications
    profile.description = payload.description
    profile.status = "pending_review"
    db.flush()
    if payload.co2e_per_unit:
        db.add(
            CarbonAssessment(
                product_id=payload.product_id,
                co2e_per_unit=Decimal(payload.co2e_per_unit),
                methodology=payload.methodology,
                verified=False,  # 提交一律未核验
            )
        )
        db.flush()
    return ApiResponse(data=GreenProfileOut.model_validate(profile))


# ---------------- 管理端 ----------------
admin_router = APIRouter(prefix="/admin/green", tags=["admin-green"])


@admin_router.get(
    "/profiles", response_model=ApiResponse[PageOut[GreenProfileOut]], summary="绿色资料审核列表"
)
def admin_list(
    status: str | None = Query(None),
    page_size_pair: tuple[int, int] = Depends(page_params),
    _admin=Depends(require_permissions("green:review")),
    db: Session = Depends(get_db),
):
    stmt = select(ProductGreenProfile).order_by(ProductGreenProfile.updated_at.desc())
    if status:
        stmt = stmt.where(ProductGreenProfile.status == status)
    items, pagination = paginate(db, stmt, *page_size_pair)
    return ApiResponse(data=PageOut(items=[GreenProfileOut.model_validate(i) for i in items], pagination=pagination))


@admin_router.post(
    "/profiles/{profile_id}/review", response_model=ApiResponse[GreenProfileOut], summary="审核绿色资料"
)
def review_profile(
    profile_id: uuid.UUID,
    payload: ReviewIn,
    admin=Depends(require_permissions("green:review")),
    db: Session = Depends(get_db),
):
    profile = db.get(ProductGreenProfile, profile_id)
    if profile is None:
        raise AppError("NOT_FOUND", "资料不存在")
    if profile.status != "pending_review":
        raise AppError("CONFLICT", "当前状态不可审核")
    profile.status = "approved" if payload.action == "approve" else "rejected"
    profile.reviewed_by = admin.id
    db.flush()
    audit_service.log_operation(
        db, operator_id=admin.id, action=f"green.{payload.action}",
        resource="green_profile", resource_id=str(profile_id),
        detail={"reason": payload.reason},
    )
    return ApiResponse(data=GreenProfileOut.model_validate(profile))


@admin_router.post(
    "/assessments/{assessment_id}/verify", response_model=ApiResponse[dict], summary="核验碳评估（pass/fail）"
)
def verify_assessment(
    assessment_id: uuid.UUID,
    payload: ReviewIn,
    admin=Depends(require_permissions("green:review")),
    db: Session = Depends(get_db),
):
    a = db.get(CarbonAssessment, assessment_id)
    if a is None:
        raise AppError("NOT_FOUND", "评估记录不存在")
    passed = payload.action == "approve"
    a.verified = passed
    a.verifier_id = admin.id
    db.add(
        VerificationRecord(
            assessment_id=assessment_id,
            result="pass" if passed else "fail",
            notes=payload.reason,
            verifier_id=admin.id,
            created_at=utcnow(),
        )
    )
    db.flush()
    audit_service.log_operation(
        db, operator_id=admin.id, action="green.verify",
        resource="carbon_assessment", resource_id=str(assessment_id),
        detail={"result": "pass" if passed else "fail"},
    )
    return ApiResponse(data={"assessment_id": str(assessment_id), "verified": passed})
