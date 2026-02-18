import uuid
from sqlalchemy import Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin


class ProjectSequence(Base, TimestampMixin):
    __tablename__ = "project_sequences"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    __table_args__ = (UniqueConstraint("tenant_id", "year", name="uq_project_sequence_tenant_year"),)


class Project(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_no: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    inbox_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    threads: Mapped[list["MessageThread"]] = relationship(back_populates="project", lazy="noload")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", lazy="noload")
    __table_args__ = (UniqueConstraint("tenant_id", "project_no", name="uq_project_tenant_no"),)
