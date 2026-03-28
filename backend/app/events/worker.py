"""Event bus worker — listens for PostgreSQL notifications and processes events.

Runs as a separate process:
    python -m app.events.worker

Responsibilities:
1. On startup: drain any unprocessed events (guards against missed notifications
   if the worker was down when events were published).
2. LISTEN on the 'vortem_events' channel.
3. For each notification: fetch the event, dispatch to a handler, mark as processed.
4. On handler failure: mark the event as failed with the error message.
5. Reconnect automatically if the PostgreSQL connection drops.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import asyncpg
from sqlalchemy import select

# Ensure the /app directory is on the path when running as `python -m`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.config import settings  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.deal import Deal  # noqa: E402
from app.models.lead import Lead  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.services import notification_service  # noqa: E402

configure_logging(settings.ENVIRONMENT, settings.LOG_LEVEL)
logger = get_logger(__name__)

_RECONNECT_DELAY = 5  # seconds between reconnection attempts


# ─── Event handlers ───────────────────────────────────────────────────────────
# Register handlers here as a mapping of event_type → coroutine function.
# Each handler receives the raw event record (asyncpg.Record).

async def _handle_instance_initialized(record: asyncpg.Record) -> None:
    logger.info("instance_initialized", payload=dict(record["payload"]))


async def _handle_default(record: asyncpg.Record) -> None:
    """No-op handler for unregistered event types."""
    logger.debug(
        "event_received_no_handler",
        event_type=record["type"],
        event_id=str(record["id"]),
    )


# ─── Phase 1D handlers ────────────────────────────────────────────────────────


async def _process_lead_qualified(payload: dict) -> None:
    """Create high-priority notifications for all supervisors in the lead's org.

    Exposed as a standalone coroutine so tests can invoke it directly without
    constructing a fake asyncpg.Record.
    """
    lead_id = UUID(payload["lead_id"])
    try:
        async with AsyncSessionLocal() as session:
            lead_result = await session.execute(
                select(Lead).where(Lead.id == lead_id)
            )
            lead: Lead | None = lead_result.scalar_one_or_none()
            if lead is None:
                logger.warning("lead_qualified_handler_lead_not_found", lead_id=str(lead_id))
                return

            supervisors_result = await session.execute(
                select(User).where(
                    User.organization_id == lead.organization_id,
                    User.role == UserRole.supervisor,
                    User.is_active.is_(True),
                )
            )
            supervisors = supervisors_result.scalars().all()

            for supervisor in supervisors:
                await notification_service.create_notification(
                    session=session,
                    user_id=supervisor.id,
                    organization_id=lead.organization_id,
                    type="lead_qualified",
                    priority="high",
                    title="Lead calificado pendiente de asignación",
                    body=(
                        f"{lead.first_name} {lead.last_name} "
                        "ha sido calificado por VoiceHire"
                    ),
                    entity_type="lead",
                    entity_id=lead.id,
                )

            await session.commit()
            logger.info(
                "lead_qualified_notifications_sent",
                lead_id=str(lead_id),
                supervisor_count=len(supervisors),
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("lead_qualified_handler_error", error=str(exc), lead_id=str(lead_id))


async def _handle_lead_qualified(record: asyncpg.Record) -> None:
    await _process_lead_qualified(dict(record["payload"]))


async def _process_lead_assigned(payload: dict) -> None:
    """Notify the assigned agent that a lead has been assigned to them."""
    lead_id = UUID(payload["lead_id"])
    assigned_to = UUID(payload["assigned_to"])
    try:
        async with AsyncSessionLocal() as session:
            lead_result = await session.execute(
                select(Lead).where(Lead.id == lead_id)
            )
            lead: Lead | None = lead_result.scalar_one_or_none()
            if lead is None:
                logger.warning("lead_assigned_handler_lead_not_found", lead_id=str(lead_id))
                return

            await notification_service.create_notification(
                session=session,
                user_id=assigned_to,
                organization_id=lead.organization_id,
                type="lead_assigned",
                priority="high",
                title="Lead asignado",
                body=f"Se te ha asignado el lead {lead.first_name} {lead.last_name}",
                entity_type="lead",
                entity_id=lead.id,
            )
            await session.commit()
            logger.info("lead_assigned_notification_sent", lead_id=str(lead_id))
    except Exception as exc:  # noqa: BLE001
        logger.exception("lead_assigned_handler_error", error=str(exc), lead_id=str(lead_id))


async def _handle_lead_assigned(record: asyncpg.Record) -> None:
    await _process_lead_assigned(dict(record["payload"]))


async def _process_deal_stage_changed(payload: dict) -> None:
    """Notify the deal's assigned user that the deal has moved stages."""
    deal_id = UUID(payload["deal_id"])
    try:
        async with AsyncSessionLocal() as session:
            deal_result = await session.execute(
                select(Deal).where(Deal.id == deal_id)
            )
            deal: Deal | None = deal_result.scalar_one_or_none()
            if deal is None:
                logger.warning("deal_stage_changed_handler_deal_not_found", deal_id=str(deal_id))
                return

            if deal.assigned_to is None:
                return

            await notification_service.create_notification(
                session=session,
                user_id=deal.assigned_to,
                organization_id=deal.organization_id,
                type="deal_stage_changed",
                priority="normal",
                title="Deal movido de etapa",
                body=f"El deal '{deal.name}' ha cambiado de etapa",
                entity_type="deal",
                entity_id=deal.id,
            )
            await session.commit()
            logger.info("deal_stage_changed_notification_sent", deal_id=str(deal_id))
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "deal_stage_changed_handler_error", error=str(exc), deal_id=str(deal_id)
        )


async def _handle_deal_stage_changed(record: asyncpg.Record) -> None:
    await _process_deal_stage_changed(dict(record["payload"]))


_HANDLERS: dict[str, object] = {
    "instance.initialized": _handle_instance_initialized,
    "lead.qualified": _handle_lead_qualified,
    "lead.assigned": _handle_lead_assigned,
    "deal.stage_changed": _handle_deal_stage_changed,
}


# ─── Core processing ──────────────────────────────────────────────────────────


async def _process_event(conn: asyncpg.Connection, event_id: UUID) -> None:
    """Fetch, dispatch, and mark a single event."""
    record = await conn.fetchrow(
        "SELECT * FROM events WHERE id = $1",
        event_id,
    )
    if record is None:
        logger.warning("event_not_found", event_id=str(event_id))
        return

    if record["processed_at"] is not None:
        # Already handled — can happen if two worker instances race.
        return

    handler = _HANDLERS.get(record["type"], _handle_default)
    try:
        await handler(record)  # type: ignore[operator]
        await conn.execute(
            "UPDATE events SET processed_at = $1 WHERE id = $2",
            datetime.now(tz=timezone.utc),
            event_id,
        )
        logger.info(
            "event_processed",
            event_id=str(event_id),
            event_type=record["type"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "event_processing_failed",
            event_id=str(event_id),
            event_type=record["type"],
            error=str(exc),
        )
        await conn.execute(
            "UPDATE events SET failed_at = $1, error = $2 WHERE id = $3",
            datetime.now(tz=timezone.utc),
            str(exc),
            event_id,
        )


async def _drain_pending(conn: asyncpg.Connection) -> None:
    """Process all events that were missed while the worker was offline."""
    rows = await conn.fetch(
        """
        SELECT id FROM events
        WHERE processed_at IS NULL AND failed_at IS NULL
        ORDER BY created_at ASC
        """
    )
    if not rows:
        return

    logger.info("draining_pending_events", count=len(rows))
    for row in rows:
        await _process_event(conn, row["id"])


# ─── Main loop ────────────────────────────────────────────────────────────────


async def _run_worker() -> None:
    """Main worker loop with automatic reconnection."""
    while True:
        try:
            conn: asyncpg.Connection = await asyncpg.connect(settings.worker_dsn)
            logger.info("worker_connected")

            await _drain_pending(conn)

            notification_queue: asyncio.Queue[UUID] = asyncio.Queue()

            def _on_notification(
                _conn: asyncpg.Connection,
                _pid: int,
                _channel: str,
                payload: str,
            ) -> None:
                try:
                    event_id = UUID(payload)
                    notification_queue.put_nowait(event_id)
                except ValueError:
                    logger.warning("invalid_notification_payload", payload=payload)

            await conn.add_listener("vortem_events", _on_notification)
            logger.info("listening_for_events", channel="vortem_events")

            try:
                while True:
                    # Wait for a notification; use a timeout to detect closed connections.
                    try:
                        event_id = await asyncio.wait_for(
                            notification_queue.get(), timeout=30.0
                        )
                    except asyncio.TimeoutError:
                        # Heartbeat — verify connection is still alive.
                        await conn.execute("SELECT 1")
                        continue

                    await _process_event(conn, event_id)

            finally:
                await conn.remove_listener("vortem_events", _on_notification)
                await conn.close()

        except (asyncpg.PostgresConnectionError, OSError) as exc:
            logger.warning(
                "worker_connection_lost",
                error=str(exc),
                retry_in=_RECONNECT_DELAY,
            )
            await asyncio.sleep(_RECONNECT_DELAY)

        except Exception as exc:  # noqa: BLE001
            logger.exception("worker_unexpected_error", error=str(exc))
            await asyncio.sleep(_RECONNECT_DELAY)


def main() -> None:
    """Entry point for `python -m app.events.worker`."""
    logger.info("worker_starting")
    asyncio.run(_run_worker())


if __name__ == "__main__":
    main()
