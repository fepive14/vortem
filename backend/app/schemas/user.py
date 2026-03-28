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


# ─── User management schemas ──────────────────────────────────────────────────


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: UserRole = UserRole.agent
    timezone: str = "America/Bogota"
    # Present so the endpoint can explicitly reject global-admin creation.
    is_global_admin: bool = False


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    timezone: str | None = None
    avatar_url: str | None = None
    phone: str | None = None


class UserRead(BaseModel):
    """Public user profile — never exposes hashed_password."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    organization_id: uuid.UUID | None
    timezone: str
    avatar_url: str | None
    phone: str | None
    created_at: datetime
