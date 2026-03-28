"""Cryptographic utilities: password hashing and JWT management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt cost factor 12 — good balance of security vs. latency (~300 ms on modern HW).
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Token type claim values
_ACCESS_TOKEN_TYPE = "access"
_REFRESH_TOKEN_TYPE = "refresh"


# ─── Password helpers ─────────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    """Return the bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ─── JWT helpers ──────────────────────────────────────────────────────────────


def create_access_token(data: dict[str, object]) -> str:
    """Create a signed access JWT valid for ACCESS_TOKEN_EXPIRE_MINUTES."""
    return _create_token(
        data,
        token_type=_ACCESS_TOKEN_TYPE,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(data: dict[str, object]) -> str:
    """Create a signed refresh JWT valid for REFRESH_TOKEN_EXPIRE_DAYS."""
    return _create_token(
        data,
        token_type=_REFRESH_TOKEN_TYPE,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, object]:
    """Decode and verify *token*.

    Raises:
        jose.JWTError: if the token is invalid, expired, or tampered.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


# ─── Internal helpers ─────────────────────────────────────────────────────────


def _create_token(
    data: dict[str, object],
    *,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        **data,
        "token_type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
