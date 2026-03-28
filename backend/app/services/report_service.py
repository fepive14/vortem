"""Report service — aggregate queries for CRM analytics."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.lead import Lead, LeadStatus


async def lead_funnel(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> dict[str, int]:
    """Return lead counts keyed by status for the given org."""
    result = await session.execute(
        select(Lead.status, func.count(Lead.id))
        .where(Lead.organization_id == organization_id)
        .group_by(Lead.status)
    )
    counts: dict[str, int] = {s.value: 0 for s in LeadStatus}
    for row in result.all():
        counts[row[0].value] = row[1]
    return counts


async def agent_performance(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> list[dict]:
    """Return per-agent activity counts and conversion counts."""
    activity_result = await session.execute(
        select(Activity.assigned_to, func.count(Activity.id))
        .where(
            Activity.organization_id == organization_id,
            Activity.assigned_to.is_not(None),
        )
        .group_by(Activity.assigned_to)
    )
    activity_counts: dict[str, int] = {
        str(row[0]): row[1] for row in activity_result.all()
    }

    conv_result = await session.execute(
        select(Lead.assigned_to, func.count(Lead.id))
        .where(
            Lead.organization_id == organization_id,
            Lead.status == LeadStatus.converted,
            Lead.assigned_to.is_not(None),
        )
        .group_by(Lead.assigned_to)
    )
    conv_counts: dict[str, int] = {
        str(row[0]): row[1] for row in conv_result.all()
    }

    all_agents = set(activity_counts.keys()) | set(conv_counts.keys())
    return [
        {
            "agent_id": agent_id,
            "activities": activity_counts.get(agent_id, 0),
            "conversions": conv_counts.get(agent_id, 0),
        }
        for agent_id in sorted(all_agents)
    ]


async def activity_by_campaign(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> list[dict]:
    """Return lead counts per campaign_id for the given org."""
    result = await session.execute(
        select(Lead.campaign_id, func.count(Lead.id))
        .where(
            Lead.organization_id == organization_id,
            Lead.campaign_id.is_not(None),
        )
        .group_by(Lead.campaign_id)
    )
    return [
        {"campaign_id": str(row[0]), "count": row[1]}
        for row in result.all()
    ]
