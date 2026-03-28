"""Add notifications table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-28 00:00:00.000000 UTC
"""

from __future__ import annotations

from alembic import op

# ─── Revision identifiers ──────────────────────────────────────────────────────
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Backfill events.updated_at if missing (migration 0001 originally
    # omitted this column; the ORM model always expected it).
    # ------------------------------------------------------------------
    op.execute("""
        ALTER TABLE events ADD COLUMN IF NOT EXISTS
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    """)

    # ------------------------------------------------------------------
    # Enum — idempotent
    # ------------------------------------------------------------------
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_priority') THEN
                CREATE TYPE notification_priority AS ENUM ('normal', 'high');
            END IF;
        END
        $$;
    """)

    # ------------------------------------------------------------------
    # notifications
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id              UUID                  PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at      TIMESTAMPTZ           NOT NULL    DEFAULT now(),
            updated_at      TIMESTAMPTZ           NOT NULL    DEFAULT now(),
            organization_id UUID                  NOT NULL    REFERENCES organizations(id) ON DELETE CASCADE,
            user_id         UUID                  NOT NULL    REFERENCES users(id) ON DELETE CASCADE,
            type            TEXT                  NOT NULL,
            priority        notification_priority NOT NULL    DEFAULT 'normal',
            title           TEXT                  NOT NULL,
            body            TEXT                  NOT NULL,
            entity_type     TEXT,
            entity_id       UUID,
            read_at         TIMESTAMPTZ
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id       ON notifications (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_read      ON notifications (user_id, read_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_organization_id ON notifications (organization_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notifications")
    op.execute("DROP TYPE IF EXISTS notification_priority")
