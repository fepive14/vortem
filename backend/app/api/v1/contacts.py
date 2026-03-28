"""Contact endpoints — CRUD for the contacts resource."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.events.catalog import EventType
from app.events.publisher import publish
from app.middleware.auth import get_current_org_id, require_auth, require_roles
from app.models.user import User, UserRole
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate
from app.services import contact_service

router = APIRouter()


@router.post(
    "",
    response_model=ContactRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create contact",
)
async def create_contact(
    body: ContactCreate,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> ContactRead:
    org_id = get_current_org_id(current_user)
    contact = await contact_service.create_contact(session, org_id, body)
    await session.commit()
    await publish(
        session,
        event_type=EventType.CONTACT_CREATED,
        payload={"contact_id": str(contact.id)},
        organization_id=org_id,
        user_id=current_user.id,
    )
    return ContactRead.model_validate(contact)


@router.get(
    "",
    response_model=list[ContactRead],
    summary="List contacts",
)
async def list_contacts(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[ContactRead]:
    org_id = get_current_org_id(current_user)
    contacts = await contact_service.list_contacts(session, org_id, skip=skip, limit=limit)
    return [ContactRead.model_validate(c) for c in contacts]


@router.get(
    "/{contact_id}",
    response_model=ContactRead,
    summary="Get contact",
)
async def get_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> ContactRead:
    org_id = get_current_org_id(current_user)
    contact = await contact_service.get_contact(session, org_id, contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found.")
    return ContactRead.model_validate(contact)


@router.patch(
    "/{contact_id}",
    response_model=ContactRead,
    summary="Update contact",
)
async def update_contact(
    contact_id: uuid.UUID,
    body: ContactUpdate,
    current_user: User = Depends(
        require_roles(UserRole.admin, UserRole.supervisor, UserRole.agent)
    ),
    session: AsyncSession = Depends(get_session),
) -> ContactRead:
    org_id = get_current_org_id(current_user)
    contact = await contact_service.get_contact(session, org_id, contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found.")
    updated = await contact_service.update_contact(session, contact, body)
    await session.commit()
    await session.refresh(updated)
    return ContactRead.model_validate(updated)


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete contact",
)
async def delete_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> None:
    org_id = get_current_org_id(current_user)
    contact = await contact_service.get_contact(session, org_id, contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found.")
    await contact_service.delete_contact(session, contact)
    await session.commit()
