"""Tests for the POST /api/v1/leads/{id}/convert endpoint."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.lead import Lead, LeadStatus
from app.models.organization import Organization
from app.models.pipeline import Pipeline
from app.models.stage import Stage

LEADS_URL = "/api/v1/leads"


# ─── Local fixtures ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def test_lead(session: AsyncSession, test_org: Organization) -> Lead:
    lead = Lead(
        organization_id=test_org.id,
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="+1234567890",
        country="US",
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return lead


@pytest_asyncio.fixture()
async def lead_with_voicehire(session: AsyncSession, test_org: Organization) -> Lead:
    lead = Lead(
        organization_id=test_org.id,
        first_name="Voice",
        last_name="Hire",
        email="voice@example.com",
        voicehire_data={"call_id": "abc123", "duration": 120, "outcome": "interested"},
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return lead


@pytest_asyncio.fixture()
async def pipeline(session: AsyncSession, test_org: Organization) -> Pipeline:
    p = Pipeline(organization_id=test_org.id, name="Conversion Pipeline")
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@pytest_asyncio.fixture()
async def stage(session: AsyncSession, test_org: Organization, pipeline: Pipeline) -> Stage:
    s = Stage(
        organization_id=test_org.id,
        pipeline_id=pipeline.id,
        name="New",
        order=1,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_convert_lead_creates_contact(
    client: AsyncClient, access_token: str, test_lead: Lead
) -> None:
    """POST /leads/{id}/convert returns a contact with correct fields."""
    client.cookies.set("access_token", access_token)
    response = await client.post(
        f"{LEADS_URL}/{test_lead.id}/convert", json={}
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "contact" in data
    contact = data["contact"]
    assert contact["first_name"] == test_lead.first_name
    assert contact["last_name"] == test_lead.last_name
    assert contact["email"] == test_lead.email
    assert str(contact["lead_id"]) == str(test_lead.id)
    assert data["deal"] is None


@pytest.mark.asyncio
async def test_convert_lead_sets_status_converted(
    client: AsyncClient, access_token: str, test_lead: Lead, session: AsyncSession
) -> None:
    """After conversion the lead's status is 'converted'."""
    client.cookies.set("access_token", access_token)
    await client.post(f"{LEADS_URL}/{test_lead.id}/convert", json={})

    result = await session.execute(
        select(Lead).where(Lead.id == test_lead.id)
    )
    refreshed = result.scalar_one()
    assert refreshed.status == LeadStatus.converted


@pytest.mark.asyncio
async def test_convert_lead_idempotency(
    client: AsyncClient, access_token: str, test_lead: Lead
) -> None:
    """A second conversion attempt on the same lead returns 400."""
    client.cookies.set("access_token", access_token)
    await client.post(f"{LEADS_URL}/{test_lead.id}/convert", json={})

    response = await client.post(f"{LEADS_URL}/{test_lead.id}/convert", json={})
    assert response.status_code == 400
    assert "already converted" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_convert_lead_not_found(
    client: AsyncClient, access_token: str
) -> None:
    """POST /leads/{unknown_id}/convert returns 404."""
    client.cookies.set("access_token", access_token)
    response = await client.post(
        f"{LEADS_URL}/00000000-0000-0000-0000-000000000000/convert", json={}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_convert_lead_with_deal(
    client: AsyncClient,
    access_token: str,
    test_lead: Lead,
    pipeline: Pipeline,
    stage: Stage,
) -> None:
    """create_deal=True with stage_id+pipeline_id returns a non-null deal."""
    client.cookies.set("access_token", access_token)
    response = await client.post(
        f"{LEADS_URL}/{test_lead.id}/convert",
        json={
            "create_deal": True,
            "stage_id": str(stage.id),
            "pipeline_id": str(pipeline.id),
            "deal_name": "Jane's Deal",
            "value": 5000.0,
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["deal"] is not None
    assert data["deal"]["name"] == "Jane's Deal"
    assert data["deal"]["stage_id"] == str(stage.id)
    assert data["deal"]["pipeline_id"] == str(pipeline.id)


@pytest.mark.asyncio
async def test_convert_lead_voicehire_data_creates_activity(
    client: AsyncClient,
    access_token: str,
    lead_with_voicehire: Lead,
    session: AsyncSession,
) -> None:
    """A lead with non-empty voicehire_data produces an Activity record."""
    client.cookies.set("access_token", access_token)
    response = await client.post(
        f"{LEADS_URL}/{lead_with_voicehire.id}/convert", json={}
    )
    assert response.status_code == 200, response.text

    result = await session.execute(
        select(Activity).where(Activity.lead_id == lead_with_voicehire.id)
    )
    activity = result.scalar_one_or_none()
    assert activity is not None
    assert activity.type.value == "voicehire_call"
