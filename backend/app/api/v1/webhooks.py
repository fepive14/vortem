"""Webhook endpoints — inbound events from external services."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.events.catalog import EventType
from app.events.publisher import publish
from app.models.lead import LeadStatus
from app.schemas.lead import LeadRead
from app.schemas.webhook import VoiceHireWebhookPayload
from app.services import webhook_service

router = APIRouter()


def _verify_voicehire_secret(
    x_voicehire_secret: str | None = Header(default=None),
) -> None:
    """Dependency — validates the shared secret header."""
    if x_voicehire_secret != settings.VOICEHIRE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing VoiceHire secret.",
        )


@router.post(
    "/voicehire/{organization_id}",
    response_model=LeadRead,
    summary="VoiceHire webhook",
    description=(
        "Inbound webhook called by VoiceHire. No JWT auth — "
        "authentication is via the X-VoiceHire-Secret header."
    ),
)
async def voicehire_webhook(
    organization_id: uuid.UUID,
    payload: VoiceHireWebhookPayload,
    _: None = Depends(_verify_voicehire_secret),
    session: AsyncSession = Depends(get_session),
) -> LeadRead:
    lead = await webhook_service.process_voicehire_event(
        session=session,
        organization_id=organization_id,
        payload=payload,
    )
    await session.commit()
    await session.refresh(lead)

    if lead.status == LeadStatus.qualified:
        await publish(
            session,
            event_type=EventType.LEAD_QUALIFIED,
            payload={"lead_id": str(lead.id)},
            organization_id=organization_id,
        )

    await publish(
        session,
        event_type=EventType.VOICEHIRE_CALL_COMPLETED,
        payload={"lead_id": str(lead.id), "event": payload.event},
        organization_id=organization_id,
    )

    return LeadRead.model_validate(lead)
