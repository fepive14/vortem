"""Webhook service — processes inbound VoiceHire events."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.activity import Activity, ActivityType
from app.models.lead import Lead, LeadStatus
from app.schemas.webhook import VoiceHireWebhookPayload

logger = get_logger(__name__)

_VALID_STATUSES = {s.value for s in LeadStatus}


async def process_voicehire_event(
    session: AsyncSession,
    organization_id: uuid.UUID,
    payload: VoiceHireWebhookPayload,
) -> Lead:
    """Apply a VoiceHire event to the matching lead.

    Mutations (in order):
      1. Fetch lead — 404 if not found.
      2. Merge voicehire_data (dict update, not replace).
      3. Update lead.status if payload.status is a valid LeadStatus.
      4. Set campaign_id if payload provides one and the lead has none.
      5. Create an Activity of type voicehire_call.
      6. flush() — caller commits and publishes events.

    Returns the updated Lead.
    """
    result = await session.execute(
        select(Lead).where(
            Lead.id == payload.lead_id,
            Lead.organization_id == organization_id,
        )
    )
    lead: Lead | None = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    # Merge voicehire_data without losing existing keys.
    if payload.voicehire_data:
        merged = dict(lead.voicehire_data)
        merged.update(payload.voicehire_data)
        lead.voicehire_data = merged

    # Update status only when the provided value is a known enum member.
    if payload.status is not None and payload.status in _VALID_STATUSES:
        lead.status = LeadStatus(payload.status)

    # Set campaign_id only if not already set.
    if payload.campaign_id is not None and lead.campaign_id is None:
        lead.campaign_id = payload.campaign_id

    activity = Activity(
        organization_id=organization_id,
        type=ActivityType.voicehire_call,
        lead_id=lead.id,
        body=f"VoiceHire event: {payload.event}",
        metadata_=payload.voicehire_data,
    )
    session.add(activity)

    await session.flush()

    logger.info(
        "voicehire_event_processed",
        lead_id=str(lead.id),
        voicehire_event=payload.event,
        new_status=payload.status,
        organization_id=str(organization_id),
    )
    return lead
