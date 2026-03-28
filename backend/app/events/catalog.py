"""Canonical event type constants.

All event types used anywhere in the application MUST be declared here.
This provides a single source of truth and prevents string typos.
"""


class EventType:
    # ─── Instance lifecycle ───────────────────────────────────────────────────
    INSTANCE_INITIALIZED = "instance.initialized"

    # ─── User activity (required by the WFM module — Phase future) ───────────
    USER_ACTIVITY_STARTED = "user.activity_started"
    USER_ACTIVITY_ENDED = "user.activity_ended"

    # ─── Auth ─────────────────────────────────────────────────────────────────
    USER_LOGGED_IN = "user.logged_in"
    USER_LOGGED_OUT = "user.logged_out"

    # ─── Contacts & Leads (Phase 1B) ─────────────────────────────────────────────
    CONTACT_CREATED = "contact.created"
    LEAD_CREATED = "lead.created"
    LEAD_STAGE_CHANGED = "lead.stage_changed"
    LEAD_CONVERTED = "lead.converted"

    # ─── Pipelines & Deals (Phase 1C) ────────────────────────────────────────────
    PIPELINE_CREATED = "pipeline.created"
    DEAL_CREATED = "deal.created"
    DEAL_STAGE_CHANGED = "deal.stage_changed"

    # Additional event types are appended here as new phases are implemented.
