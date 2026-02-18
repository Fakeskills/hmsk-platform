"""Sprint 4 hardening – category, doc_no uniqueness, source_template_version_id

Revision ID: 0006_sprint4_hardening
Revises: 0005_sprint4_documents
Create Date: 2025-01-01 00:00:05
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_sprint4_hardening"
down_revision: Union[str, None] = "0005_sprint4_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── doc_templates: add category ───────────────────────────────────────────
    op.add_column("doc_templates", sa.Column("category", sa.String(50), nullable=True))
    op.execute("UPDATE doc_templates SET category = 'ANNET' WHERE category IS NULL")
    op.alter_column("doc_templates", "category", nullable=False)

    # ── project_docs: add category + source_template_version_id ──────────────
    op.add_column("project_docs", sa.Column("category", sa.String(50), nullable=True))
    op.execute("UPDATE project_docs SET category = 'ANNET' WHERE category IS NULL")
    op.alter_column("project_docs", "category", nullable=False)

    op.add_column("project_docs", sa.Column(
        "source_template_version_id", postgresql.UUID(as_uuid=True), nullable=True
    ))
    op.create_foreign_key(
        "fk_project_docs_source_template_version",
        "project_docs", "doc_template_versions",
        ["source_template_version_id"], ["id"],
        ondelete="SET NULL",
    )

    # Migrate existing template_version_id -> source_template_version_id
    op.execute("""
        UPDATE project_docs
        SET source_template_version_id = template_version_id
        WHERE template_version_id IS NOT NULL
          AND source_template_version_id IS NULL
    """)

    # Drop old template_version_id column (replaced by source_template_version_id)
    op.drop_constraint(
        "project_docs_template_version_id_fkey", "project_docs", type_="foreignkey"
    )
    op.drop_column("project_docs", "template_version_id")

    # ── project_docs: unique constraint on tenant+project+doc_no ─────────────
    op.create_unique_constraint(
        "uq_project_doc_no", "project_docs", ["tenant_id", "project_id", "doc_no"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_project_doc_no", "project_docs", type_="unique")

    op.add_column("project_docs", sa.Column(
        "template_version_id", postgresql.UUID(as_uuid=True), nullable=True
    ))
    op.execute("""
        UPDATE project_docs
        SET template_version_id = source_template_version_id
        WHERE source_template_version_id IS NOT NULL
    """)
    op.create_foreign_key(
        "project_docs_template_version_id_fkey",
        "project_docs", "doc_template_versions",
        ["template_version_id"], ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "fk_project_docs_source_template_version", "project_docs", type_="foreignkey"
    )
    op.drop_column("project_docs", "source_template_version_id")
    op.drop_column("project_docs", "category")
    op.drop_column("doc_templates", "category")
