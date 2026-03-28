"""Tests for the /api/v1/pipelines/* endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole

PIPELINES_URL = "/api/v1/pipelines"

VALID_PIPELINE = {"name": "Sales Pipeline", "description": "Main sales funnel"}


# ─── Local fixtures ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def supervisor_user(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="pipe_supervisor@test.com",
        full_name="Pipeline Supervisor",
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


@pytest_asyncio.fixture()
async def agent_user(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="pipe_agent@test.com",
        full_name="Pipeline Agent",
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


@pytest.fixture()
def supervisor_token(supervisor_user: User) -> str:
    return create_access_token({"sub": str(supervisor_user.id)})


@pytest.fixture()
def agent_token(agent_user: User) -> str:
    return create_access_token({"sub": str(agent_user.id)})


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_pipeline_as_supervisor(
    client: AsyncClient, supervisor_token: str
) -> None:
    """POST /pipelines returns 201 with correct fields for a supervisor."""
    client.cookies.set("access_token", supervisor_token)
    response = await client.post(PIPELINES_URL, json=VALID_PIPELINE)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == VALID_PIPELINE["name"]
    assert data["description"] == VALID_PIPELINE["description"]
    assert "id" in data
    assert "organization_id" in data


@pytest.mark.asyncio
async def test_create_pipeline_as_agent_forbidden(
    client: AsyncClient, agent_token: str
) -> None:
    """POST /pipelines returns 403 for an agent."""
    client.cookies.set("access_token", agent_token)
    response = await client.post(PIPELINES_URL, json=VALID_PIPELINE)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_pipelines(
    client: AsyncClient, access_token: str, supervisor_token: str
) -> None:
    """GET /pipelines returns the created pipeline."""
    client.cookies.set("access_token", supervisor_token)
    await client.post(PIPELINES_URL, json=VALID_PIPELINE)

    client.cookies.set("access_token", access_token)
    response = await client.get(PIPELINES_URL)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == VALID_PIPELINE["name"]


@pytest.mark.asyncio
async def test_get_pipeline_not_found(
    client: AsyncClient, access_token: str
) -> None:
    """GET /pipelines/{unknown_id} returns 404."""
    client.cookies.set("access_token", access_token)
    response = await client.get(f"{PIPELINES_URL}/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_pipeline(
    client: AsyncClient, access_token: str, supervisor_token: str
) -> None:
    """PATCH /pipelines/{id} updates the pipeline name."""
    client.cookies.set("access_token", supervisor_token)
    create_resp = await client.post(PIPELINES_URL, json=VALID_PIPELINE)
    pipeline_id = create_resp.json()["id"]

    response = await client.patch(
        f"{PIPELINES_URL}/{pipeline_id}", json={"name": "Renamed Pipeline"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Renamed Pipeline"


@pytest.mark.asyncio
async def test_delete_pipeline_as_admin(
    client: AsyncClient, access_token: str, supervisor_token: str
) -> None:
    """DELETE /pipelines/{id} returns 204 for an admin."""
    client.cookies.set("access_token", supervisor_token)
    create_resp = await client.post(PIPELINES_URL, json=VALID_PIPELINE)
    pipeline_id = create_resp.json()["id"]

    client.cookies.set("access_token", access_token)
    response = await client.delete(f"{PIPELINES_URL}/{pipeline_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_pipeline_as_supervisor_forbidden(
    client: AsyncClient, supervisor_token: str
) -> None:
    """DELETE /pipelines/{id} returns 403 for a supervisor (admin-only)."""
    client.cookies.set("access_token", supervisor_token)
    create_resp = await client.post(PIPELINES_URL, json=VALID_PIPELINE)
    pipeline_id = create_resp.json()["id"]

    response = await client.delete(f"{PIPELINES_URL}/{pipeline_id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pipeline_isolated_by_org(
    client: AsyncClient,
    access_token: str,
    supervisor_token: str,
    session: AsyncSession,
) -> None:
    """A pipeline in org A is not visible to a user in org B."""
    client.cookies.set("access_token", supervisor_token)
    await client.post(PIPELINES_URL, json=VALID_PIPELINE)

    org_b = Organization(name="Org B Pipelines")
    session.add(org_b)
    await session.flush()

    user_b = User(
        email="userb_pipelines@test.com",
        full_name="User B",
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
    response = await client.get(PIPELINES_URL)

    assert response.status_code == 200
    assert response.json() == []
