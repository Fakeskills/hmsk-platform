"""Sprint 5 hardening – submitted_by, source_key, NOT NULL source_version

Revision ID: 0008_sprint5_hardening
Revises: 0007_sprint5_checklists
Create Date: 2025-01-01 00:00:07
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_sprint5_hardening"
down_revision: Union[str, None] = "0007_sprint5_checklists"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix #3 – add submitted_by to checklist_runs
    op.add_column("checklist_runs", sa.Column(
        "submitted_by", postgresql.UUID(as_uuid=True), nullable=True
    ))
    op.create_foreign_key(
        "fk_checklist_runs_submitted_by",
        "checklist_runs", "users",
        ["submitted_by"], ["id"],
        ondelete="SET NULL",
    )

    # Fix #2 – source_checklist_template_version_id NOT NULL
    # Backfill nulls with first available checklist_template_version
    op.execute("""
        UPDATE project_checklist_templates pct
        SET source_checklist_template_version_id = (
            SELECT id FROM checklist_template_versions
            ORDER BY created_at ASC
            LIMIT 1
        )
        WHERE pct.source_checklist_template_version_id IS NULL
    """)
    op.alter_column(
        "project_checklist_templates",
        "source_checklist_template_version_id",
        nullable=False,
    )

    # Find actual FK name in pg_constraint and drop it dynamically
    op.execute("""
        DO $$
        DECLARE
            fk_name TEXT;
        BEGIN
            SELECT conname INTO fk_name
            FROM pg_constraint
            WHERE conrelid = 'project_checklist_templates'::regclass
              AND contype = 'f'
              AND conname LIKE '%source_checklist%';
            IF fk_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE project_checklist_templates DROP CONSTRAINT ' || quote_ident(fk_name);
            END IF;
        END $$;
    """)
    op.create_foreign_key(
        "fk_pct_source_version",
        "project_checklist_templates", "checklist_template_versions",
        ["source_checklist_template_version_id"], ["id"],
        ondelete="RESTRICT",
    )

    # Fix #6 – add source_key to nonconformances for idempotency
    op.add_column("nonconformances", sa.Column(
        "source_key", sa.String(255), nullable=True
    ))
    op.execute("""
        CREATE UNIQUE INDEX uq_nc_checklist_source_key
        ON nonconformances (tenant_id, source_type, source_id, source_key)
        WHERE source_type = 'checklist'
          AND source_key IS NOT NULL
          AND is_deleted = false
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_nc_checklist_source_key")
    op.drop_column("nonconformances", "source_key")

    op.drop_constraint("fk_pct_source_version", "project_checklist_templates", type_="foreignkey")
    op.execute("""
        DO $$
        BEGIN
            ALTER TABLE project_checklist_templates
                ADD CONSTRAINT fk_pct_source_version_old
                FOREIGN KEY (source_checklist_template_version_id)
                REFERENCES checklist_template_versions(id)
                ON DELETE SET NULL;
        END $$;
    """)
    op.alter_column(
        "project_checklist_templates",
        "source_checklist_template_version_id",
        nullable=True,
    )

    op.drop_constraint("fk_checklist_runs_submitted_by", "checklist_runs", type_="foreignkey")
    op.drop_column("checklist_runs", "submitted_by")
