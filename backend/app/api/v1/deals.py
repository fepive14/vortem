"""Deal endpoints — CRUD for the deals resource."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.events.catalog import EventType
from app.events.publisher import publish
from app.middleware.auth import get_current_org_id, require_auth, require_roles
from app.models.user import User, UserRole
from app.schemas.deal import DealCreate, DealRead, DealUpdate
from app.services import deal_service

router = APIRouter()


@router.post(
    "",
    response_model=DealRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create deal",
)
async def create_deal(
    body: DealCreate,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DealRead:
    org_id = get_current_org_id(current_user)
    deal = await deal_service.create_deal(session, org_id, body)
    await publish(
        session,
        event_type=EventType.DEAL_CREATED,
        payload={"deal_id": str(deal.id)},
        organization_id=org_id,
        user_id=current_user.id,
    )
    await session.commit()
    return DealRead.model_validate(deal)


@router.get(
    "",
    response_model=list[DealRead],
    summary="List deals",
)
async def list_deals(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[DealRead]:
    org_id = get_current_org_id(current_user)
    deals = await deal_service.list_deals(session, org_id, skip=skip, limit=limit)
    return [DealRead.model_validate(d) for d in deals]


@router.get(
    "/{deal_id}",
    response_model=DealRead,
    summary="Get deal",
)
async def get_deal(
    deal_id: uuid.UUID,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> DealRead:
    org_id = get_current_org_id(current_user)
    deal = await deal_service.get_deal(session, org_id, deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found.")
    return DealRead.model_validate(deal)


@router.patch(
    "/{deal_id}",
    response_model=DealRead,
    summary="Update deal",
)
async def update_deal(
    deal_id: uuid.UUID,
    body: DealUpdate,
    current_user: User = Depends(
        require_roles(UserRole.admin, UserRole.supervisor, UserRole.agent)
    ),
    session: AsyncSession = Depends(get_session),
) -> DealRead:
    org_id = get_current_org_id(current_user)
    deal = await deal_service.get_deal(session, org_id, deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found.")

    old_stage_id = deal.stage_id
    updated = await deal_service.update_deal(session, deal, body, organization_id=org_id)
    # updated.stage_id is available in memory after flush() in update_deal.
    if body.stage_id is not None and updated.stage_id != old_stage_id:
        await publish(
            session,
            event_type=EventType.DEAL_STAGE_CHANGED,
            payload={
                "deal_id": str(updated.id),
                "old_stage_id": str(old_stage_id),
                "new_stage_id": str(updated.stage_id),
            },
            organization_id=org_id,
            user_id=current_user.id,
        )
    await session.commit()
    await session.refresh(updated)
    return DealRead.model_validate(updated)


@router.delete(
    "/{deal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete deal",
)
async def delete_deal(
    deal_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> None:
    org_id = get_current_org_id(current_user)
    deal = await deal_service.get_deal(session, org_id, deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found.")
    await deal_service.delete_deal(session, deal)
    await session.commit()
