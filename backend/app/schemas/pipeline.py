"""Pydantic schemas for Pipeline endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PipelineCreate(BaseModel):
    name: str
    description: str | None = None
    is_default: bool = False


class PipelineUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_default: bool | None = None


class PipelineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    name: str
    description: str | None
    is_default: bool
