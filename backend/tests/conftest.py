"""Shared pytest fixtures for the Vortem test suite."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.db.session import get_session
from app.main import app as _app
from app.models.base import Base
from app.models.organization import Organization
from app.models.user import User, UserRole

# ─── Test engine ──────────────────────────────────────────────────────────────
# NullPool prevents connections from being reused across coroutines, which
# avoids subtle "connection already used in another task" failures in tests.

_TEST_ENGINE = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

_TestSession = async_sessionmaker(
    bind=_TEST_ENGINE,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
)


# ─── Schema management ────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables() -> AsyncGenerator[None, None]:
    """Create schema once for the whole test session, then drop everything."""
    async with _TEST_ENGINE.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        # Create the user_role enum if it doesn't exist (mirrors the migration)
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
                    CREATE TYPE user_role AS ENUM ('admin', 'supervisor', 'agent', 'viewer');
                END IF;
            END $$;
        """))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


@pytest_asyncio.fixture(autouse=True)
async def clean_tables() -> AsyncGenerator[None, None]:
    """Truncate all data tables after every test to ensure isolation."""
    yield
    async with _TEST_ENGINE.begin() as conn:
        # Truncate in dependency order (events first, then users, then orgs).
        await conn.execute(text("TRUNCATE TABLE events, users, organizations RESTART IDENTITY CASCADE"))


# ─── Session fixture ──────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def session() -> AsyncGenerator[AsyncSession, None]:
    """An open AsyncSession backed by the test engine."""
    async with _TestSession() as sess:
        yield sess


# ─── HTTP client fixture ──────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client with the DB session dependency overridden.

    Uses the same session as the test so that objects created in fixtures are
    visible to the endpoint without needing an extra commit.
    """

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    _app.dependency_overrides[get_session] = _override_get_session

    async with LifespanManager(_app):
        async with AsyncClient(
            transport=ASGITransport(app=_app),
            base_url="http://test",
        ) as ac:
            yield ac

    _app.dependency_overrides.clear()


# ─── Domain fixtures ──────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def test_org(session: AsyncSession) -> Organization:
    """A persisted Organization available for the current test."""
    org = Organization(name="Test Org")
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return org


@pytest_asyncio.fixture()
async def test_user(session: AsyncSession, test_org: Organization) -> User:
    """A persisted, active admin user belonging to test_org."""
    user = User(
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("testpassword123"),
        is_active=True,
        organization_id=test_org.id,
        is_global_admin=False,
        role=UserRole.admin,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def test_global_admin(session: AsyncSession) -> User:
    """A persisted global admin (no org affiliation)."""
    user = User(
        email="globaladmin@test.com",
        full_name="Global Admin",
        hashed_password=hash_password("globalpass123"),
        is_active=True,
        organization_id=None,
        is_global_admin=True,
        role=UserRole.admin,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture()
def access_token(test_user: User) -> str:
    """A valid access token for test_user."""
    return create_access_token({"sub": str(test_user.id)})


@pytest.fixture()
def refresh_token_fixture(test_user: User) -> str:
    """A valid refresh token for test_user."""
    return create_refresh_token({"sub": str(test_user.id)})
