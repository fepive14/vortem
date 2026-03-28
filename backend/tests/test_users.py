"""Tests for /api/v1/users endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole

USERS_URL = "/api/v1/users"


# ─── Local fixtures ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def second_user(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="agent@test.com",
        full_name="Agent One",
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


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_users_returns_members(
    client: AsyncClient,
    access_token: str,
    test_user: User,
    second_user: User,
) -> None:
    """GET /users returns all org members."""
    client.cookies.set("access_token", access_token)
    response = await client.get(USERS_URL)
    assert response.status_code == 200
    ids = {u["id"] for u in response.json()}
    assert str(test_user.id) in ids
    assert str(second_user.id) in ids


@pytest.mark.asyncio
async def test_list_users_filter_by_role(
    client: AsyncClient,
    access_token: str,
    test_user: User,
    second_user: User,
) -> None:
    """GET /users?role=agent returns only agents."""
    client.cookies.set("access_token", access_token)
    response = await client.get(USERS_URL, params={"role": "agent"})
    assert response.status_code == 200
    data = response.json()
    assert all(u["role"] == "agent" for u in data)
    ids = {u["id"] for u in data}
    assert str(second_user.id) in ids
    assert str(test_user.id) not in ids


@pytest.mark.asyncio
async def test_get_user_success(
    client: AsyncClient,
    access_token: str,
    second_user: User,
) -> None:
    """GET /users/{id} returns the user."""
    client.cookies.set("access_token", access_token)
    response = await client.get(f"{USERS_URL}/{second_user.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(second_user.id)


@pytest.mark.asyncio
async def test_get_user_not_found(
    client: AsyncClient,
    access_token: str,
) -> None:
    """GET /users/{unknown_id} returns 404."""
    import uuid
    client.cookies.set("access_token", access_token)
    response = await client.get(f"{USERS_URL}/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_user_success(
    client: AsyncClient,
    access_token: str,
) -> None:
    """POST /users creates a new user in the org."""
    client.cookies.set("access_token", access_token)
    response = await client.post(
        USERS_URL,
        json={
            "email": "newagent@test.com",
            "password": "newpass123",
            "full_name": "New Agent",
            "role": "agent",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newagent@test.com"
    assert data["role"] == "agent"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_user_rejects_global_admin(
    client: AsyncClient,
    access_token: str,
) -> None:
    """POST /users with is_global_admin=True returns 403."""
    client.cookies.set("access_token", access_token)
    response = await client.post(
        USERS_URL,
        json={
            "email": "evilglobal@test.com",
            "password": "hackpass123",
            "full_name": "Evil Admin",
            "role": "admin",
            "is_global_admin": True,
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_user_success(
    client: AsyncClient,
    access_token: str,
    second_user: User,
) -> None:
    """PATCH /users/{id} updates allowed fields."""
    client.cookies.set("access_token", access_token)
    response = await client.patch(
        f"{USERS_URL}/{second_user.id}",
        json={"full_name": "Updated Name", "role": "supervisor"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["role"] == "supervisor"


@pytest.mark.asyncio
async def test_deactivate_user_success(
    client: AsyncClient,
    access_token: str,
    second_user: User,
) -> None:
    """DELETE /users/{id} soft-deletes by setting is_active=False."""
    client.cookies.set("access_token", access_token)
    response = await client.delete(f"{USERS_URL}/{second_user.id}")
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_deactivate_self_returns_400(
    client: AsyncClient,
    access_token: str,
    test_user: User,
) -> None:
    """DELETE /users/{own_id} returns 400 — cannot deactivate yourself."""
    client.cookies.set("access_token", access_token)
    response = await client.delete(f"{USERS_URL}/{test_user.id}")
    assert response.status_code == 400
