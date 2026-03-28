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

    # Additional event types are appended here as new phases are implemented.
