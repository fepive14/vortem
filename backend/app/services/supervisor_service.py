"""Supervisor service — lead queue and assignment."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.lead import Lead, LeadStatus

logger = get_logger(__name__)


async def list_qualified_unassigned(
    session: AsyncSession,
    organization_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Lead]:
    """Return qualified, unassigned leads ordered oldest-first (FIFO queue)."""
    result = await session.execute(
        select(Lead)
        .where(
            Lead.organization_id == organization_id,
            Lead.status == LeadStatus.qualified,
            Lead.assigned_to.is_(None),
        )
        .order_by(Lead.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def assign_lead(
    session: AsyncSession,
    lead: Lead,
    assigned_to: uuid.UUID,
) -> Lead:
    """Assign a lead to a user. Caller commits and publishes LEAD_ASSIGNED."""
    lead.assigned_to = assigned_to
    await session.flush()
    logger.info(
        "lead_assigned",
        lead_id=str(lead.id),
        assigned_to=str(assigned_to),
    )
    return lead
