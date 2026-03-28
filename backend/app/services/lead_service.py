"""Lead service — business logic for lead CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate

logger = get_logger(__name__)


async def create_lead(
    session: AsyncSession,
    organization_id: uuid.UUID,
    data: LeadCreate,
) -> Lead:
    """Create a new Lead scoped to organization_id.

    Flushes but does NOT commit — the caller (endpoint) commits and then
    publishes the LEAD_CREATED event.
    """
    lead = Lead(
        organization_id=organization_id,
        **data.model_dump(),
    )
    session.add(lead)
    await session.flush()

    logger.info(
        "lead_created",
        lead_id=str(lead.id),
        organization_id=str(organization_id),
    )
    return lead


async def list_leads(
    session: AsyncSession,
    organization_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Lead]:
    """Return leads for the given org, newest first."""
    result = await session.execute(
        select(Lead)
        .where(Lead.organization_id == organization_id)
        .order_by(Lead.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_lead(
    session: AsyncSession,
    organization_id: uuid.UUID,
    lead_id: uuid.UUID,
) -> Lead | None:
    """Return a single Lead, or None if not found or belongs to a different org."""
    result = await session.execute(
        select(Lead).where(
            Lead.id == lead_id,
            Lead.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def update_lead(
    session: AsyncSession,
    lead: Lead,
    data: LeadUpdate,
) -> Lead:
    """Apply only the fields explicitly set in data.

    Flushes but does NOT commit — the caller (endpoint) commits.
    """
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    await session.flush()
    return lead


async def delete_lead(session: AsyncSession, lead: Lead) -> None:
    """Hard-delete a lead.

    Flushes but does NOT commit — the caller (endpoint) commits.
    """
    await session.delete(lead)
    await session.flush()
