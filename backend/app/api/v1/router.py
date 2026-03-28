"""API v1 router — aggregates all v1 sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, contacts, deals, leads, pipelines, setup, stages

router = APIRouter(prefix="/api/v1")

router.include_router(setup.router, prefix="/setup", tags=["Setup"])
router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(contacts.router, prefix="/contacts", tags=["Contacts"])
router.include_router(leads.router, prefix="/leads", tags=["Leads"])
router.include_router(pipelines.router, prefix="/pipelines", tags=["Pipelines"])
router.include_router(stages.router, prefix="/stages", tags=["Stages"])
router.include_router(deals.router, prefix="/deals", tags=["Deals"])
