"""Stage service — business logic for stage CRUD."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.pipeline import Pipeline
from app.models.stage import Stage
from app.schemas.stage import StageCreate, StageUpdate

logger = get_logger(__name__)


async def create_stage(
    session: AsyncSession,
    organization_id: uuid.UUID,
    data: StageCreate,
) -> Stage:
    """Create a stage, validating that the pipeline belongs to the org."""
    pipeline_result = await session.execute(
        select(Pipeline).where(
            Pipeline.id == data.pipeline_id,
            Pipeline.organization_id == organization_id,
        )
    )
    if pipeline_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found.",
        )

    stage = Stage(
        organization_id=organization_id,
        pipeline_id=data.pipeline_id,
        name=data.name,
        order=data.order,
        color=data.color,
        probability=data.probability,
        is_won=data.is_won,
        is_lost=data.is_lost,
    )
    session.add(stage)
    await session.flush()
    logger.info("stage_created", stage_id=str(stage.id), pipeline_id=str(data.pipeline_id))
    return stage


async def list_stages(
    session: AsyncSession,
    organization_id: uuid.UUID,
    pipeline_id: uuid.UUID,
) -> list[Stage]:
    result = await session.execute(
        select(Stage)
        .where(
            Stage.pipeline_id == pipeline_id,
            Stage.organization_id == organization_id,
        )
        .order_by(Stage.order.asc())
    )
    return list(result.scalars().all())


async def get_stage(
    session: AsyncSession,
    organization_id: uuid.UUID,
    stage_id: uuid.UUID,
) -> Stage | None:
    result = await session.execute(
        select(Stage).where(
            Stage.id == stage_id,
            Stage.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def update_stage(
    session: AsyncSession,
    stage: Stage,
    data: StageUpdate,
) -> Stage:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(stage, field, value)
    await session.flush()
    return stage


async def delete_stage(session: AsyncSession, stage: Stage) -> None:
    await session.delete(stage)
    await session.flush()
