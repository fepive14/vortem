"""Tests for the create_org_admin CLI helper (H-009 fix).

These tests call the business-logic layer directly — no subprocess, no HTTP.
The CLI's interactive prompts (_main) are not tested here; only the logic that
matters for correctness and safety.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.create_admin import create_org_admin
from app.core.security import verify_password
from app.models.organization import Organization
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_create_admin_happy_path(session: AsyncSession) -> None:
    """Creates org + org-scoped admin with correct attributes and hashed password."""
    user = await create_org_admin(
        session,
        email="boss@acme.com",
        full_name="El Jefe",
        org_name="Acme Corp",
        password="supersecret99",
    )
    await session.commit()

    assert user.email == "boss@acme.com"
    assert user.full_name == "El Jefe"
    assert user.role == UserRole.admin
    assert user.is_active is True
    assert user.is_global_admin is False
    assert user.organization_id is not None
    assert verify_password("supersecret99", user.hashed_password), (
        "Password was not hashed correctly — verify_password returned False"
    )

    org = await session.get(Organization, user.organization_id)
    assert org is not None
    assert org.name == "Acme Corp"


@pytest.mark.asyncio
async def test_create_admin_org_admin_already_exists(
    session: AsyncSession,
    test_user: User,
) -> None:
    """Raises ValueError when an org-scoped user already exists.

    test_user (from conftest) is an org-scoped admin — exactly the condition
    the protection must detect and refuse.
    """
    with pytest.raises(ValueError, match="org admin already exists"):
        await create_org_admin(
            session,
            email="another@acme.com",
            full_name="Another Admin",
            org_name="Acme Corp",
            password="supersecret99",
        )


@pytest.mark.asyncio
async def test_create_admin_uses_existing_org(session: AsyncSession) -> None:
    """Reuses an existing org rather than creating a duplicate.

    Simulates the state after POST /api/v1/setup: an org exists but there is no
    org-scoped user yet (only a global admin, which has organization_id=None).
    """
    org = Organization(name="Vortem Corp")
    session.add(org)
    await session.flush()
    existing_org_id = org.id

    user = await create_org_admin(
        session,
        email="admin@vortem.com",
        full_name="Admin",
        org_name="Vortem Corp",
        password="password123",
    )
    await session.commit()

    assert user.organization_id == existing_org_id, (
        "create_org_admin created a new org instead of reusing the existing one"
    )

    orgs = (await session.execute(select(Organization))).scalars().all()
    assert len(orgs) == 1, (
        f"Expected 1 org, found {len(orgs)} — duplicate org was created"
    )
