"""Contact service — business logic for contact CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate

logger = get_logger(__name__)


async def create_contact(
    session: AsyncSession,
    organization_id: uuid.UUID,
    data: ContactCreate,
) -> Contact:
    """Create a new Contact scoped to organization_id.

    Flushes but does NOT commit — the caller (endpoint) commits and then
    publishes the CONTACT_CREATED event.
    """
    contact = Contact(
        organization_id=organization_id,
        **data.model_dump(),
    )
    session.add(contact)
    await session.flush()

    logger.info(
        "contact_created",
        contact_id=str(contact.id),
        organization_id=str(organization_id),
    )
    return contact


async def list_contacts(
    session: AsyncSession,
    organization_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Contact]:
    """Return contacts for the given org, newest first."""
    result = await session.execute(
        select(Contact)
        .where(Contact.organization_id == organization_id)
        .order_by(Contact.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_contact(
    session: AsyncSession,
    organization_id: uuid.UUID,
    contact_id: uuid.UUID,
) -> Contact | None:
    """Return a single Contact, or None if not found or belongs to a different org."""
    result = await session.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def update_contact(
    session: AsyncSession,
    contact: Contact,
    data: ContactUpdate,
) -> Contact:
    """Apply only the fields explicitly set in data.

    Flushes but does NOT commit — the caller (endpoint) commits.
    """
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    await session.flush()
    return contact


async def delete_contact(session: AsyncSession, contact: Contact) -> None:
    """Hard-delete a contact.

    Flushes but does NOT commit — the caller (endpoint) commits.
    """
    await session.delete(contact)
    await session.flush()
