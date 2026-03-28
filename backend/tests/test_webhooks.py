"""Tests for POST /api/v1/webhooks/voicehire/{org_id} endpoint."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.activity import Activity
from app.models.lead import Lead, LeadStatus
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.user import User, UserRole

VOICEHIRE_SECRET = "change-me-in-production"


def _webhook_url(org_id: object) -> str:
    return f"/api/v1/webhooks/voicehire/{org_id}"


# ─── Local fixtures ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def test_lead(session: AsyncSession, test_org: Organization) -> Lead:
    lead = Lead(
        organization_id=test_org.id,
        first_name="Webhook",
        last_name="Lead",
        email="webhook@example.com",
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return lead


@pytest_asyncio.fixture()
async def supervisor_user(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="supervisor_wh@test.com",
        full_name="Supervisor WH",
        hashed_password=hash_password("pass123456"),
        is_active=True,
        organization_id=test_org.id,
        is_global_admin=False,
        role=UserRole.supervisor,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_updates_lead_status(
    client: AsyncClient,
    test_lead: Lead,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """POST with status='qualified' updates lead.status in the DB."""
    response = await client.post(
        _webhook_url(test_org.id),
        json={
            "lead_id": str(test_lead.id),
            "event": "lead_qualified",
            "status": "qualified",
        },
        headers={"X-VoiceHire-Secret": VOICEHIRE_SECRET},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "qualified"

    result = await session.execute(select(Lead).where(Lead.id == test_lead.id))
    refreshed = result.scalar_one()
    assert refreshed.status == LeadStatus.qualified


@pytest.mark.asyncio
async def test_webhook_merges_voicehire_data(
    client: AsyncClient,
    test_lead: Lead,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """Existing voicehire_data keys are preserved; new keys are added."""
    # Pre-seed voicehire_data.
    test_lead.voicehire_data = {"existing_key": "old_value"}
    await session.commit()

    response = await client.post(
        _webhook_url(test_org.id),
        json={
            "lead_id": str(test_lead.id),
            "event": "call_completed",
            "voicehire_data": {"new_key": "new_value"},
        },
        headers={"X-VoiceHire-Secret": VOICEHIRE_SECRET},
    )
    assert response.status_code == 200, response.text

    result = await session.execute(select(Lead).where(Lead.id == test_lead.id))
    refreshed = result.scalar_one()
    assert refreshed.voicehire_data["existing_key"] == "old_value"
    assert refreshed.voicehire_data["new_key"] == "new_value"


@pytest.mark.asyncio
async def test_webhook_creates_activity(
    client: AsyncClient,
    test_lead: Lead,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """Each webhook call creates an Activity record for the lead."""
    response = await client.post(
        _webhook_url(test_org.id),
        json={
            "lead_id": str(test_lead.id),
            "event": "call_completed",
        },
        headers={"X-VoiceHire-Secret": VOICEHIRE_SECRET},
    )
    assert response.status_code == 200, response.text

    result = await session.execute(
        select(Activity).where(Activity.lead_id == test_lead.id)
    )
    activity = result.scalar_one_or_none()
    assert activity is not None
    assert activity.type.value == "voicehire_call"


@pytest.mark.asyncio
async def test_webhook_wrong_secret(
    client: AsyncClient,
    test_lead: Lead,
    test_org: Organization,
) -> None:
    """Missing or wrong X-VoiceHire-Secret returns 401."""
    response = await client.post(
        _webhook_url(test_org.id),
        json={"lead_id": str(test_lead.id), "event": "call_completed"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_lead_not_found(
    client: AsyncClient,
    test_org: Organization,
) -> None:
    """Unknown lead_id returns 404."""
    response = await client.post(
        _webhook_url(test_org.id),
        json={
            "lead_id": "00000000-0000-0000-0000-000000000000",
            "event": "call_completed",
        },
        headers={"X-VoiceHire-Secret": VOICEHIRE_SECRET},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_webhook_qualified_triggers_notification(
    client: AsyncClient,
    test_lead: Lead,
    test_org: Organization,
    supervisor_user: User,
    session: AsyncSession,
) -> None:
    """After a qualified webhook event, the LEAD_QUALIFIED handler creates
    a notification for supervisors in the same org."""
    # Fire the webhook to qualify the lead.
    response = await client.post(
        _webhook_url(test_org.id),
        json={
            "lead_id": str(test_lead.id),
            "event": "lead_qualified",
            "status": "qualified",
        },
        headers={"X-VoiceHire-Secret": VOICEHIRE_SECRET},
    )
    assert response.status_code == 200, response.text

    # Directly invoke the handler (worker is not running in tests).
    from app.events.worker import _process_lead_qualified
    await _process_lead_qualified({"lead_id": str(test_lead.id)})

    # The handler commits using its own session; query via the test session.
    result = await session.execute(
        select(Notification).where(
            Notification.user_id == supervisor_user.id,
            Notification.organization_id == test_org.id,
        )
    )
    notifications = result.scalars().all()
    assert len(notifications) == 1
    assert notifications[0].type == "lead_qualified"
    assert notifications[0].priority == "high"
