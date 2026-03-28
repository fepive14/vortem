"""Stage endpoints — CRUD for the stages resource."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.middleware.auth import get_current_org_id, require_auth, require_roles
from app.models.user import User, UserRole
from app.schemas.stage import StageCreate, StageRead, StageUpdate
from app.services import stage_service

router = APIRouter()


@router.post(
    "",
    response_model=StageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create stage",
)
async def create_stage(
    body: StageCreate,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> StageRead:
    org_id = get_current_org_id(current_user)
    stage = await stage_service.create_stage(session, org_id, body)
    await session.commit()
    return StageRead.model_validate(stage)


@router.get(
    "",
    response_model=list[StageRead],
    summary="List stages for a pipeline",
)
async def list_stages(
    pipeline_id: uuid.UUID = Query(..., description="Filter stages by pipeline"),
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[StageRead]:
    stages = await stage_service.list_stages(session, pipeline_id)
    return [StageRead.model_validate(s) for s in stages]


@router.get(
    "/{stage_id}",
    response_model=StageRead,
    summary="Get stage",
)
async def get_stage(
    stage_id: uuid.UUID,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> StageRead:
    org_id = get_current_org_id(current_user)
    stage = await stage_service.get_stage(session, org_id, stage_id)
    if stage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found.")
    return StageRead.model_validate(stage)


@router.patch(
    "/{stage_id}",
    response_model=StageRead,
    summary="Update stage",
)
async def update_stage(
    stage_id: uuid.UUID,
    body: StageUpdate,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> StageRead:
    org_id = get_current_org_id(current_user)
    stage = await stage_service.get_stage(session, org_id, stage_id)
    if stage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found.")
    updated = await stage_service.update_stage(session, stage, body)
    await session.commit()
    await session.refresh(updated)
    return StageRead.model_validate(updated)


@router.delete(
    "/{stage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete stage",
)
async def delete_stage(
    stage_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_session),
) -> None:
    org_id = get_current_org_id(current_user)
    stage = await stage_service.get_stage(session, org_id, stage_id)
    if stage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found.")
    await stage_service.delete_stage(session, stage)
    await session.commit()
