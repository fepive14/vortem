"""Tests for the outbox atomicity guarantee (H-007).

Contract: publish() and session.commit() are now called in a single transaction.
If publish() fails, the business mutation is also rolled back.

The test session is shared with the app and does NOT auto-rollback on exception
(unlike the production get_session() dependency, which has try/except/rollback).
Tests call ``await session.rollback()`` explicitly after a simulated failure and
then query the DB to verify no change was committed.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.catalog import EventType
from app.models.event import Event
from app.models.lead import Lead, LeadStatus
from app.models.organization import Organization
from app.models.user import User

_WEBHOOK_BASE = "/api/v1/webhooks/voicehire"
_LEADS_URL = "/api/v1/leads"
_WEBHOOK_SECRET = "change-me-in-production"


@pytest_asyncio.fixture()
async def _committed_lead(
    session: AsyncSession,
    test_org: Organization,
) -> Lead:
    """A lead committed to the DB before the test body runs.

    Using commit (not just flush) means an explicit session.rollback() during
    the test only undoes the endpoint's changes, not the lead itself.
    """
    lead = Lead(
        organization_id=test_org.id,
        first_name="Webhook",
        last_name="Subject",
    )
    session.add(lead)
    await session.commit()
    return lead


# ─── H-007: Core atomicity ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_outbox_publish_failure_rolls_back_lead_creation(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    access_token: str,
) -> None:
    """H-007: Si publish() lanza excepción al crear un lead, el lead NO queda en la BD.

    Con el outbox: publish() flushes el Event en la misma transacción que el Lead.
    Si publish() falla antes de session.commit(), nada se persiste.
    """
    with patch(
        "app.api.v1.leads.publish",
        new_callable=AsyncMock,
        side_effect=RuntimeError("simulated publish failure"),
    ):
        client.cookies.set("access_token", access_token)
        response = await client.post(
            _LEADS_URL,
            json={"first_name": "Atomic", "last_name": "Test"},
        )

    assert response.status_code == 500

    # The test session override does not auto-rollback on exception.
    # Roll back the pending transaction explicitly before querying.
    await session.rollback()

    leads = (await session.execute(select(Lead))).scalars().all()
    assert leads == [], (
        "H-007: El lead quedó guardado aunque publish() falló — atomicidad rota"
    )


# ─── H-007: webhooks.py — status evaluado en memoria (post-flush, pre-commit) ─


@pytest.mark.asyncio
async def test_outbox_webhook_publish_failure_rolls_back_lead_status(
    client: AsyncClient,
    session: AsyncSession,
    _committed_lead: Lead,
    test_org: Organization,
) -> None:
    """H-007/webhooks.py: Si publish() falla, el status del lead NO cambia.

    process_voicehire_event() actualiza lead.status en memoria y llama flush().
    Con el outbox, session.commit() se llama DESPUÉS de publish(). Si publish()
    falla, el flush se revierte y el lead queda con su status original.
    """
    # Capture the ID before the request so it's available after session rollback
    # (rollback expires all object attributes, including the PK).
    lead_id = _committed_lead.id

    with patch(
        "app.api.v1.webhooks.publish",
        new_callable=AsyncMock,
        side_effect=RuntimeError("simulated publish failure"),
    ):
        response = await client.post(
            f"{_WEBHOOK_BASE}/{test_org.id}",
            json={
                "lead_id": str(lead_id),
                "event": "lead_qualified",
                "status": "qualified",
            },
            headers={"X-VoiceHire-Secret": _WEBHOOK_SECRET},
        )

    assert response.status_code == 500
    await session.rollback()

    db_lead = (
        await session.execute(select(Lead).where(Lead.id == lead_id))
    ).scalar_one()
    assert db_lead.status == LeadStatus.new, (
        "H-007: El status quedó 'qualified' aunque publish() falló — atomicidad rota"
    )


@pytest.mark.asyncio
async def test_outbox_webhook_both_events_committed_atomically(
    client: AsyncClient,
    session: AsyncSession,
    _committed_lead: Lead,
    test_org: Organization,
) -> None:
    """webhooks.py: LEAD_QUALIFIED y VOICEHIRE_CALL_COMPLETED se persisten en la
    misma transacción que el cambio de status del lead.

    Verifica que el status evaluado en memoria (post-flush, pre-commit) genera
    correctamente el evento condicional LEAD_QUALIFIED cuando status=='qualified'.
    """
    response = await client.post(
        f"{_WEBHOOK_BASE}/{test_org.id}",
        json={
            "lead_id": str(_committed_lead.id),
            "event": "lead_qualified",
            "status": "qualified",
        },
        headers={"X-VoiceHire-Secret": _WEBHOOK_SECRET},
    )
    assert response.status_code == 200

    events = (
        await session.execute(
            select(Event).where(Event.organization_id == test_org.id)
        )
    ).scalars().all()
    event_types = {e.type for e in events}

    assert EventType.LEAD_QUALIFIED in event_types, (
        "LEAD_QUALIFIED no se persistió — la evaluación del status pre-commit falló"
    )
    assert EventType.VOICEHIRE_CALL_COMPLETED in event_types, (
        "VOICEHIRE_CALL_COMPLETED no se persistió"
    )
