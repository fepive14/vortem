"""Organization model — top-level tenant entity."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # FK to Pipeline — constraint is added by migration 0003 (ALTER TABLE).
    # Kept as plain UUID here to avoid a circular FK dependency between
    # organizations and pipelines during create_all in tests.
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Arbitrary tenant-level configuration blob.
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Self-referential hierarchy (parent org → child orgs).
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    parent: Mapped[Organization | None] = relationship(
        "Organization",
        remote_side="Organization.id",
        back_populates="children",
    )
    children: Mapped[list[Organization]] = relationship(
        "Organization",
        back_populates="parent",
    )
    users: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User",
        back_populates="organization",
        lazy="raise",  # Prevent accidental N+1 loads.
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} name={self.name!r}>"
