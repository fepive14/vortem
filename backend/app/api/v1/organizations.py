"""Organization management endpoints — global admin only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.middleware.auth import require_auth
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationResponse, SetOrgVerticalRequest

router = APIRouter()


@router.patch(
    "/{org_id}/vertical",
    response_model=OrganizationResponse,
    summary="Set the vertical for an organization",
    description="Only global admins can change an organization's vertical.",
)
async def set_org_vertical(
    org_id: uuid.UUID,
    body: SetOrgVerticalRequest,
    current_user: User = Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> OrganizationResponse:
    if not current_user.is_global_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only global admins can modify an organization's vertical.",
        )
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )
    org.vertical = body.vertical
    await session.commit()
    await session.refresh(org)
    return OrganizationResponse.model_validate(org)
