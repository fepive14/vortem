"""Initial schema: organizations, users, events.

Revision ID: 0001
Revises:
Create Date: 2026-03-28 00:00:00.000000 UTC
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ─── Revision identifiers ──────────────────────────────────────────────────────
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Extensions — idempotent
    # ------------------------------------------------------------------
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ------------------------------------------------------------------
    # organizations
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at  TIMESTAMPTZ NOT NULL    DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL    DEFAULT now(),
            name        TEXT        NOT NULL,
            description TEXT,
            logo_url    TEXT,
            is_active   BOOLEAN     NOT NULL    DEFAULT TRUE,
            pipeline_id UUID,
            settings    JSONB       NOT NULL    DEFAULT '{}',
            parent_id   UUID        REFERENCES organizations(id)
        )
    """)

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    # Create enum type idempotently
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
                CREATE TYPE user_role AS ENUM ('admin', 'supervisor', 'agent', 'viewer');
            END IF;
        END
        $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at      TIMESTAMPTZ NOT NULL    DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL    DEFAULT now(),
            email           TEXT        NOT NULL    UNIQUE,
            full_name       TEXT        NOT NULL,
            hashed_password TEXT        NOT NULL,
            is_active       BOOLEAN     NOT NULL    DEFAULT TRUE,
            organization_id UUID        REFERENCES organizations(id),
            is_global_admin BOOLEAN     NOT NULL    DEFAULT FALSE,
            role            user_role   NOT NULL,
            avatar_url      TEXT,
            phone           TEXT,
            timezone        TEXT        NOT NULL    DEFAULT 'America/Bogota',
            CONSTRAINT ck_users_org_or_global
                CHECK (is_global_admin = TRUE OR organization_id IS NOT NULL)
        )
    """)

    # Indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_email
            ON users (email)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_organization_id
            ON users (organization_id)
    """)

    # ------------------------------------------------------------------
    # events  (internal event bus)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            type            TEXT        NOT NULL,
            payload         JSONB       NOT NULL,
            organization_id UUID,
            user_id         UUID,
            processed_at    TIMESTAMPTZ,
            failed_at       TIMESTAMPTZ,
            error           TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Partial index for unprocessed events — the worker polls this.
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_events_unprocessed
            ON events (processed_at)
            WHERE processed_at IS NULL AND failed_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS events")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS organizations")
    op.execute("DROP TYPE IF EXISTS user_role")
