"""Tests for the /api/v1/deals/* endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.contact import Contact
from app.models.organization import Organization
from app.models.pipeline import Pipeline
from app.models.stage import Stage
from app.models.user import User, UserRole

DEALS_URL = "/api/v1/deals"


# ─── Local fixtures ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def pipeline(session: AsyncSession, test_org: Organization) -> Pipeline:
    p = Pipeline(organization_id=test_org.id, name="Test Pipeline")
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@pytest_asyncio.fixture()
async def stage(session: AsyncSession, test_org: Organization, pipeline: Pipeline) -> Stage:
    s = Stage(
        organization_id=test_org.id,
        pipeline_id=pipeline.id,
        name="Prospecting",
        order=1,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


@pytest_asyncio.fixture()
async def stage2(session: AsyncSession, test_org: Organization, pipeline: Pipeline) -> Stage:
    s = Stage(
        organization_id=test_org.id,
        pipeline_id=pipeline.id,
        name="Qualified",
        order=2,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


@pytest_asyncio.fixture()
async def contact(session: AsyncSession, test_org: Organization) -> Contact:
    c = Contact(
        organization_id=test_org.id,
        first_name="Deal",
        last_name="Contact",
    )
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return c


@pytest_asyncio.fixture()
async def agent_user(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="deal_agent@test.com",
        full_name="Deal Agent",
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


@pytest_asyncio.fixture()
async def supervisor_user(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="deal_supervisor@test.com",
        full_name="Deal Supervisor",
        hashed_password=hash_password("supervisorpass123"),
        is_active=True,
        organization_id=test_org.id,
        is_global_admin=False,
        role=UserRole.supervisor,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture()
def agent_token(agent_user: User) -> str:
    return create_access_token({"sub": str(agent_user.id)})


@pytest.fixture()
def supervisor_token(supervisor_user: User) -> str:
    return create_access_token({"sub": str(supervisor_user.id)})


@pytest.fixture()
def valid_deal_body(contact: Contact, stage: Stage, pipeline: Pipeline) -> dict:
    return {
        "name": "Big Deal",
        "contact_id": str(contact.id),
        "stage_id": str(stage.id),
        "pipeline_id": str(pipeline.id),
    }


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_deal_success(
    client: AsyncClient, access_token: str, valid_deal_body: dict
) -> None:
    """POST /deals returns 201 with correct fields."""
    client.cookies.set("access_token", access_token)
    response = await client.post(DEALS_URL, json=valid_deal_body)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "Big Deal"
    assert data["currency"] == "USD"
    assert "id" in data
    assert "organization_id" in data


@pytest.mark.asyncio
async def test_list_deals_empty(
    client: AsyncClient, access_token: str
) -> None:
    """GET /deals returns empty list when no deals exist."""
    client.cookies.set("access_token", access_token)
    response = await client.get(DEALS_URL)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_deal_success(
    client: AsyncClient, access_token: str, valid_deal_body: dict
) -> None:
    """GET /deals/{id} returns the correct deal."""
    client.cookies.set("access_token", access_token)
    create_resp = await client.post(DEALS_URL, json=valid_deal_body)
    deal_id = create_resp.json()["id"]

    response = await client.get(f"{DEALS_URL}/{deal_id}")
    assert response.status_code == 200, response.text
    assert response.json()["id"] == deal_id


@pytest.mark.asyncio
async def test_get_deal_not_found(
    client: AsyncClient, access_token: str
) -> None:
    """GET /deals/{unknown_id} returns 404."""
    client.cookies.set("access_token", access_token)
    response = await client.get(f"{DEALS_URL}/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_deal_stage(
    client: AsyncClient, access_token: str, valid_deal_body: dict, stage2: Stage
) -> None:
    """PATCH /deals/{id} with a new stage_id updates the stage."""
    client.cookies.set("access_token", access_token)
    create_resp = await client.post(DEALS_URL, json=valid_deal_body)
    deal_id = create_resp.json()["id"]

    response = await client.patch(
        f"{DEALS_URL}/{deal_id}", json={"stage_id": str(stage2.id)}
    )
    assert response.status_code == 200, response.text
    assert response.json()["stage_id"] == str(stage2.id)


@pytest.mark.asyncio
async def test_delete_deal_as_agent_forbidden(
    client: AsyncClient,
    access_token: str,
    agent_token: str,
    valid_deal_body: dict,
) -> None:
    """DELETE /deals/{id} returns 403 for an agent."""
    client.cookies.set("access_token", access_token)
    create_resp = await client.post(DEALS_URL, json=valid_deal_body)
    deal_id = create_resp.json()["id"]

    client.cookies.set("access_token", agent_token)
    response = await client.delete(f"{DEALS_URL}/{deal_id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_deal_as_supervisor(
    client: AsyncClient,
    access_token: str,
    supervisor_token: str,
    valid_deal_body: dict,
) -> None:
    """DELETE /deals/{id} returns 204 for a supervisor."""
    client.cookies.set("access_token", access_token)
    create_resp = await client.post(DEALS_URL, json=valid_deal_body)
    deal_id = create_resp.json()["id"]

    client.cookies.set("access_token", supervisor_token)
    response = await client.delete(f"{DEALS_URL}/{deal_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_deal_isolated_by_org(
    client: AsyncClient,
    access_token: str,
    valid_deal_body: dict,
    session: AsyncSession,
) -> None:
    """A deal in org A is not visible to a user in org B."""
    client.cookies.set("access_token", access_token)
    await client.post(DEALS_URL, json=valid_deal_body)

    org_b = Organization(name="Org B Deals")
    session.add(org_b)
    await session.flush()

    user_b = User(
        email="userb_deals@test.com",
        full_name="User B Deals",
        hashed_password=hash_password("userbpass123"),
        is_active=True,
        organization_id=org_b.id,
        is_global_admin=False,
        role=UserRole.admin,
    )
    session.add(user_b)
    await session.commit()
    await session.refresh(user_b)

    token_b = create_access_token({"sub": str(user_b.id)})
    client.cookies.set("access_token", token_b)
    response = await client.get(DEALS_URL)

    assert response.status_code == 200
    assert response.json() == []
