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
from app.schemas.contact import ContactRead
from app.schemas.conversion import ConvertLeadRequest, ConvertLeadResponse
from app.schemas.deal import DealRead
from app.schemas.lead import LeadCreate, LeadRead, LeadUpdate
from app.services import conversion_service, lead_service

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


@router.post(
    "/{lead_id}/convert",
    response_model=ConvertLeadResponse,
    summary="Convert lead to contact",
    description=(
        "Converts a lead into a Contact. Optionally creates a Deal when "
        "create_deal=True and stage_id + pipeline_id are supplied. "
        "Returns 400 if the lead is already converted, 404 if not found."
    ),
)
async def convert_lead(
    lead_id: uuid.UUID,
    body: ConvertLeadRequest,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> ConvertLeadResponse:
    org_id = get_current_org_id(current_user)
    contact, deal = await conversion_service.convert_lead(
        session=session,
        organization_id=org_id,
        lead_id=lead_id,
        assigned_to=body.assigned_to,
        create_deal=body.create_deal,
        deal_name=body.deal_name,
        stage_id=body.stage_id,
        pipeline_id=body.pipeline_id,
        value=body.value,
        currency=body.currency,
    )
    await session.commit()
    await session.refresh(contact)
    if deal is not None:
        await session.refresh(deal)

    await publish(
        session,
        event_type=EventType.LEAD_CONVERTED,
        payload={"lead_id": str(lead_id), "contact_id": str(contact.id)},
        organization_id=org_id,
        user_id=current_user.id,
    )
    return ConvertLeadResponse(
        contact=ContactRead.model_validate(contact),
        deal=DealRead.model_validate(deal) if deal is not None else None,
    )
