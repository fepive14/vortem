"""Deal service — business logic for deal CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.deal import Deal
from app.schemas.deal import DealCreate, DealUpdate

logger = get_logger(__name__)


async def create_deal(
    session: AsyncSession,
    organization_id: uuid.UUID,
    data: DealCreate,
) -> Deal:
    """Create a deal scoped to organization_id. Flushes; endpoint commits."""
    deal = Deal(organization_id=organization_id, **data.model_dump())
    session.add(deal)
    await session.flush()
    logger.info("deal_created", deal_id=str(deal.id), organization_id=str(organization_id))
    return deal


async def list_deals(
    session: AsyncSession,
    organization_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Deal]:
    result = await session.execute(
        select(Deal)
        .where(Deal.organization_id == organization_id)
        .order_by(Deal.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_deal(
    session: AsyncSession,
    organization_id: uuid.UUID,
    deal_id: uuid.UUID,
) -> Deal | None:
    result = await session.execute(
        select(Deal).where(
            Deal.id == deal_id,
            Deal.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def update_deal(
    session: AsyncSession,
    deal: Deal,
    data: DealUpdate,
) -> Deal:
    """Apply only the fields explicitly set in data. Flushes; endpoint commits.

    The endpoint is responsible for detecting stage_id changes and publishing
    DEAL_STAGE_CHANGED after commit.
    """
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(deal, field, value)
    await session.flush()
    return deal


async def delete_deal(session: AsyncSession, deal: Deal) -> None:
    await session.delete(deal)
    await session.flush()
