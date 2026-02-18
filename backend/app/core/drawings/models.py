import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, Text, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin


class Drawing(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    Project drawing register with revision control.
    status: received | active | superseded | void
    One active revision per drawing_no per project.
    """
    __tablename__ = "drawings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    drawing_no: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False)
    revision: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="RESTRICT"), nullable=False)
    supersedes_drawing_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("drawings.id", ondelete="SET NULL"), nullable=True)
    source_thread_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("message_threads.id", ondelete="SET NULL"), nullable=True)
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("incoming_messages.id", ondelete="SET NULL"), nullable=True)
    registered_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "drawing_no", "revision", name="uq_drawing_no_revision"),
    )
