"""积分管理端接口：规则版本管理、用户绿豆调整（需 points:manage 权限）。"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permissions
from app.core.errors import AppError
from app.core.responses import ApiResponse
from app.modules.points import service
from app.modules.points.models import PointRule, PointRuleVersion

router = APIRouter(prefix="/admin/points", tags=["admin-points"])


class RuleOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    current_version_id: uuid.UUID | None = None


class RuleVersionOut(BaseModel):
    id: uuid.UUID
    rule_id: uuid.UUID
    version: int
    config: dict
    effective_from: datetime
    created_at: datetime


class RuleUpdateIn(BaseModel):
    config: dict = Field(..., description='如 {"enabled": true, "rate": "1"}')


class AdjustIn(BaseModel):
    user_id: uuid.UUID
    delta: int
    reason: str = Field(..., min_length=2, max_length=255)

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("调整原因不能为空白")
        return v.strip()


@router.get("/rules", response_model=ApiResponse[list[RuleOut]], summary="积分规则列表")
def list_rules(
    _admin=Depends(require_permissions("points:manage")), db: Session = Depends(get_db)
):
    service.ensure_rules_seeded(db)
    rules = db.execute(select(PointRule)).scalars()
    return ApiResponse(data=[RuleOut.model_validate(r) for r in rules])


@router.get(
    "/rules/{rule_id}/versions", response_model=ApiResponse[list[RuleVersionOut]], summary="规则版本历史"
)
def rule_versions(
    rule_id: uuid.UUID,
    _admin=Depends(require_permissions("points:manage")),
    db: Session = Depends(get_db),
):
    versions = db.execute(
        select(PointRuleVersion)
        .where(PointRuleVersion.rule_id == rule_id)
        .order_by(PointRuleVersion.version.desc())
    ).scalars()
    return ApiResponse(data=[RuleVersionOut.model_validate(v) for v in versions])


@router.put("/rules/{code}", response_model=ApiResponse[RuleOut], summary="更新规则（生成新版本）")
def update_rule(
    code: str,
    payload: RuleUpdateIn,
    admin=Depends(require_permissions("points:manage")),
    db: Session = Depends(get_db),
):
    rule = service.update_rule(db, code, payload.config, admin.id)
    return ApiResponse(data=RuleOut.model_validate(rule))


@router.post("/adjust", response_model=ApiResponse[dict], summary="调整用户绿豆（必填原因，记审计）")
def adjust(
    payload: AdjustIn,
    admin=Depends(require_permissions("points:manage")),
    db: Session = Depends(get_db),
):
    txn = service.admin_adjust(db, payload.user_id, payload.delta, payload.reason, admin.id)
    return ApiResponse(
        data={"transaction_id": str(txn.id), "balance_after": txn.balance_after}
    )
