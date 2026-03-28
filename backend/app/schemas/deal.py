"""Pydantic schemas for Deal endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DealCreate(BaseModel):
    name: str
    contact_id: uuid.UUID
    stage_id: uuid.UUID
    pipeline_id: uuid.UUID
    value: Decimal | None = None
    currency: str = "USD"
    assigned_to: uuid.UUID | None = None
    expected_close_date: date | None = None
    notes: str | None = None
    custom_fields: dict = {}


class DealUpdate(BaseModel):
    name: str | None = None
    value: Decimal | None = None
    currency: str | None = None
    stage_id: uuid.UUID | None = None
    pipeline_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    expected_close_date: date | None = None
    notes: str | None = None
    custom_fields: dict | None = None


class DealRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    name: str
    value: Decimal | None
    currency: str
    contact_id: uuid.UUID
    stage_id: uuid.UUID
    pipeline_id: uuid.UUID
    assigned_to: uuid.UUID | None
    expected_close_date: date | None
    closed_at: datetime | None
    notes: str | None
    custom_fields: dict
