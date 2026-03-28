"""Tests for GET/PATCH /api/v1/notifications endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services import notification_service

NOTIF_URL = "/api/v1/notifications"


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _make_notification(
    session: AsyncSession,
    user: User,
    org: Organization,
    title: str = "Test",
) -> None:
    await notification_service.create_notification(
        session=session,
        user_id=user.id,
        organization_id=org.id,
        type="lead_qualified",
        title=title,
        body="A test notification",
        priority="normal",
    )
    await session.commit()


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_list_notifications(
    client: AsyncClient,
    access_token: str,
    test_user: User,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """Notifications created via service are returned by GET /notifications."""
    await _make_notification(session, test_user, test_org, title="Notif A")
    await _make_notification(session, test_user, test_org, title="Notif B")

    client.cookies.set("access_token", access_token)
    response = await client.get(NOTIF_URL)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = {n["title"] for n in data}
    assert titles == {"Notif A", "Notif B"}


@pytest.mark.asyncio
async def test_unread_count(
    client: AsyncClient,
    access_token: str,
    test_user: User,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """Unread count equals number of notifications before any are read."""
    for i in range(3):
        await _make_notification(session, test_user, test_org, title=f"N{i}")

    client.cookies.set("access_token", access_token)
    response = await client.get(f"{NOTIF_URL}/unread-count")
    assert response.status_code == 200
    assert response.json()["count"] == 3


@pytest.mark.asyncio
async def test_mark_as_read(
    client: AsyncClient,
    access_token: str,
    test_user: User,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """PATCH /{id}/read sets read_at; unread count drops to 0."""
    notif = await notification_service.create_notification(
        session=session,
        user_id=test_user.id,
        organization_id=test_org.id,
        type="lead_qualified",
        title="Mark me",
        body="body",
    )
    await session.commit()
    await session.refresh(notif)

    client.cookies.set("access_token", access_token)
    response = await client.patch(f"{NOTIF_URL}/{notif.id}/read")
    assert response.status_code == 200
    data = response.json()
    assert data["read_at"] is not None

    count_resp = await client.get(f"{NOTIF_URL}/unread-count")
    assert count_resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_mark_as_read_wrong_user(
    client: AsyncClient,
    test_user: User,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """A notification belonging to user A returns 404 when user B tries to read it."""
    # Create user B in the same org.
    user_b = User(
        email="userb@test.com",
        full_name="User B",
        hashed_password=hash_password("pass123456"),
        is_active=True,
        organization_id=test_org.id,
        is_global_admin=False,
        role=UserRole.agent,
    )
    session.add(user_b)
    await session.commit()
    await session.refresh(user_b)

    # Notification belongs to test_user (user A).
    notif = await notification_service.create_notification(
        session=session,
        user_id=test_user.id,
        organization_id=test_org.id,
        type="lead_qualified",
        title="User A notif",
        body="body",
    )
    await session.commit()
    await session.refresh(notif)

    # Log in as user B.
    from app.core.security import create_access_token
    token_b = create_access_token({"sub": str(user_b.id)})
    client.cookies.set("access_token", token_b)

    response = await client.patch(f"{NOTIF_URL}/{notif.id}/read")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_notifications_paginated(
    client: AsyncClient,
    access_token: str,
    test_user: User,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """GET /notifications?limit=2 returns exactly 2 items when 5 exist."""
    for i in range(5):
        await _make_notification(session, test_user, test_org, title=f"P{i}")

    client.cookies.set("access_token", access_token)
    response = await client.get(f"{NOTIF_URL}?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_notifications_isolated_by_user(
    client: AsyncClient,
    test_user: User,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """User B's GET /notifications does not return user A's notifications."""
    # Create user B.
    user_b = User(
        email="isolated_b@test.com",
        full_name="Isolated B",
        hashed_password=hash_password("pass123456"),
        is_active=True,
        organization_id=test_org.id,
        is_global_admin=False,
        role=UserRole.agent,
    )
    session.add(user_b)
    await session.commit()
    await session.refresh(user_b)

    # Give test_user (A) a notification.
    await _make_notification(session, test_user, test_org, title="A's notif")

    from app.core.security import create_access_token
    token_b = create_access_token({"sub": str(user_b.id)})
    client.cookies.set("access_token", token_b)

    response = await client.get(NOTIF_URL)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_unread_count_excludes_read(
    client: AsyncClient,
    access_token: str,
    test_user: User,
    test_org: Organization,
    session: AsyncSession,
) -> None:
    """Unread count decreases after marking a notification as read."""
    # Create 2 notifications.
    notif = await notification_service.create_notification(
        session=session,
        user_id=test_user.id,
        organization_id=test_org.id,
        type="lead_qualified",
        title="First",
        body="body",
    )
    await _make_notification(session, test_user, test_org, title="Second")
    await session.refresh(notif)

    client.cookies.set("access_token", access_token)
    # Mark first as read.
    await client.patch(f"{NOTIF_URL}/{notif.id}/read")

    count_resp = await client.get(f"{NOTIF_URL}/unread-count")
    assert count_resp.json()["count"] == 1
