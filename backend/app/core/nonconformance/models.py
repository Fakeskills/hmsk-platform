import uuid
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin


class Nonconformance(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    NC – Avvik.
    status flow: open -> under_review -> resolved -> closed
    owner_user_id: required, primary responsible person
    """
    __tablename__ = "nonconformances"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    nc_no: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    nc_type: Mapped[str] = mapped_column(String(50), nullable=False, default="nonconformance")
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="low")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    actions: Mapped[list["CapaAction"]] = relationship(back_populates="nonconformance", lazy="noload")


class CapaAction(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    CAPA – Corrective And Preventive Action.
    status lifecycle: open -> done -> verified (terminal)
    """
    __tablename__ = "capa_actions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nonconformance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nonconformances.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, default="corrective")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    done_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    verified_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    nonconformance: Mapped["Nonconformance"] = relationship(back_populates="actions")
