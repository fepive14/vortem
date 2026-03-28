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

# Ensure the /app directory is on the path when running as `python -m`.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.config import settings  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402

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


_HANDLERS: dict[str, object] = {
    "instance.initialized": _handle_instance_initialized,
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
