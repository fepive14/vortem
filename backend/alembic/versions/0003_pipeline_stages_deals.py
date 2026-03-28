"""Add pipelines, stages, deals, activities tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-28 00:00:00.000000 UTC
"""

from __future__ import annotations

from alembic import op

# ─── Revision identifiers ──────────────────────────────────────────────────────
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Enum — idempotent
    # ------------------------------------------------------------------
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'activity_type') THEN
                CREATE TYPE activity_type AS ENUM (
                    'call', 'note', 'task', 'email', 'meeting', 'voicehire_call'
                );
            END IF;
        END
        $$;
    """)

    # ------------------------------------------------------------------
    # pipelines
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS pipelines (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at      TIMESTAMPTZ NOT NULL    DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL    DEFAULT now(),
            organization_id UUID        REFERENCES organizations(id) ON DELETE CASCADE,
            name            TEXT        NOT NULL,
            description     TEXT,
            is_default      BOOLEAN     NOT NULL    DEFAULT FALSE
        )
    """)

    # ------------------------------------------------------------------
    # stages
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS stages (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at      TIMESTAMPTZ NOT NULL    DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL    DEFAULT now(),
            organization_id UUID        NOT NULL    REFERENCES organizations(id) ON DELETE CASCADE,
            pipeline_id     UUID        NOT NULL    REFERENCES pipelines(id) ON DELETE CASCADE,
            name            TEXT        NOT NULL,
            "order"         INTEGER     NOT NULL,
            color           TEXT,
            probability     INTEGER     NOT NULL    DEFAULT 0,
            is_won          BOOLEAN     NOT NULL    DEFAULT FALSE,
            is_lost         BOOLEAN     NOT NULL    DEFAULT FALSE,
            CONSTRAINT uq_stages_pipeline_order UNIQUE (pipeline_id, "order")
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_stages_pipeline_id ON stages (pipeline_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_stages_organization_id ON stages (organization_id)")

    # ------------------------------------------------------------------
    # deals
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS deals (
            id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at          TIMESTAMPTZ   NOT NULL    DEFAULT now(),
            updated_at          TIMESTAMPTZ   NOT NULL    DEFAULT now(),
            organization_id     UUID          NOT NULL    REFERENCES organizations(id) ON DELETE CASCADE,
            name                TEXT          NOT NULL,
            value               NUMERIC(14,2),
            currency            TEXT          NOT NULL    DEFAULT 'USD',
            contact_id          UUID          NOT NULL    REFERENCES contacts(id) ON DELETE RESTRICT,
            stage_id            UUID          NOT NULL    REFERENCES stages(id) ON DELETE RESTRICT,
            pipeline_id         UUID          NOT NULL    REFERENCES pipelines(id) ON DELETE RESTRICT,
            assigned_to         UUID          REFERENCES users(id) ON DELETE SET NULL,
            expected_close_date DATE,
            closed_at           TIMESTAMPTZ,
            notes               TEXT,
            custom_fields       JSONB         NOT NULL    DEFAULT '{}'
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_deals_organization_id ON deals (organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_deals_contact_id      ON deals (contact_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_deals_stage_id        ON deals (stage_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_deals_pipeline_id     ON deals (pipeline_id)")

    # ------------------------------------------------------------------
    # activities
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at      TIMESTAMPTZ   NOT NULL    DEFAULT now(),
            updated_at      TIMESTAMPTZ   NOT NULL    DEFAULT now(),
            organization_id UUID          NOT NULL    REFERENCES organizations(id) ON DELETE CASCADE,
            type            activity_type NOT NULL,
            contact_id      UUID          REFERENCES contacts(id) ON DELETE SET NULL,
            lead_id         UUID          REFERENCES leads(id) ON DELETE SET NULL,
            deal_id         UUID          REFERENCES deals(id) ON DELETE SET NULL,
            assigned_to     UUID          REFERENCES users(id) ON DELETE SET NULL,
            due_at          TIMESTAMPTZ,
            completed_at    TIMESTAMPTZ,
            body            TEXT,
            metadata        JSONB         NOT NULL    DEFAULT '{}'
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_activities_contact_id ON activities (contact_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_activities_lead_id    ON activities (lead_id)")

    # ------------------------------------------------------------------
    # Wire organizations.pipeline_id → pipelines (FK)
    #
    # The column already exists (created in migration 0001 as plain UUID).
    # ADD COLUMN IF NOT EXISTS is a no-op for existing columns, so the FK
    # constraint must be added separately.
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS pipeline_id UUID")

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_organizations_pipeline_id'
                  AND conrelid = 'organizations'::regclass
            ) THEN
                ALTER TABLE organizations
                    ADD CONSTRAINT fk_organizations_pipeline_id
                    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE SET NULL;
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE organizations
        DROP CONSTRAINT IF EXISTS fk_organizations_pipeline_id
    """)
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS pipeline_id")
    op.execute("DROP TABLE IF EXISTS activities")
    op.execute("DROP TABLE IF EXISTS deals")
    op.execute("DROP TABLE IF EXISTS stages")
    op.execute("DROP TABLE IF EXISTS pipelines")
    op.execute("DROP TYPE IF EXISTS activity_type")
