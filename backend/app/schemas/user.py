"""Pydantic schemas for User endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


# ─── Input schemas ────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    """Used only when the refresh token is passed in the request body.
    The primary path reads the httpOnly cookie directly."""

    refresh_token: str


# ─── Output schemas ───────────────────────────────────────────────────────────


class UserResponse(BaseModel):
    """Public representation of a user — never includes hashed_password."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    organization_id: uuid.UUID | None
    is_global_admin: bool
    role: UserRole
    avatar_url: str | None
    phone: str | None
    timezone: str
    created_at: datetime
    updated_at: datetime


class AuthResponse(BaseModel):
    """Response body for login and refresh endpoints."""

    user: UserResponse
