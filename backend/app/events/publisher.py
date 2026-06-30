"""Event publisher — inserts event records and triggers LISTEN/NOTIFY."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.event import Event

logger = get_logger(__name__)


async def publish(
    session: AsyncSession,
    event_type: str,
    payload: dict,
    organization_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> None:
    """Flush an Event into the caller's open transaction and schedule NOTIFY.

    Must be called BEFORE session.commit().  The Event INSERT and the
    pg_notify() are part of the same transaction as the business data, so
    a failure here (or in the caller before commit) rolls back everything —
    no orphaned business records without a matching event.

    pg_notify() is transactional: the worker only receives the notification
    after the enclosing transaction commits, which closes the race between
    the worker reading the event and the row being visible.

    Args:
        session:         An open AsyncSession with an active transaction.
        event_type:      An EventType constant, e.g. EventType.LEAD_CREATED.
        payload:         Arbitrary JSON-serialisable dict with event data.
        organization_id: Tenant scope (None for global/system events).
        user_id:         Actor that triggered the event (None if not applicable).
    """
    event = Event(
        type=event_type,
        payload=payload,
        organization_id=organization_id,
        user_id=user_id,
    )
    session.add(event)
    await session.flush()  # Assigns event.id without committing.

    # NOTIFY is transactional — delivered only when the caller commits.
    await session.execute(
        text("SELECT pg_notify('vortem_events', :event_id)"),
        {"event_id": str(event.id)},
    )

    logger.info(
        "event_staged",
        event_id=str(event.id),
        event_type=event_type,
        organization_id=str(organization_id) if organization_id else None,
    )
