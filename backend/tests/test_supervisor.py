"""Tests for GET/PATCH /api/v1/supervisor endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.lead import Lead, LeadStatus
from app.models.organization import Organization
from app.models.user import User, UserRole

SUPERVISOR_URL = "/api/v1/supervisor"


# ─── Local fixtures ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def agent_user(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="agent_sv@test.com",
        full_name="Agent User",
        hashed_password=hash_password("pass123456"),
        is_active=True,
        organization_id=test_org.id,
        is_global_admin=False,
        role=UserRole.agent,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def qualified_lead(session: AsyncSession, test_org: Organization) -> Lead:
    lead = Lead(
        organization_id=test_org.id,
        first_name="Queue",
        last_name="Lead",
        status=LeadStatus.qualified,
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return lead


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_queue_empty_initially(
    client: AsyncClient, access_token: str
) -> None:
    """GET /supervisor/leads/queue returns [] when no qualified leads exist."""
    client.cookies.set("access_token", access_token)
    response = await client.get(f"{SUPERVISOR_URL}/leads/queue")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_queue_shows_qualified_unassigned(
    client: AsyncClient,
    access_token: str,
    qualified_lead: Lead,
) -> None:
    """A qualified, unassigned lead appears in the queue."""
    client.cookies.set("access_token", access_token)
    response = await client.get(f"{SUPERVISOR_URL}/leads/queue")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(qualified_lead.id)


@pytest.mark.asyncio
async def test_queue_excludes_assigned(
    client: AsyncClient,
    access_token: str,
    qualified_lead: Lead,
    test_user: User,
    session: AsyncSession,
) -> None:
    """An assigned lead is not in the queue even if status=qualified."""
    qualified_lead.assigned_to = test_user.id
    await session.commit()

    client.cookies.set("access_token", access_token)
    response = await client.get(f"{SUPERVISOR_URL}/leads/queue")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_queue_excludes_non_qualified(
    client: AsyncClient,
    access_token: str,
    session: AsyncSession,
    test_org: Organization,
) -> None:
    """A lead with status='new' does not appear in the queue."""
    lead = Lead(
        organization_id=test_org.id,
        first_name="New",
        last_name="Lead",
        status=LeadStatus.new,
    )
    session.add(lead)
    await session.commit()

    client.cookies.set("access_token", access_token)
    response = await client.get(f"{SUPERVISOR_URL}/leads/queue")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_assign_lead_success(
    client: AsyncClient,
    access_token: str,
    qualified_lead: Lead,
    agent_user: User,
) -> None:
    """PATCH /supervisor/leads/{id}/assign sets assigned_to on the lead."""
    client.cookies.set("access_token", access_token)
    response = await client.patch(
        f"{SUPERVISOR_URL}/leads/{qualified_lead.id}/assign",
        json={"assigned_to": str(agent_user.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["assigned_to"] == str(agent_user.id)


@pytest.mark.asyncio
async def test_assign_lead_as_agent_forbidden(
    client: AsyncClient,
    agent_user: User,
    qualified_lead: Lead,
) -> None:
    """Agents cannot assign leads — 403."""
    token = create_access_token({"sub": str(agent_user.id)})
    client.cookies.set("access_token", token)
    response = await client.patch(
        f"{SUPERVISOR_URL}/leads/{qualified_lead.id}/assign",
        json={"assigned_to": str(agent_user.id)},
    )
    assert response.status_code == 403
