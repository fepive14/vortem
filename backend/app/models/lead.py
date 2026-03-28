"""Lead model — inbound prospect record."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    converted = "converted"
    discarded = "discarded"


class LeadSource(str, enum.Enum):
    csv_import = "csv_import"
    manual = "manual"
    api = "api"
    voicehire = "voicehire"


class Lead(Base):
    __tablename__ = "leads"

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
    country: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus, name="lead_status", create_type=False),
        nullable=False,
        default=LeadStatus.new,
    )

    source: Mapped[LeadSource] = mapped_column(
        SAEnum(LeadSource, name="lead_source", create_type=False),
        nullable=False,
        default=LeadSource.manual,
    )

    # Plain UUID — no FK constraint; Pipeline module wires this in a future phase.
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    voicehire_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    def __repr__(self) -> str:
        return f"<Lead id={self.id} name={self.first_name!r} {self.last_name!r} status={self.status}>"
