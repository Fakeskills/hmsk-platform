"""Sprint 7 – timesheets, compliance, payroll export

Revision ID: 0011_sprint7_timesheets
Revises: 0010_hardening_indexes
Create Date: 2025-01-01 00:00:10
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_sprint7_timesheets"
down_revision: Union[str, None] = "0010_hardening_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── timesheets ────────────────────────────────────────────────────────────
    op.create_table(
        "timesheets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_start", sa.Date, nullable=False),
        sa.Column("week_end", sa.Date, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopened_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["locked_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reopened_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "project_id", "user_id", "week_start",
                            name="uq_timesheet_user_week"),
    )
    op.create_index("ix_timesheets_tenant_id", "timesheets", ["tenant_id"])
    op.create_index("ix_timesheets_user_week", "timesheets", ["tenant_id", "user_id", "week_start"])
    op.create_index("ix_timesheets_tenant_status", "timesheets", ["tenant_id", "status"])
    op.create_index("ix_timesheets_tenant_project", "timesheets", ["tenant_id", "project_id"])

    # ── time_entries ──────────────────────────────────────────────────────────
    op.create_table(
        "time_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timesheet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_date", sa.Date, nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("break_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("net_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("is_adjustment", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("original_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("delta_minutes", sa.Integer, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["timesheet_id"], ["timesheets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["original_entry_id"], ["time_entries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_time_entries_tenant_id", "time_entries", ["tenant_id"])
    op.create_index("ix_time_entries_timesheet_id", "time_entries", ["timesheet_id"])
    op.create_index("ix_time_entries_tenant_user_date",
                    "time_entries", ["tenant_id", "user_id", "work_date"])
    op.create_index("ix_time_entries_tenant_project",
                    "time_entries", ["tenant_id", "project_id"])

    # ── compliance_rules ──────────────────────────────────────────────────────
    op.create_table(
        "compliance_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_code", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.String(50), nullable=False, server_default="warn"),
        sa.Column("action", sa.String(50), nullable=False, server_default="log"),
        sa.Column("parameters_json", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "rule_code", name="uq_compliance_rule_code"),
    )
    op.create_index("ix_compliance_rules_tenant_id", "compliance_rules", ["tenant_id"])

    # ── compliance_results ────────────────────────────────────────────────────
    op.create_table(
        "compliance_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timesheet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_code", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pass"),
        sa.Column("occurred_on", sa.Date, nullable=True),
        sa.Column("rule_snapshot_json", sa.Text, nullable=True),
        sa.Column("per_day_json", sa.Text, nullable=True),
        sa.Column("details_json", sa.Text, nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["timesheet_id"], ["timesheets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["compliance_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compliance_results_tenant_id", "compliance_results", ["tenant_id"])
    op.create_index("ix_compliance_results_timesheet_id", "compliance_results", ["timesheet_id"])
    op.create_index("ix_compliance_results_tenant_severity",
                    "compliance_results", ["tenant_id", "severity"])

    # ── payroll_exports ───────────────────────────────────────────────────────
    op.create_table(
        "payroll_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="generated"),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("void_reason", sa.Text, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sent_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["voided_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payroll_exports_tenant_id", "payroll_exports", ["tenant_id"])
    op.create_index("ix_payroll_exports_tenant_period",
                    "payroll_exports", ["tenant_id", "period_start", "period_end"])

    # ── payroll_export_lines ──────────────────────────────────────────────────
    op.create_table(
        "payroll_export_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("export_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timesheet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("net_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("source_entry_ids_json", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["export_id"], ["payroll_exports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["timesheet_id"], ["timesheets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("export_id", "timesheet_id", name="uq_export_line_timesheet"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payroll_export_lines_tenant_id", "payroll_export_lines", ["tenant_id"])
    op.create_index("ix_payroll_export_lines_export_id", "payroll_export_lines", ["export_id"])
    op.create_index("ix_payroll_export_lines_user_id", "payroll_export_lines", ["user_id"])


def downgrade() -> None:
    op.drop_table("payroll_export_lines")
    op.drop_table("payroll_exports")
    op.drop_table("compliance_results")
    op.drop_table("compliance_rules")
    op.drop_table("time_entries")
    op.drop_table("timesheets")
