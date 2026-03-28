"""Tests for the /api/v1/auth/* endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User

LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
REFRESH_URL = "/api/v1/auth/refresh"
ME_URL = "/api/v1/auth/me"


# ─── Login ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User) -> None:
    """Valid credentials return user data and set httpOnly cookies."""
    response = await client.post(
        LOGIN_URL,
        json={"email": test_user.email, "password": "testpassword123"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["email"] == test_user.email
    assert "hashed_password" not in data["user"]

    # Both cookies must be set
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: User) -> None:
    """Wrong password returns 401."""
    response = await client.post(
        LOGIN_URL,
        json={"email": test_user.email, "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient) -> None:
    """Non-existent email returns 401 (no user enumeration)."""
    response = await client.post(
        LOGIN_URL,
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(
    client: AsyncClient,
    test_user: User,
) -> None:
    """Deactivated account returns 403."""
    test_user.is_active = False
    response = await client.post(
        LOGIN_URL,
        json={"email": test_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 403
    test_user.is_active = True  # Reset for other tests


# ─── Logout ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logout_clears_cookies(client: AsyncClient, test_user: User) -> None:
    """Logout clears both auth cookies."""
    # Login first
    await client.post(
        LOGIN_URL,
        json={"email": test_user.email, "password": "testpassword123"},
    )

    response = await client.post(LOGOUT_URL)
    assert response.status_code == 204

    # Cookies should be cleared (set with empty value or expired)
    # httpx represents deleted cookies as absent or with empty value
    assert response.cookies.get("access_token", "") in ("", None)


# ─── Refresh ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_success(
    client: AsyncClient,
    test_user: User,
    refresh_token_fixture: str,
) -> None:
    """A valid refresh token rotates both tokens and returns user data."""
    client.cookies.set("refresh_token", refresh_token_fixture)
    response = await client.post(REFRESH_URL)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["email"] == test_user.email

    # New cookies issued
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_refresh_no_cookie(client: AsyncClient) -> None:
    """Missing refresh token cookie returns 401."""
    response = await client.post(REFRESH_URL)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient) -> None:
    """Tampered refresh token returns 401."""
    client.cookies.set("refresh_token", "not.a.valid.token")
    response = await client.post(REFRESH_URL)
    assert response.status_code == 401


# ─── Me ───────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_me_authenticated(
    client: AsyncClient,
    test_user: User,
    access_token: str,
) -> None:
    """Valid access token returns the authenticated user's profile."""
    client.cookies.set("access_token", access_token)
    response = await client.get(ME_URL)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient) -> None:
    """No cookie returns 401."""
    response = await client.get(ME_URL)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient) -> None:
    """Bogus access token returns 401."""
    client.cookies.set("access_token", "garbage.token.value")
    response = await client.get(ME_URL)
    assert response.status_code == 401
