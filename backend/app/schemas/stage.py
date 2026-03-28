"""Pydantic schemas for Stage endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StageCreate(BaseModel):
    name: str
    order: int
    pipeline_id: uuid.UUID
    color: str | None = None
    probability: int = 0
    is_won: bool = False
    is_lost: bool = False


class StageUpdate(BaseModel):
    name: str | None = None
    order: int | None = None
    color: str | None = None
    probability: int | None = None
    is_won: bool | None = None
    is_lost: bool | None = None


class StageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    pipeline_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    name: str
    order: int
    color: str | None
    probability: int
    is_won: bool
    is_lost: bool
