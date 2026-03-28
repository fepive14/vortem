"""Conversion service — converts a Lead into a Contact (and optionally a Deal)."""

from __future__ import annotations

import json
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.activity import Activity, ActivityType
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.lead import Lead, LeadStatus

logger = get_logger(__name__)


async def convert_lead(
    session: AsyncSession,
    organization_id: uuid.UUID,
    lead_id: uuid.UUID,
    assigned_to: uuid.UUID | None = None,
    create_deal: bool = False,
    deal_name: str | None = None,
    stage_id: uuid.UUID | None = None,
    pipeline_id: uuid.UUID | None = None,
    value: float | None = None,
    currency: str = "USD",
) -> tuple[Contact, Deal | None]:
    """Convert a lead into a contact (and optionally a deal).

    All DB mutations happen in a single flush. The caller (endpoint) commits
    and then publishes LEAD_CONVERTED.

    Returns:
        (contact, deal_or_none)

    Raises:
        HTTPException 404: Lead not found.
        HTTPException 400: Lead already converted.
    """
    # 1. Fetch lead — must belong to the caller's org.
    result = await session.execute(
        select(Lead).where(Lead.id == lead_id, Lead.organization_id == organization_id)
    )
    lead: Lead | None = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    # 2. Guard against double-conversion.
    if lead.status == LeadStatus.converted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lead already converted.",
        )

    # 3. Create Contact from lead fields.
    #    Generate UUID explicitly so contact.id is available before flush.
    effective_assigned_to = assigned_to or lead.assigned_to
    contact_id = uuid.uuid4()
    contact = Contact(
        id=contact_id,
        organization_id=organization_id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        phone=lead.phone,
        email=lead.email,
        country=lead.country,
        lead_id=lead.id,
        assigned_to=effective_assigned_to,
    )
    session.add(contact)

    # 4. Persist voicehire_data as an Activity if present.
    if lead.voicehire_data:
        activity = Activity(
            organization_id=organization_id,
            type=ActivityType.voicehire_call,
            lead_id=lead.id,
            body=json.dumps(lead.voicehire_data),
            assigned_to=effective_assigned_to,
        )
        session.add(activity)

    # 5. Mark lead as converted.
    lead.status = LeadStatus.converted

    # 6. Optionally create a Deal.
    deal: Deal | None = None
    if create_deal and stage_id is not None and pipeline_id is not None:
        name = deal_name or f"Deal — {contact.first_name} {contact.last_name}"
        deal = Deal(
            organization_id=organization_id,
            name=name,
            contact_id=contact_id,   # Uses the explicitly generated UUID.
            stage_id=stage_id,
            pipeline_id=pipeline_id,
            value=value,
            currency=currency,
        )
        session.add(deal)

    # 7. Single flush to persist all objects.
    await session.flush()

    logger.info(
        "lead_converted",
        lead_id=str(lead_id),
        contact_id=str(contact.id),
        deal_id=str(deal.id) if deal else None,
        organization_id=str(organization_id),
    )
    return contact, deal
