"""Tests for the /api/v1/setup bootstrap endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User, UserRole

SETUP_URL = "/api/v1/setup"

VALID_BODY = {
    "email": "founder@example.com",
    "password": "securepass123",
    "full_name": "Founder User",
    "org_name": "Acme Corp",
}


@pytest.mark.asyncio
async def test_setup_happy_path(client: AsyncClient, session: AsyncSession) -> None:
    """POST /setup creates org + global admin and returns the user."""
    response = await client.post(SETUP_URL, json=VALID_BODY)

    assert response.status_code == 201, response.text
    data = response.json()

    assert data["email"] == VALID_BODY["email"]
    assert data["full_name"] == VALID_BODY["full_name"]
    assert data["is_global_admin"] is True
    assert data["role"] == UserRole.admin.value
    assert "hashed_password" not in data

    # Verify DB state
    result = await session.execute(
        select(User).where(User.email == VALID_BODY["email"])
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.is_global_admin is True
    assert user.organization_id is None

    org_result = await session.execute(
        select(Organization).where(Organization.name == VALID_BODY["org_name"])
    )
    org = org_result.scalar_one_or_none()
    assert org is not None


@pytest.mark.asyncio
async def test_setup_already_initialized(
    client: AsyncClient,
    test_user: User,  # Creates a user, so instance is "initialized"
) -> None:
    """POST /setup returns 403 when the instance already has users."""
    response = await client.post(SETUP_URL, json=VALID_BODY)
    assert response.status_code == 403
    assert "already initialized" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_setup_weak_password(client: AsyncClient) -> None:
    """POST /setup rejects passwords shorter than 8 characters."""
    body = {**VALID_BODY, "password": "short"}
    response = await client.post(SETUP_URL, json=body)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_setup_invalid_email(client: AsyncClient) -> None:
    """POST /setup rejects malformed email addresses."""
    body = {**VALID_BODY, "email": "not-an-email"}
    response = await client.post(SETUP_URL, json=body)
    assert response.status_code == 422
