"""Stage model — a single column in a Pipeline."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Stage(Base):
    __tablename__ = "stages"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str | None] = mapped_column(Text, nullable=True)
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_won: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        # No two stages may share the same position in the same pipeline.
        UniqueConstraint("pipeline_id", "order", name="uq_stages_pipeline_order"),
    )

    def __repr__(self) -> str:
        return f"<Stage id={self.id} name={self.name!r} order={self.order}>"
