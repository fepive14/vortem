"""Pydantic schemas for inbound webhook payloads."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class VoiceHireWebhookPayload(BaseModel):
    lead_id: uuid.UUID
    event: str  # 'call_completed', 'lead_qualified', 'lead_discarded'
    status: str | None = None       # new lead status if changed
    voicehire_data: dict = {}       # transcription, buy signals, etc.
    campaign_id: uuid.UUID | None = None
