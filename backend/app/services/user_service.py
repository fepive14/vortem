"""User service — CRUD for users within a tenant."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate

logger = get_logger(__name__)


async def create_user(
    session: AsyncSession,
    organization_id: uuid.UUID,
    data: UserCreate,
) -> User:
    """Create a new user scoped to organization_id. Flushes — caller commits."""
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
        timezone=data.timezone,
        is_active=True,
        organization_id=organization_id,
        is_global_admin=False,
    )
    session.add(user)
    await session.flush()
    logger.info("user_created", user_id=str(user.id), organization_id=str(organization_id))
    return user


async def list_users(
    session: AsyncSession,
    organization_id: uuid.UUID,
    role: UserRole | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[User]:
    """Return users in the org, optionally filtered by role."""
    q = select(User).where(User.organization_id == organization_id)
    if role is not None:
        q = q.where(User.role == role)
    q = q.order_by(User.created_at.asc()).offset(skip).limit(limit)
    result = await session.execute(q)
    return list(result.scalars().all())


async def get_user(
    session: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
) -> User | None:
    """Return a single user belonging to the org, or None."""
    result = await session.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def update_user(
    session: AsyncSession,
    user: User,
    data: UserUpdate,
) -> User:
    """Apply only the fields explicitly set in data. Flushes — caller commits."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await session.flush()
    return user


async def deactivate_user(session: AsyncSession, user: User) -> User:
    """Soft-delete: set is_active=False. Flushes — caller commits."""
    user.is_active = False
    await session.flush()
    logger.info("user_deactivated", user_id=str(user.id))
    return user
