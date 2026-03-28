"""Notification endpoints — list, unread count, and mark-as-read."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.middleware.auth import get_current_org_id, require_auth
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationRead
from app.services import notification_service

router = APIRouter()


@router.get(
    "",
    response_model=list[NotificationRead],
    summary="List notifications",
)
async def list_notifications(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationRead]:
    org_id = get_current_org_id(current_user)
    notifications = await notification_service.list_notifications(
        session, current_user.id, org_id, skip=skip, limit=limit
    )
    return [NotificationRead.model_validate(n) for n in notifications]


@router.get(
    "/unread-count",
    summary="Unread notification count",
)
async def unread_count(
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> dict:
    org_id = get_current_org_id(current_user)
    count = await notification_service.get_unread_count(session, current_user.id, org_id)
    return {"count": count}


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
    summary="Mark notification as read",
)
async def mark_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> NotificationRead:
    org_id = get_current_org_id(current_user)
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
            Notification.organization_id == org_id,
        )
    )
    notification: Notification | None = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found."
        )
    updated = await notification_service.mark_as_read(session, notification)
    await session.commit()
    await session.refresh(updated)
    return NotificationRead.model_validate(updated)
