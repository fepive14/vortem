"""Bootstrap service — initializes the first organization and admin user."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.organization import Organization, OrgVertical
from app.models.user import User, UserRole

logger = get_logger(__name__)


class SetupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)
    org_name: str = Field(..., min_length=1)
    vertical: OrgVertical = OrgVertical.generic


async def is_already_initialized(session: AsyncSession) -> bool:
    """Return True if at least one user exists in the database."""
    result = await session.execute(select(func.count()).select_from(User))
    count: int = result.scalar_one()
    return count > 0


async def bootstrap(session: AsyncSession, request: SetupRequest) -> User:
    """Create the first Organization and a global admin User.

    This function assumes the caller has already verified that the instance is
    not yet initialized (i.e., no users exist).

    The session is NOT committed here — the caller (endpoint) is responsible
    for committing so that events can be published after the commit.

    Args:
        session: An open AsyncSession. Must NOT have an active transaction
                 from external code that should be rolled back on failure.
        request: Validated setup input.

    Returns:
        The newly created User (not yet committed to DB).
    """
    org = Organization(name=request.org_name, vertical=request.vertical)
    session.add(org)
    await session.flush()  # Assigns org.id

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        is_global_admin=True,
        organization_id=None,  # Global admin has no org affiliation.
        role=UserRole.admin,
    )
    session.add(user)
    await session.flush()  # Assigns user.id

    logger.info(
        "instance_bootstrapped",
        org_id=str(org.id),
        user_id=str(user.id),
        email=user.email,
    )
    return user
