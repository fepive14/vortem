"""Lead endpoints — CRUD for the leads resource."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.events.catalog import EventType
from app.events.publisher import publish
from app.middleware.auth import get_current_org_id, require_auth, require_roles
from app.models.user import User, UserRole
from app.schemas.lead import LeadCreate, LeadRead, LeadUpdate
from app.services import lead_service

router = APIRouter()


@router.post(
    "",
    response_model=LeadRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create lead",
)
async def create_lead(
    body: LeadCreate,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> LeadRead:
    org_id = get_current_org_id(current_user)
    lead = await lead_service.create_lead(session, org_id, body)
    await session.commit()
    await publish(
        session,
        event_type=EventType.LEAD_CREATED,
        payload={"lead_id": str(lead.id)},
        organization_id=org_id,
        user_id=current_user.id,
    )
    return LeadRead.model_validate(lead)


@router.get(
    "",
    response_model=list[LeadRead],
    summary="List leads",
)
async def list_leads(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[LeadRead]:
    org_id = get_current_org_id(current_user)
    leads = await lead_service.list_leads(session, org_id, skip=skip, limit=limit)
    return [LeadRead.model_validate(l) for l in leads]


@router.get(
    "/{lead_id}",
    response_model=LeadRead,
    summary="Get lead",
)
async def get_lead(
    lead_id: uuid.UUID,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> LeadRead:
    org_id = get_current_org_id(current_user)
    lead = await lead_service.get_lead(session, org_id, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    return LeadRead.model_validate(lead)


@router.patch(
    "/{lead_id}",
    response_model=LeadRead,
    summary="Update lead",
)
async def update_lead(
    lead_id: uuid.UUID,
    body: LeadUpdate,
    current_user: User = Depends(
        require_roles(UserRole.admin, UserRole.supervisor, UserRole.agent)
    ),
    session: AsyncSession = Depends(get_session),
) -> LeadRead:
    org_id = get_current_org_id(current_user)
    lead = await lead_service.get_lead(session, org_id, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    updated = await lead_service.update_lead(session, lead, body)
    await session.commit()
    await session.refresh(updated)
    return LeadRead.model_validate(updated)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lead",
)
async def delete_lead(
    lead_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> None:
    org_id = get_current_org_id(current_user)
    lead = await lead_service.get_lead(session, org_id, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    await lead_service.delete_lead(session, lead)
    await session.commit()
