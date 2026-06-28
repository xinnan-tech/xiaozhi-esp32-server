"""后台通知控制器"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_session
from app.infrastructure.persistence.models import AdminNotificationModel
from app.interfaces.api.auth import get_current_user, scoped_store_id

router = APIRouter(prefix="/notification", tags=["后台通知"])


@router.get("/list")
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    store_id = scoped_store_id(current_user)
    query = session.query(AdminNotificationModel)
    if store_id:
        query = query.filter(AdminNotificationModel.store_id == store_id)
    if status:
        query = query.filter(AdminNotificationModel.status == status)
    total = query.count()
    rows = query.order_by(AdminNotificationModel.create_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
    unread = session.query(AdminNotificationModel).filter(AdminNotificationModel.status == "unread")
    if store_id:
        unread = unread.filter(AdminNotificationModel.store_id == store_id)
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "list": [
                {
                    "id": n.id,
                    "storeId": n.store_id,
                    "title": n.title,
                    "content": n.content,
                    "notificationType": n.notification_type,
                    "targetRoute": n.target_route,
                    "targetId": n.target_id,
                    "status": n.status,
                    "createDate": str(n.create_date) if n.create_date else None,
                }
                for n in rows
            ],
            "total": total,
            "unread": unread.count(),
            "page": page,
            "pageSize": page_size,
        },
    }


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    store_id = scoped_store_id(current_user)
    query = session.query(AdminNotificationModel).filter(AdminNotificationModel.id == notification_id)
    if store_id:
        query = query.filter(AdminNotificationModel.store_id == store_id)
    item = query.first()
    if item:
        item.status = "read"
        session.commit()
    return {"code": 0, "msg": "success"}


@router.post("/read-all")
async def mark_all_read(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    store_id = scoped_store_id(current_user)
    query = session.query(AdminNotificationModel).filter(AdminNotificationModel.status == "unread")
    if store_id:
        query = query.filter(AdminNotificationModel.store_id == store_id)
    for item in query.all():
        item.status = "read"
    session.commit()
    return {"code": 0, "msg": "success"}
