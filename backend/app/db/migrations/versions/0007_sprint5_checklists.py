"""Sprint 5 – checklist engine

Revision ID: 0007_sprint5_checklists
Revises: 0006_sprint4_hardening
Create Date: 2025-01-01 00:00:06
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_sprint5_checklists"
down_revision: Union[str, None] = "0006_sprint4_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "checklist_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklist_no", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="ANNET"),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "checklist_no", name="uq_checklist_template_no"),
    )
    op.create_index("ix_checklist_templates_tenant_id", "checklist_templates", ["tenant_id"])

    op.create_table(
        "checklist_template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer, nullable=False, server_default="1"),
        sa.Column("schema_json", sa.Text, nullable=True),
        sa.Column("change_summary", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["checklist_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_checklist_template_versions_tenant_id", "checklist_template_versions", ["tenant_id"])
    op.create_index("ix_checklist_template_versions_template_id", "checklist_template_versions", ["template_id"])

    op.create_table(
        "project_checklist_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_checklist_template_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checklist_no", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="ANNET"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_checklist_template_version_id"], ["checklist_template_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "project_id", "checklist_no", name="uq_project_checklist_no"),
    )
    op.create_index("ix_project_checklist_templates_tenant_id", "project_checklist_templates", ["tenant_id"])
    op.create_index("ix_project_checklist_templates_project_id", "project_checklist_templates", ["project_id"])

    op.create_table(
        "project_checklist_template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer, nullable=False, server_default="1"),
        sa.Column("schema_json", sa.Text, nullable=True),
        sa.Column("change_summary", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["checklist_id"], ["project_checklist_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_checklist_template_versions_tenant_id", "project_checklist_template_versions", ["tenant_id"])
    op.create_index("ix_project_checklist_template_versions_checklist_id", "project_checklist_template_versions", ["checklist_id"])

    op.create_table(
        "checklist_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("answers_json", sa.Text, nullable=True),
        sa.Column("run_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["checklist_id"], ["project_checklist_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_version_id"], ["project_checklist_template_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rejected_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_checklist_runs_tenant_id", "checklist_runs", ["tenant_id"])
    op.create_index("ix_checklist_runs_project_id", "checklist_runs", ["project_id"])
    op.create_index("ix_checklist_runs_checklist_id", "checklist_runs", ["checklist_id"])


def downgrade() -> None:
    op.drop_table("checklist_runs")
    op.drop_table("project_checklist_template_versions")
    op.drop_table("project_checklist_templates")
    op.drop_table("checklist_template_versions")
    op.drop_table("checklist_templates")
