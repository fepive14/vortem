"""Pipeline endpoints — CRUD for the pipelines resource."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.events.catalog import EventType
from app.events.publisher import publish
from app.middleware.auth import get_current_org_id, require_auth, require_roles
from app.models.user import User, UserRole
from app.schemas.pipeline import PipelineCreate, PipelineRead, PipelineUpdate
from app.services import pipeline_service

router = APIRouter()


@router.post(
    "",
    response_model=PipelineRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create pipeline",
)
async def create_pipeline(
    body: PipelineCreate,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> PipelineRead:
    org_id = get_current_org_id(current_user)
    pipeline = await pipeline_service.create_pipeline(session, org_id, body)
    await publish(
        session,
        event_type=EventType.PIPELINE_CREATED,
        payload={"pipeline_id": str(pipeline.id)},
        organization_id=org_id,
        user_id=current_user.id,
    )
    await session.commit()
    return PipelineRead.model_validate(pipeline)


@router.get(
    "",
    response_model=list[PipelineRead],
    summary="List pipelines",
)
async def list_pipelines(
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[PipelineRead]:
    org_id = get_current_org_id(current_user)
    pipelines = await pipeline_service.list_pipelines(session, org_id)
    return [PipelineRead.model_validate(p) for p in pipelines]


@router.get(
    "/{pipeline_id}",
    response_model=PipelineRead,
    summary="Get pipeline",
)
async def get_pipeline(
    pipeline_id: uuid.UUID,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> PipelineRead:
    org_id = get_current_org_id(current_user)
    pipeline = await pipeline_service.get_pipeline(session, org_id, pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found.")
    return PipelineRead.model_validate(pipeline)


@router.patch(
    "/{pipeline_id}",
    response_model=PipelineRead,
    summary="Update pipeline",
)
async def update_pipeline(
    pipeline_id: uuid.UUID,
    body: PipelineUpdate,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> PipelineRead:
    org_id = get_current_org_id(current_user)
    pipeline = await pipeline_service.get_pipeline(session, org_id, pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found.")
    updated = await pipeline_service.update_pipeline(session, pipeline, body)
    await session.commit()
    await session.refresh(updated)
    return PipelineRead.model_validate(updated)


@router.delete(
    "/{pipeline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete pipeline",
)
async def delete_pipeline(
    pipeline_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_session),
) -> None:
    org_id = get_current_org_id(current_user)
    pipeline = await pipeline_service.get_pipeline(session, org_id, pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found.")
    await pipeline_service.delete_pipeline(session, pipeline)
    await session.commit()
