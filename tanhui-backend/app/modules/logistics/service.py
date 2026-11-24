"""物流服务：发货建单、轨迹查询（轨迹为 Mock 数据）。"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.base import utcnow
from app.core.errors import AppError
from app.modules.logistics.models import Shipment, ShipmentTrack
from app.modules.orders.models import StoreOrder


def create_shipment(
    db: Session,
    store_order: StoreOrder,
    carrier: str,
    tracking_no: str,
    operator_id: uuid.UUID,
) -> Shipment:
    exists = db.execute(
        select(Shipment).where(Shipment.store_order_id == store_order.id)
    ).scalar_one_or_none()
    if exists is not None:
        raise AppError("CONFLICT", "该店铺订单已有发货单")
    shipment = Shipment(
        store_order_id=store_order.id,
        carrier=carrier,
        tracking_no=tracking_no,
        shipped_by=operator_id,
    )
    db.add(shipment)
    db.flush()
    # 初始轨迹【仿真数据：真实场景接入物流商轨迹推送】
    db.add(
        ShipmentTrack(
            shipment_id=shipment.id,
            status="shipped",
            description=f"{carrier} 已揽收（Mock 轨迹）",
        )
    )
    db.flush()
    return shipment


def get_shipments_for_order(db: Session, store_order_ids: list[uuid.UUID]) -> list[dict]:
    """按店铺子单 ID 批量取发货单 + 轨迹。"""
    result = []
    if not store_order_ids:
        return result
    for sh in db.execute(
        select(Shipment).where(Shipment.store_order_id.in_(store_order_ids))
    ).scalars():
        tracks = [
            {
                "status": t.status,
                "description": t.description,
                "occurred_at": t.occurred_at,
            }
            for t in db.execute(
                select(ShipmentTrack)
                .where(ShipmentTrack.shipment_id == sh.id)
                .order_by(ShipmentTrack.occurred_at)
            ).scalars()
        ]
        result.append(
            {
                "id": str(sh.id),
                "store_order_id": str(sh.store_order_id),
                "carrier": sh.carrier,
                "tracking_no": sh.tracking_no,
                "status": sh.status,
                "shipped_at": sh.shipped_at,
                "delivered_at": sh.delivered_at,
                "tracks": tracks,
                "mock": True,  # 【仿真标记】轨迹为 Mock
            }
        )
    return result
