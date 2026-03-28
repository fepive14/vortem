"""Pydantic schemas for Organization endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrganizationResponse(BaseModel):
    """Public representation of an organization."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    logo_url: str | None
    is_active: bool
    settings: dict
    parent_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
