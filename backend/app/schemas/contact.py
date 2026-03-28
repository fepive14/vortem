"""Pydantic schemas for Contact endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.contact import ContactStatus


class ContactCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str | None = None
    email: str | None = None
    company: str | None = None
    position: str | None = None
    country: str | None = None
    assigned_to: uuid.UUID | None = None
    tags: list = []
    custom_fields: dict = {}


class ContactUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    company: str | None = None
    position: str | None = None
    country: str | None = None
    status: ContactStatus | None = None
    lead_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    tags: list | None = None
    custom_fields: dict | None = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    first_name: str
    last_name: str
    phone: str | None
    email: str | None
    company: str | None
    position: str | None
    country: str | None
    status: ContactStatus
    lead_id: uuid.UUID | None
    assigned_to: uuid.UUID | None
    tags: list
    custom_fields: dict
