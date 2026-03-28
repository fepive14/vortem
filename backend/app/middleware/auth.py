"""Authentication and authorization dependencies for FastAPI endpoints."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User, UserRole

logger = get_logger(__name__)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
)

_INACTIVE_USER_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Inactive user.",
)

_PERMISSION_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Insufficient permissions.",
)


# ─── Core auth dependency ─────────────────────────────────────────────────────


async def _get_current_user(
    session: AsyncSession = Depends(get_session),
    access_token: str | None = Cookie(default=None),
) -> User:
    """Decode the access token cookie and load the corresponding user.

    Injected automatically by require_auth and require_roles.
    Not intended to be used directly by endpoint functions.
    """
    if access_token is None:
        raise _CREDENTIALS_EXCEPTION

    try:
        payload = decode_token(access_token)
    except JWTError:
        raise _CREDENTIALS_EXCEPTION

    token_type: str | None = payload.get("token_type")  # type: ignore[assignment]
    if token_type != "access":
        raise _CREDENTIALS_EXCEPTION

    user_id_raw: str | None = payload.get("sub")  # type: ignore[assignment]
    if user_id_raw is None:
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(user_id_raw)
    except ValueError:
        raise _CREDENTIALS_EXCEPTION

    result = await session.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()

    if user is None:
        raise _CREDENTIALS_EXCEPTION

    if not user.is_active:
        raise _INACTIVE_USER_EXCEPTION

    # Invariant: non-global users must belong to an organization.
    # The DB constraint also enforces this, but we check here for an explicit 403.
    if not user.is_global_admin and user.organization_id is None:
        logger.warning(
            "user_missing_organization",
            user_id=str(user.id),
            email=user.email,
        )
        raise _PERMISSION_EXCEPTION

    return user


# ─── Public dependencies ──────────────────────────────────────────────────────


async def require_auth(
    user: User = Depends(_get_current_user),
) -> User:
    """Require any authenticated, active user.

    Usage::

        @router.get("/resource")
        async def endpoint(current_user: User = Depends(require_auth)):
            ...
    """
    return user


def require_roles(*roles: UserRole) -> Callable[..., Coroutine[Any, Any, User]]:
    """Factory that returns a dependency requiring one of the given roles.

    Global admins bypass all role checks.

    Usage::

        @router.delete("/resource")
        async def endpoint(current_user: User = Depends(require_roles(UserRole.admin))):
            ...
    """
    allowed = set(roles)

    async def _dependency(user: User = Depends(_get_current_user)) -> User:
        if user.is_global_admin:
            return user
        if user.role not in allowed:
            raise _PERMISSION_EXCEPTION
        return user

    return _dependency


def get_current_org_id(current_user: User) -> uuid.UUID:
    """Extract the organization_id from an authenticated user.

    Raises:
        HTTPException 403: if the user has no organization (should not happen
        after require_auth, but guards against misuse).

    Usage (inside a service or endpoint)::

        org_id = get_current_org_id(current_user)
        results = await session.execute(
            select(Lead).where(Lead.organization_id == org_id)
        )
    """
    if current_user.organization_id is None:
        # Global admins querying tenant data must specify org_id explicitly.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint requires an organization context.",
        )
    return current_user.organization_id
