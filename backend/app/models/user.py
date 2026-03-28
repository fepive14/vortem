"""User model — identity and access entity."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, CheckConstraint, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    supervisor = "supervisor"
    agent = "agent"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # True only for the platform super-admin; no org affiliation.
    is_global_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Explicit name ties the column to the existing 'user_role' PG enum created
    # by the migration; prevents SQLAlchemy from trying to CREATE TYPE on its own.
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", create_type=False),
        nullable=False,
    )

    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Required by the WFM module (Phase future).
    timezone: Mapped[str] = mapped_column(
        Text, nullable=False, default="America/Bogota"
    )

    # Relationships
    organization: Mapped["Organization | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organization",
        back_populates="users",
        lazy="raise",
    )

    # ─── Constraints ──────────────────────────────────────────────────────────
    __table_args__ = (
        # A non-global user MUST belong to an organization.
        # The invariant "global_admin => organization_id IS NULL" is enforced in
        # auth_service, not here, to keep DB logic minimal.
        CheckConstraint(
            "is_global_admin = TRUE OR organization_id IS NOT NULL",
            name="ck_users_org_or_global",
        ),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
