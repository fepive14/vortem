"""Add vertical column to organizations.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-01
"""

from __future__ import annotations

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'org_vertical') THEN
                CREATE TYPE org_vertical AS ENUM ('generic', 'veterinary');
            END IF;
        END $$;
    """)

    op.execute("""
        ALTER TABLE organizations
        ADD COLUMN IF NOT EXISTS vertical org_vertical NOT NULL DEFAULT 'generic';
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS vertical")
    op.execute("DROP TYPE IF EXISTS org_vertical")
