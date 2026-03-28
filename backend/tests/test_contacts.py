"""Tests for the /api/v1/contacts/* endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole

CONTACTS_URL = "/api/v1/contacts"

VALID_CONTACT = {
    "first_name": "Alice",
    "last_name": "Smith",
    "email": "alice@example.com",
    "phone": "+1234567890",
    "company": "Acme",
}


# ─── Local fixtures ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def agent_user(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="agent@test.com",
        full_name="Agent User",
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
async def viewer_user(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="viewer@test.com",
        full_name="Viewer User",
        hashed_password=hash_password("viewerpass123"),
        is_active=True,
        organization_id=test_org.id,
        is_global_admin=False,
        role=UserRole.viewer,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def supervisor_user(session: AsyncSession, test_org: Organization) -> User:
    user = User(
        email="supervisor@test.com",
        full_name="Supervisor User",
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
def viewer_token(viewer_user: User) -> str:
    return create_access_token({"sub": str(viewer_user.id)})


@pytest.fixture()
def supervisor_token(supervisor_user: User) -> str:
    return create_access_token({"sub": str(supervisor_user.id)})


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_contact_success(
    client: AsyncClient, access_token: str
) -> None:
    """POST /contacts returns 201 with correct fields."""
    client.cookies.set("access_token", access_token)
    response = await client.post(CONTACTS_URL, json=VALID_CONTACT)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["first_name"] == VALID_CONTACT["first_name"]
    assert data["last_name"] == VALID_CONTACT["last_name"]
    assert data["email"] == VALID_CONTACT["email"]
    assert data["status"] == "active"
    assert "id" in data
    assert "organization_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_contacts_empty(
    client: AsyncClient, access_token: str
) -> None:
    """GET /contacts returns empty list when no contacts exist."""
    client.cookies.set("access_token", access_token)
    response = await client.get(CONTACTS_URL)

    assert response.status_code == 200, response.text
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_contacts_returns_created(
    client: AsyncClient, access_token: str
) -> None:
    """Created contact appears in the list."""
    client.cookies.set("access_token", access_token)
    await client.post(CONTACTS_URL, json=VALID_CONTACT)

    response = await client.get(CONTACTS_URL)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["first_name"] == VALID_CONTACT["first_name"]


@pytest.mark.asyncio
async def test_get_contact_success(
    client: AsyncClient, access_token: str
) -> None:
    """GET /contacts/{id} returns the correct contact."""
    client.cookies.set("access_token", access_token)
    create_resp = await client.post(CONTACTS_URL, json=VALID_CONTACT)
    contact_id = create_resp.json()["id"]

    response = await client.get(f"{CONTACTS_URL}/{contact_id}")
    assert response.status_code == 200, response.text
    assert response.json()["id"] == contact_id


@pytest.mark.asyncio
async def test_get_contact_not_found(
    client: AsyncClient, access_token: str
) -> None:
    """GET /contacts/{unknown_id} returns 404."""
    client.cookies.set("access_token", access_token)
    response = await client.get(f"{CONTACTS_URL}/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_contact_as_agent(
    client: AsyncClient,
    access_token: str,
    agent_token: str,
) -> None:
    """PATCH /contacts/{id} succeeds for an agent."""
    client.cookies.set("access_token", access_token)
    create_resp = await client.post(CONTACTS_URL, json=VALID_CONTACT)
    contact_id = create_resp.json()["id"]

    client.cookies.set("access_token", agent_token)
    response = await client.patch(
        f"{CONTACTS_URL}/{contact_id}", json={"company": "Updated Corp"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["company"] == "Updated Corp"


@pytest.mark.asyncio
async def test_update_contact_as_viewer_forbidden(
    client: AsyncClient,
    access_token: str,
    viewer_token: str,
) -> None:
    """PATCH /contacts/{id} returns 403 for a viewer."""
    client.cookies.set("access_token", access_token)
    create_resp = await client.post(CONTACTS_URL, json=VALID_CONTACT)
    contact_id = create_resp.json()["id"]

    client.cookies.set("access_token", viewer_token)
    response = await client.patch(
        f"{CONTACTS_URL}/{contact_id}", json={"company": "Should Fail"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_contact_as_supervisor(
    client: AsyncClient,
    access_token: str,
    supervisor_token: str,
) -> None:
    """DELETE /contacts/{id} returns 204 for a supervisor."""
    client.cookies.set("access_token", access_token)
    create_resp = await client.post(CONTACTS_URL, json=VALID_CONTACT)
    contact_id = create_resp.json()["id"]

    client.cookies.set("access_token", supervisor_token)
    response = await client.delete(f"{CONTACTS_URL}/{contact_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_contact_as_agent_forbidden(
    client: AsyncClient,
    access_token: str,
    agent_token: str,
) -> None:
    """DELETE /contacts/{id} returns 403 for an agent."""
    client.cookies.set("access_token", access_token)
    create_resp = await client.post(CONTACTS_URL, json=VALID_CONTACT)
    contact_id = create_resp.json()["id"]

    client.cookies.set("access_token", agent_token)
    response = await client.delete(f"{CONTACTS_URL}/{contact_id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_contact_isolated_by_org(
    client: AsyncClient,
    access_token: str,
    session: AsyncSession,
) -> None:
    """A contact in org A is not visible to a user in org B."""
    # Create the contact in org A
    client.cookies.set("access_token", access_token)
    await client.post(CONTACTS_URL, json=VALID_CONTACT)

    # Create org B and a user in it
    org_b = Organization(name="Org B")
    session.add(org_b)
    await session.flush()

    user_b = User(
        email="userb_contacts@test.com",
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
    response = await client.get(CONTACTS_URL)

    assert response.status_code == 200
    assert response.json() == []
