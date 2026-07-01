"""Tests for the vertical concept on organizations (H-029 / Epic V-1)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.create_admin import create_org_admin
from app.core.security import create_access_token
from app.models.organization import Organization, OrgVertical
from app.models.user import User


# ─── Default vertical ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_org_default_vertical_is_generic(session: AsyncSession) -> None:
    """Org created via CLI without specifying vertical defaults to 'generic'."""
    user = await create_org_admin(
        session,
        email="admin@genericorg.com",
        full_name="Generic Admin",
        org_name="Generic Org",
        password="password123",
    )
    await session.commit()

    org = await session.get(Organization, user.organization_id)
    assert org is not None
    assert org.vertical == OrgVertical.generic


@pytest.mark.asyncio
async def test_create_admin_with_veterinary_vertical(session: AsyncSession) -> None:
    """CLI create_org_admin can set vertical='veterinary' at creation time."""
    user = await create_org_admin(
        session,
        email="vet@clinic.com",
        full_name="Vet Admin",
        org_name="Happy Paws Clinic",
        password="password123",
        vertical=OrgVertical.veterinary,
    )
    await session.commit()

    org = await session.get(Organization, user.organization_id)
    assert org is not None
    assert org.vertical == OrgVertical.veterinary


# ─── Setup endpoint ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_setup_org_has_default_vertical(
    client: AsyncClient, session: AsyncSession
) -> None:
    """POST /setup without vertical creates org with vertical='generic'."""
    response = await client.post(
        "/api/v1/setup",
        json={
            "email": "founder@example.com",
            "password": "securepass123",
            "full_name": "Founder",
            "org_name": "Acme Corp",
        },
    )
    assert response.status_code == 201

    result = await session.execute(
        select(Organization).where(Organization.name == "Acme Corp")
    )
    org = result.scalar_one_or_none()
    assert org is not None
    assert org.vertical == OrgVertical.generic


@pytest.mark.asyncio
async def test_setup_accepts_veterinary_vertical(
    client: AsyncClient, session: AsyncSession
) -> None:
    """POST /setup with vertical='veterinary' persists that vertical on the org."""
    response = await client.post(
        "/api/v1/setup",
        json={
            "email": "founder@example.com",
            "password": "securepass123",
            "full_name": "Founder",
            "org_name": "Happy Paws Clinic",
            "vertical": "veterinary",
        },
    )
    assert response.status_code == 201

    result = await session.execute(
        select(Organization).where(Organization.name == "Happy Paws Clinic")
    )
    org = result.scalar_one_or_none()
    assert org is not None
    assert org.vertical == OrgVertical.veterinary


# ─── Guard: only global_admin can change vertical ─────────────────────────────


@pytest.mark.asyncio
async def test_normal_user_cannot_set_vertical(
    client: AsyncClient,
    test_user: User,
    test_org: Organization,
) -> None:
    """An org-scoped user (even admin role) gets 403 when trying to change vertical."""
    token = create_access_token({"sub": str(test_user.id)})
    response = await client.patch(
        f"/api/v1/organizations/{test_org.id}/vertical",
        json={"vertical": "veterinary"},
        cookies={"access_token": token},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_global_admin_can_set_vertical(
    client: AsyncClient,
    test_org: Organization,
    test_global_admin: User,
    session: AsyncSession,
) -> None:
    """A global admin can change an org's vertical via the API."""
    token = create_access_token({"sub": str(test_global_admin.id)})
    response = await client.patch(
        f"/api/v1/organizations/{test_org.id}/vertical",
        json={"vertical": "veterinary"},
        cookies={"access_token": token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["vertical"] == "veterinary"

    await session.refresh(test_org)
    assert test_org.vertical == OrgVertical.veterinary


@pytest.mark.asyncio
async def test_global_admin_cannot_set_unknown_vertical(
    client: AsyncClient,
    test_org: Organization,
    test_global_admin: User,
) -> None:
    """The endpoint rejects unknown vertical strings."""
    token = create_access_token({"sub": str(test_global_admin.id)})
    response = await client.patch(
        f"/api/v1/organizations/{test_org.id}/vertical",
        json={"vertical": "unknown_sector"},
        cookies={"access_token": token},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_global_admin_set_vertical_nonexistent_org(
    client: AsyncClient,
    test_global_admin: User,
) -> None:
    """Setting vertical on a non-existent org returns 404."""
    import uuid
    token = create_access_token({"sub": str(test_global_admin.id)})
    response = await client.patch(
        f"/api/v1/organizations/{uuid.uuid4()}/vertical",
        json={"vertical": "veterinary"},
        cookies={"access_token": token},
    )
    assert response.status_code == 404
