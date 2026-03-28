"""Pipeline service — business logic for pipeline CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.pipeline import Pipeline
from app.schemas.pipeline import PipelineCreate, PipelineUpdate

logger = get_logger(__name__)


async def create_pipeline(
    session: AsyncSession,
    organization_id: uuid.UUID,
    data: PipelineCreate,
) -> Pipeline:
    """Create a pipeline scoped to organization_id. Flushes; endpoint commits."""
    pipeline = Pipeline(organization_id=organization_id, **data.model_dump())
    session.add(pipeline)
    await session.flush()
    logger.info("pipeline_created", pipeline_id=str(pipeline.id), organization_id=str(organization_id))
    return pipeline


async def list_pipelines(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> list[Pipeline]:
    result = await session.execute(
        select(Pipeline)
        .where(Pipeline.organization_id == organization_id)
        .order_by(Pipeline.created_at.desc())
    )
    return list(result.scalars().all())


async def get_pipeline(
    session: AsyncSession,
    organization_id: uuid.UUID,
    pipeline_id: uuid.UUID,
) -> Pipeline | None:
    result = await session.execute(
        select(Pipeline).where(
            Pipeline.id == pipeline_id,
            Pipeline.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def update_pipeline(
    session: AsyncSession,
    pipeline: Pipeline,
    data: PipelineUpdate,
) -> Pipeline:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pipeline, field, value)
    await session.flush()
    return pipeline


async def delete_pipeline(session: AsyncSession, pipeline: Pipeline) -> None:
    await session.delete(pipeline)
    await session.flush()
