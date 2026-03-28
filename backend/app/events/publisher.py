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
    """Persist an event and notify the worker via PostgreSQL LISTEN/NOTIFY.

    IMPORTANT: This function must be called AFTER the business transaction has
    been committed.  It opens a separate transaction for the event record so
    that a publisher failure does not roll back the business data.

    Args:
        session:         An AsyncSession.  The caller is responsible for
                         committing the business transaction before invoking
                         this function.
        event_type:      An EventType constant, e.g. EventType.INSTANCE_INITIALIZED.
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

    # Send the NOTIFY in the same transaction so the worker only receives it
    # after this INSERT commits — avoids the race between the worker reading
    # the event and the INSERT being visible.
    await session.execute(
        text("SELECT pg_notify('vortem_events', :event_id)"),
        {"event_id": str(event.id)},
    )
    await session.commit()

    logger.info(
        "event_published",
        event_id=str(event.id),
        event_type=event_type,
        organization_id=str(organization_id) if organization_id else None,
    )
