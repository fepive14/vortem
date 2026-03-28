"""Add contacts and leads tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-28 00:00:00.000000 UTC
"""

from __future__ import annotations

from alembic import op

# ─── Revision identifiers ──────────────────────────────────────────────────────
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Enum types — idempotent
    # ------------------------------------------------------------------
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'contact_status') THEN
                CREATE TYPE contact_status AS ENUM ('active', 'inactive', 'do_not_contact');
            END IF;
        END
        $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lead_status') THEN
                CREATE TYPE lead_status AS ENUM ('new', 'contacted', 'qualified', 'converted', 'discarded');
            END IF;
        END
        $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lead_source') THEN
                CREATE TYPE lead_source AS ENUM ('csv_import', 'manual', 'api', 'voicehire');
            END IF;
        END
        $$;
    """)

    # ------------------------------------------------------------------
    # leads  (must be created before contacts due to FK)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at      TIMESTAMPTZ   NOT NULL    DEFAULT now(),
            updated_at      TIMESTAMPTZ   NOT NULL    DEFAULT now(),
            organization_id UUID          NOT NULL    REFERENCES organizations(id) ON DELETE CASCADE,
            first_name      TEXT          NOT NULL,
            last_name       TEXT          NOT NULL,
            phone           TEXT,
            email           TEXT,
            country         TEXT,
            status          lead_status   NOT NULL    DEFAULT 'new',
            source          lead_source   NOT NULL    DEFAULT 'manual',
            campaign_id     UUID,
            assigned_to     UUID          REFERENCES users(id) ON DELETE SET NULL,
            voicehire_data  JSONB         NOT NULL    DEFAULT '{}'
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_leads_organization_id ON leads (organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_leads_assigned_to    ON leads (assigned_to)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_leads_status         ON leads (status)")

    # ------------------------------------------------------------------
    # contacts
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id              UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at      TIMESTAMPTZ    NOT NULL    DEFAULT now(),
            updated_at      TIMESTAMPTZ    NOT NULL    DEFAULT now(),
            organization_id UUID           NOT NULL    REFERENCES organizations(id) ON DELETE CASCADE,
            first_name      TEXT           NOT NULL,
            last_name       TEXT           NOT NULL,
            phone           TEXT,
            email           TEXT,
            company         TEXT,
            position        TEXT,
            country         TEXT,
            status          contact_status NOT NULL    DEFAULT 'active',
            lead_id         UUID           REFERENCES leads(id) ON DELETE SET NULL,
            assigned_to     UUID           REFERENCES users(id) ON DELETE SET NULL,
            tags            JSONB          NOT NULL    DEFAULT '[]',
            custom_fields   JSONB          NOT NULL    DEFAULT '{}'
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_contacts_organization_id ON contacts (organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_contacts_assigned_to     ON contacts (assigned_to)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS contacts")
    op.execute("DROP TABLE IF EXISTS leads")
    op.execute("DROP TYPE IF EXISTS contact_status")
    op.execute("DROP TYPE IF EXISTS lead_status")
    op.execute("DROP TYPE IF EXISTS lead_source")
