"""Notification service — create and retrieve user notifications."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.notification import Notification

logger = get_logger(__name__)


async def create_notification(
    session: AsyncSession,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    type: str,
    title: str,
    body: str,
    priority: str = "normal",
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> Notification:
    """Insert a Notification. No flush — caller decides."""
    notification = Notification(
        user_id=user_id,
        organization_id=organization_id,
        type=type,
        title=title,
        body=body,
        priority=priority,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    session.add(notification)
    return notification


async def list_notifications(
    session: AsyncSession,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Notification]:
    """Return notifications for the given user, newest first."""
    result = await session.execute(
        select(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
        )
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_unread_count(
    session: AsyncSession,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> int:
    """Count unread notifications for the given user."""
    result = await session.execute(
        select(func.count()).where(
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
            Notification.read_at.is_(None),
        )
    )
    return result.scalar_one()


async def mark_as_read(
    session: AsyncSession,
    notification: Notification,
) -> Notification:
    """Set read_at to now. Caller commits."""
    notification.read_at = datetime.now(tz=timezone.utc)
    await session.flush()
    return notification
