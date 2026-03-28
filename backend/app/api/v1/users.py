"""User management endpoints — admin CRUD for org users."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.middleware.auth import get_current_org_id, require_roles
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter()


@router.get(
    "",
    response_model=list[UserRead],
    summary="List users in the current org",
)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    role: UserRole | None = Query(default=None),
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_session),
) -> list[UserRead]:
    org_id = get_current_org_id(current_user)
    users = await user_service.list_users(session, org_id, role=role, skip=skip, limit=limit)
    return [UserRead.model_validate(u) for u in users]


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get a single user in the current org",
)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    org_id = get_current_org_id(current_user)
    user = await user_service.get_user(session, org_id, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserRead.model_validate(user)


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user in the current org",
)
async def create_user(
    body: UserCreate,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    if body.is_global_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create global admin users via this endpoint.",
        )
    org_id = get_current_org_id(current_user)
    user = await user_service.create_user(session, org_id, body)
    await session.commit()
    await session.refresh(user)
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update a user in the current org",
)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    org_id = get_current_org_id(current_user)
    user = await user_service.get_user(session, org_id, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    updated = await user_service.update_user(session, user, body)
    await session.commit()
    await session.refresh(updated)
    return UserRead.model_validate(updated)


@router.delete(
    "/{user_id}",
    response_model=UserRead,
    summary="Soft-delete a user (set is_active=False)",
)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.admin)),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account.",
        )
    org_id = get_current_org_id(current_user)
    user = await user_service.get_user(session, org_id, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    deactivated = await user_service.deactivate_user(session, user)
    await session.commit()
    await session.refresh(deactivated)
    return UserRead.model_validate(deactivated)
