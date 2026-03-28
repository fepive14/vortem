"""Bootstrap endpoint — initializes a fresh Vortem instance."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.events.catalog import EventType
from app.events.publisher import publish
from app.schemas.user import UserResponse
from app.services.setup_service import SetupRequest, bootstrap, is_already_initialized

router = APIRouter()


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bootstrap the instance",
    description=(
        "Creates the first organization and global admin user. "
        "Returns 403 if the instance has already been initialized."
    ),
)
async def setup(
    body: SetupRequest,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    if await is_already_initialized(session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instance is already initialized.",
        )

    user = await bootstrap(session, body)
    await session.commit()

    # Publish after commit — the business data is durable before notifying.
    await publish(
        session,
        event_type=EventType.INSTANCE_INITIALIZED,
        payload={"user_id": str(user.id), "email": user.email},
    )

    return UserResponse.model_validate(user)
