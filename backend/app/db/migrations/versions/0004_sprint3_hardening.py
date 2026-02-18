"""Sprint 3 hardening – incident anonymity, NC owner, CAPA lifecycle

Revision ID: 0004_sprint3_hardening
Revises: 0003_sprint3
Create Date: 2025-01-01 00:00:03
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_sprint3_hardening"
down_revision: Union[str, None] = "0003_sprint3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── incidents: replace anonymous+reported_by with visibility model ────────
    op.add_column("incidents", sa.Column("reporter_visibility", sa.String(20), nullable=True))
    op.add_column("incidents", sa.Column("reporter_user_id_internal", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("incidents", sa.Column("reporter_user_id_visible", postgresql.UUID(as_uuid=True), nullable=True))

    # Migrate existing data
    op.execute("""
        UPDATE incidents SET
            reporter_visibility = CASE
                WHEN anonymous = true THEN 'anonymous'
                ELSE 'named'
            END,
            reporter_user_id_internal = reported_by,
            reporter_user_id_visible = CASE
                WHEN anonymous = true THEN NULL
                ELSE reported_by
            END
    """)

    # Set NOT NULL after data migration
    op.alter_column("incidents", "reporter_visibility", nullable=False)

    # Add FK for reporter_user_id_internal
    op.create_foreign_key(
        "fk_incidents_reporter_internal",
        "incidents", "users",
        ["reporter_user_id_internal"], ["id"],
        ondelete="SET NULL",
    )

    # Drop old columns
    op.drop_column("incidents", "anonymous")
    op.drop_column("incidents", "reported_by")

    # ── nonconformances: rename assigned_to -> owner_user_id ──────────────────
    op.add_column("nonconformances", sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.execute("UPDATE nonconformances SET owner_user_id = assigned_to")

    op.create_foreign_key(
        "fk_nonconformances_owner",
        "nonconformances", "users",
        ["owner_user_id"], ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint("nonconformances_assigned_to_fkey", "nonconformances", type_="foreignkey")
    op.drop_column("nonconformances", "assigned_to")

    # ── capa_actions: add lifecycle columns ───────────────────────────────────
    op.add_column("capa_actions", sa.Column("done_at", sa.String(30), nullable=True))
    op.add_column("capa_actions", sa.Column("verified_at", sa.String(30), nullable=True))
    op.add_column("capa_actions", sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True))

    # Normalize any unknown status values to 'open'
    op.execute("""
        UPDATE capa_actions
        SET status = 'open'
        WHERE status NOT IN ('open', 'done', 'verified')
    """)

    op.create_foreign_key(
        "fk_capa_verified_by",
        "capa_actions", "users",
        ["verified_by"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # capa_actions
    op.drop_constraint("fk_capa_verified_by", "capa_actions", type_="foreignkey")
    op.drop_column("capa_actions", "verified_by")
    op.drop_column("capa_actions", "verified_at")
    op.drop_column("capa_actions", "done_at")

    # nonconformances
    op.drop_constraint("fk_nonconformances_owner", "nonconformances", type_="foreignkey")
    op.add_column("nonconformances", sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE nonconformances SET assigned_to = owner_user_id")
    op.create_foreign_key(
        "nonconformances_assigned_to_fkey",
        "nonconformances", "users",
        ["assigned_to"], ["id"],
        ondelete="SET NULL",
    )
    op.drop_column("nonconformances", "owner_user_id")

    # incidents
    op.drop_constraint("fk_incidents_reporter_internal", "incidents", type_="foreignkey")
    op.add_column("incidents", sa.Column("reported_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("incidents", sa.Column("anonymous", sa.Boolean, nullable=True))
    op.execute("""
        UPDATE incidents SET
            reported_by = reporter_user_id_internal,
            anonymous = CASE WHEN reporter_visibility = 'anonymous' THEN true ELSE false END
    """)
    op.drop_column("incidents", "reporter_user_id_visible")
    op.drop_column("incidents", "reporter_user_id_internal")
    op.drop_column("incidents", "reporter_visibility")
