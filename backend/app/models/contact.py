"""Contact model — person record within a tenant."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContactStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    do_not_contact = "do_not_contact"


class Contact(Base):
    __tablename__ = "contacts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ContactStatus] = mapped_column(
        SAEnum(ContactStatus, name="contact_status", create_type=False),
        nullable=False,
        default=ContactStatus.active,
    )

    # Optional link to a Lead record.
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    custom_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<Contact id={self.id} name={self.first_name!r} {self.last_name!r}>"
