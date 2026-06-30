"""Supervisor endpoints — lead assignment queue."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.events.catalog import EventType
from app.events.publisher import publish
from app.middleware.auth import get_current_org_id, require_roles
from app.models.user import User, UserRole
from app.schemas.lead import LeadAssignRequest, LeadRead
from app.services import lead_service, supervisor_service

router = APIRouter()


@router.get(
    "/leads/queue",
    response_model=list[LeadRead],
    summary="Qualified unassigned lead queue",
)
async def get_lead_queue(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> list[LeadRead]:
    org_id = get_current_org_id(current_user)
    leads = await supervisor_service.list_qualified_unassigned(
        session, org_id, skip=skip, limit=limit
    )
    return [LeadRead.model_validate(l) for l in leads]


@router.patch(
    "/leads/{lead_id}/assign",
    response_model=LeadRead,
    summary="Assign a lead to an agent",
)
async def assign_lead(
    lead_id: uuid.UUID,
    body: LeadAssignRequest,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> LeadRead:
    org_id = get_current_org_id(current_user)
    lead = await lead_service.get_lead(session, org_id, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    updated = await supervisor_service.assign_lead(session, lead, body.assigned_to, organization_id=org_id)
    await publish(
        session,
        event_type=EventType.LEAD_ASSIGNED,
        payload={"lead_id": str(lead_id), "assigned_to": str(body.assigned_to)},
        organization_id=org_id,
        user_id=current_user.id,
    )
    await session.commit()
    await session.refresh(updated)
    return LeadRead.model_validate(updated)
