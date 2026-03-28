"""Authentication endpoints — login, logout, refresh, me."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.middleware.auth import require_auth
from app.models.user import User
from app.schemas.user import AuthResponse, LoginRequest, UserResponse
from app.services import auth_service

router = APIRouter()

_COOKIE_MAX_AGE_ACCESS = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
_COOKIE_MAX_AGE_REFRESH = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86_400


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Write both JWT tokens as httpOnly cookies."""
    secure = settings.is_production
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=_COOKIE_MAX_AGE_ACCESS,
        httponly=True,
        secure=secure,
        samesite="lax",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=_COOKIE_MAX_AGE_REFRESH,
        httponly=True,
        secure=secure,
        samesite="lax",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Delete both JWT cookies from the client."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login",
    description="Authenticate with email and password. Sets httpOnly JWT cookies.",
)
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    user, access_token, refresh_token = await auth_service.authenticate(
        session, body.email, body.password
    )
    _set_auth_cookies(response, access_token, refresh_token)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Clears the JWT cookies.",
)
async def logout(response: Response) -> None:
    _clear_auth_cookies(response)


@router.post(
    "/refresh",
    response_model=AuthResponse,
    summary="Refresh tokens",
    description="Rotate the token pair using the refresh_token cookie.",
)
async def refresh(
    response: Response,
    session: AsyncSession = Depends(get_session),
    refresh_token: str | None = Cookie(default=None),
) -> AuthResponse:
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not provided.",
        )

    user, new_access, new_refresh = await auth_service.refresh_tokens(
        session, refresh_token
    )
    _set_auth_cookies(response, new_access, new_refresh)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current user",
    description="Returns the authenticated user's profile.",
)
async def me(current_user: User = Depends(require_auth)) -> UserResponse:
    return UserResponse.model_validate(current_user)
