"""Tests for /api/v1/reports endpoints."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.activity import Activity, ActivityType
from app.models.lead import Lead, LeadStatus
from app.models.organization import Organization
from app.models.user import User, UserRole

REPORTS_URL = "/api/v1/reports"


# ─── Local fixtures ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def agent_user(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="report_agent@test.com",
        full_name="Report Agent",
        hashed_password=hash_password("agentpass123"),
        is_active=True,
        organization_id=test_org.id,
        is_global_admin=False,
        role=UserRole.agent,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ─── Funnel tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_funnel_empty_returns_all_statuses(
    client: AsyncClient,
    access_token: str,
) -> None:
    """GET /reports/funnel returns zero counts when no leads exist."""
    client.cookies.set("access_token", access_token)
    response = await client.get(f"{REPORTS_URL}/funnel")
    assert response.status_code == 200
    data = response.json()
    for s in ("new", "contacted", "qualified", "converted", "discarded"):
        assert s in data
        assert data[s] == 0


@pytest.mark.asyncio
async def test_funnel_counts_by_status(
    client: AsyncClient,
    access_token: str,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """GET /reports/funnel reflects actual lead counts per status."""
    for _ in range(2):
        session.add(Lead(organization_id=test_org.id, first_name="A", last_name="B", status=LeadStatus.new))
    session.add(Lead(organization_id=test_org.id, first_name="C", last_name="D", status=LeadStatus.qualified))
    await session.commit()

    client.cookies.set("access_token", access_token)
    response = await client.get(f"{REPORTS_URL}/funnel")
    assert response.status_code == 200
    data = response.json()
    assert data["new"] == 2
    assert data["qualified"] == 1


# ─── Agent performance tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_agent_performance_empty(
    client: AsyncClient,
    access_token: str,
) -> None:
    """GET /reports/agent-performance returns [] when no activities exist."""
    client.cookies.set("access_token", access_token)
    response = await client.get(f"{REPORTS_URL}/agent-performance")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_agent_performance_counts_activities(
    client: AsyncClient,
    access_token: str,
    test_org: Organization,
    agent_user: User,
    session: AsyncSession,
) -> None:
    """GET /reports/agent-performance counts activities per agent."""
    for _ in range(3):
        session.add(Activity(
            organization_id=test_org.id,
            type=ActivityType.call,
            assigned_to=agent_user.id,
        ))
    await session.commit()

    client.cookies.set("access_token", access_token)
    response = await client.get(f"{REPORTS_URL}/agent-performance")
    assert response.status_code == 200
    data = response.json()
    agent_row = next((r for r in data if r["agent_id"] == str(agent_user.id)), None)
    assert agent_row is not None
    assert agent_row["activities"] == 3
    assert agent_row["conversions"] == 0


@pytest.mark.asyncio
async def test_agent_performance_counts_conversions(
    client: AsyncClient,
    access_token: str,
    test_org: Organization,
    agent_user: User,
    session: AsyncSession,
) -> None:
    """GET /reports/agent-performance counts converted leads per agent."""
    session.add(Lead(
        organization_id=test_org.id,
        first_name="X",
        last_name="Y",
        status=LeadStatus.converted,
        assigned_to=agent_user.id,
    ))
    await session.commit()

    client.cookies.set("access_token", access_token)
    response = await client.get(f"{REPORTS_URL}/agent-performance")
    assert response.status_code == 200
    data = response.json()
    agent_row = next((r for r in data if r["agent_id"] == str(agent_user.id)), None)
    assert agent_row is not None
    assert agent_row["conversions"] == 1


# ─── Activity by campaign tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_activity_by_campaign_empty(
    client: AsyncClient,
    access_token: str,
) -> None:
    """GET /reports/activity-by-campaign returns [] when no campaign leads exist."""
    client.cookies.set("access_token", access_token)
    response = await client.get(f"{REPORTS_URL}/activity-by-campaign")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_activity_by_campaign_groups_correctly(
    client: AsyncClient,
    access_token: str,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """GET /reports/activity-by-campaign groups lead counts by campaign_id."""
    campaign_a = uuid.uuid4()
    campaign_b = uuid.uuid4()
    for _ in range(3):
        session.add(Lead(organization_id=test_org.id, first_name="A", last_name="B", campaign_id=campaign_a))
    session.add(Lead(organization_id=test_org.id, first_name="C", last_name="D", campaign_id=campaign_b))
    await session.commit()

    client.cookies.set("access_token", access_token)
    response = await client.get(f"{REPORTS_URL}/activity-by-campaign")
    assert response.status_code == 200
    data = response.json()
    by_campaign = {r["campaign_id"]: r["count"] for r in data}
    assert by_campaign[str(campaign_a)] == 3
    assert by_campaign[str(campaign_b)] == 1


@pytest.mark.asyncio
async def test_reports_require_auth(
    client: AsyncClient,
) -> None:
    """Report endpoints return 401 without a valid token."""
    response = await client.get(f"{REPORTS_URL}/funnel")
    assert response.status_code == 401
