"""Hardening patch v1 – missing indexes

Revision ID: 0010_hardening_indexes
Revises: 0009_sprint6_drawings
Create Date: 2025-01-01 00:00:09
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0010_hardening_indexes"
down_revision: Union[str, None] = "0009_sprint6_drawings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # tasks: tenant+project+status
    op.create_index(
        "ix_tasks_tenant_project_status",
        "tasks",
        ["tenant_id", "project_id", "status"],
    )
    # incidents: tenant+project+status
    op.create_index(
        "ix_incidents_tenant_project_status",
        "incidents",
        ["tenant_id", "project_id", "status"],
    )
    # incoming_messages: tenant+thread_id
    op.create_index(
        "ix_incoming_messages_tenant_thread",
        "incoming_messages",
        ["tenant_id", "thread_id"],
    )
    # nonconformances: tenant+project+status
    op.create_index(
        "ix_nonconformances_tenant_project_status",
        "nonconformances",
        ["tenant_id", "project_id", "status"],
    )
    # checklist_runs: tenant+project+status
    op.create_index(
        "ix_checklist_runs_tenant_project_status",
        "checklist_runs",
        ["tenant_id", "project_id", "status"],
    )
    # drawings: tenant+project+drawing_no (confirm/create)
    op.create_index(
        "ix_drawings_tenant_project_status",
        "drawings",
        ["tenant_id", "project_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_drawings_tenant_project_status", table_name="drawings")
    op.drop_index("ix_checklist_runs_tenant_project_status", table_name="checklist_runs")
    op.drop_index("ix_nonconformances_tenant_project_status", table_name="nonconformances")
    op.drop_index("ix_incoming_messages_tenant_thread", table_name="incoming_messages")
    op.drop_index("ix_incidents_tenant_project_status", table_name="incidents")
    op.drop_index("ix_tasks_tenant_project_status", table_name="tasks")
