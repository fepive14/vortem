"""Authentication service — login, logout, token refresh."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User

logger = get_logger(__name__)

_AUTH_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect email or password.",
)


async def authenticate(
    session: AsyncSession,
    email: str,
    password: str,
) -> tuple[User, str, str]:
    """Verify credentials and return the user plus a fresh token pair.

    Returns:
        Tuple of (user, access_token, refresh_token).

    Raises:
        HTTPException 401: on invalid email or password.
        HTTPException 403: if the account is inactive.
    """
    result = await session.execute(select(User).where(User.email == email))
    user: User | None = result.scalar_one_or_none()

    # Use a constant-time comparison path even on "user not found" to avoid
    # user-enumeration via timing differences.
    # A valid, complete bcrypt hash (60 chars). Used only to keep the timing
    # of "user not found" identical to "wrong password" — prevents user enumeration.
    dummy_hash = "$2b$12$yNjLsGDEUrs9f3ptBV7g3O60I36FDYXM4HCwl.HDAaJHnA6Buit5m"
    if user is None:
        verify_password(password, dummy_hash)
        raise _AUTH_EXCEPTION

    if not verify_password(password, user.hashed_password):
        raise _AUTH_EXCEPTION

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    # Invariant: non-global users must belong to an organization.
    if not user.is_global_admin and user.organization_id is None:
        logger.error(
            "login_user_missing_organization",
            user_id=str(user.id),
            email=user.email,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has no associated organization.",
        )

    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.info("user_authenticated", user_id=str(user.id), email=user.email)
    return user, access_token, refresh_token


async def refresh_tokens(
    session: AsyncSession,
    refresh_token: str,
) -> tuple[User, str, str]:
    """Validate a refresh token and issue a new token pair (rotation).

    Args:
        session:       Open AsyncSession.
        refresh_token: The current refresh token (from cookie).

    Returns:
        Tuple of (user, new_access_token, new_refresh_token).

    Raises:
        HTTPException 401: if the token is invalid, expired, or not a refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
    )

    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise credentials_exception

    if payload.get("token_type") != "refresh":
        raise credentials_exception

    user_id_raw: str | None = payload.get("sub")  # type: ignore[assignment]
    if user_id_raw is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_raw)
    except ValueError:
        raise credentials_exception

    result = await session.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    token_data = {"sub": str(user.id)}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    logger.info("tokens_refreshed", user_id=str(user.id))
    return user, new_access, new_refresh
