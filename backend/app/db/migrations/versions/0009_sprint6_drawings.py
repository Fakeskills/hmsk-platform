"""Sprint 6 – drawing register

Revision ID: 0009_sprint6_drawings
Revises: 0008_sprint5_hardening
Create Date: 2025-01-01 00:00:08
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_sprint6_drawings"
down_revision: Union[str, None] = "0008_sprint5_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "drawings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("drawing_no", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("discipline", sa.String(100), nullable=False),
        sa.Column("revision", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supersedes_drawing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_thread_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("registered_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_drawing_id"], ["drawings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_thread_id"], ["message_threads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_message_id"], ["incoming_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["registered_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "project_id", "drawing_no", "revision", name="uq_drawing_no_revision"),
    )
    op.create_index("ix_drawings_tenant_id", "drawings", ["tenant_id"])
    op.create_index("ix_drawings_project_id", "drawings", ["project_id"])
    op.create_index("ix_drawings_drawing_no", "drawings", ["tenant_id", "project_id", "drawing_no"])


def downgrade() -> None:
    op.drop_table("drawings")
