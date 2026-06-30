"""Deal service — business logic for deal CRUD."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.pipeline import Pipeline
from app.models.stage import Stage
from app.models.user import User
from app.schemas.deal import DealCreate, DealUpdate

logger = get_logger(__name__)


async def _check_org_fk(
    session: AsyncSession,
    model: type,
    resource_id: uuid.UUID,
    organization_id: uuid.UUID,
    field_name: str,
) -> None:
    """Raise 400 if resource_id does not belong to organization_id. [H-017]"""
    result = await session.execute(
        select(model).where(
            model.id == resource_id,
            model.organization_id == organization_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name}: resource not found in this organization.",
        )


async def create_deal(
    session: AsyncSession,
    organization_id: uuid.UUID,
    data: DealCreate,
) -> Deal:
    """Create a deal scoped to organization_id. Flushes; endpoint commits."""
    await _check_org_fk(session, Contact, data.contact_id, organization_id, "contact_id")
    await _check_org_fk(session, Pipeline, data.pipeline_id, organization_id, "pipeline_id")
    await _check_org_fk(session, Stage, data.stage_id, organization_id, "stage_id")

    if data.assigned_to is not None:
        res = await session.execute(
            select(User).where(
                User.id == data.assigned_to,
                User.organization_id == organization_id,
                User.is_active.is_(True),
            )
        )
        if res.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="assigned_to: user not found in this organization.",
            )

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
    organization_id: uuid.UUID | None = None,
) -> Deal:
    """Apply only the fields explicitly set in data. Flushes; endpoint commits.

    Pass organization_id to validate cross-org FKs. [H-016, H-017]
    The endpoint is responsible for detecting stage_id changes and publishing
    DEAL_STAGE_CHANGED after commit.
    """
    if organization_id is not None:
        if data.stage_id is not None:
            await _check_org_fk(session, Stage, data.stage_id, organization_id, "stage_id")
        if data.pipeline_id is not None:
            await _check_org_fk(session, Pipeline, data.pipeline_id, organization_id, "pipeline_id")
        if data.assigned_to is not None:
            res = await session.execute(
                select(User).where(
                    User.id == data.assigned_to,
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
            )
            if res.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="assigned_to: user not found in this organization.",
                )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(deal, field, value)
    await session.flush()
    return deal


async def delete_deal(session: AsyncSession, deal: Deal) -> None:
    await session.delete(deal)
    await session.flush()
