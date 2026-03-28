"""Pydantic schemas for Lead endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.lead import LeadSource, LeadStatus


class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str | None = None
    email: str | None = None
    country: str | None = None
    source: LeadSource = LeadSource.manual
    campaign_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    voicehire_data: dict = {}


class LeadUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    country: str | None = None
    status: LeadStatus | None = None
    source: LeadSource | None = None
    campaign_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    voicehire_data: dict | None = None


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    first_name: str
    last_name: str
    phone: str | None
    email: str | None
    country: str | None
    status: LeadStatus
    source: LeadSource
    campaign_id: uuid.UUID | None
    assigned_to: uuid.UUID | None
    voicehire_data: dict
