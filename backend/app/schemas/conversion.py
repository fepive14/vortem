"""Pydantic schemas for the lead → contact conversion endpoint."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.schemas.contact import ContactRead
from app.schemas.deal import DealRead


class ConvertLeadRequest(BaseModel):
    assigned_to: uuid.UUID | None = None
    create_deal: bool = False
    deal_name: str | None = None
    stage_id: uuid.UUID | None = None
    pipeline_id: uuid.UUID | None = None
    value: float | None = None
    currency: str = "USD"


class ConvertLeadResponse(BaseModel):
    contact: ContactRead
    deal: DealRead | None
