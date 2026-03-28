"""Report endpoints — CRM analytics aggregates."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.middleware.auth import get_current_org_id, require_roles
from app.models.user import User, UserRole
from app.services import report_service

router = APIRouter()


@router.get(
    "/funnel",
    summary="Lead funnel — counts per status",
)
async def get_funnel(
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    org_id = get_current_org_id(current_user)
    return await report_service.lead_funnel(session, org_id)


@router.get(
    "/agent-performance",
    summary="Per-agent activity and conversion counts",
)
async def get_agent_performance(
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    org_id = get_current_org_id(current_user)
    return await report_service.agent_performance(session, org_id)


@router.get(
    "/activity-by-campaign",
    summary="Lead counts grouped by campaign",
)
async def get_activity_by_campaign(
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.supervisor)),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    org_id = get_current_org_id(current_user)
    return await report_service.activity_by_campaign(session, org_id)
