import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin


class Incident(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    RUH – Rapport om Uønsket Hendelse.
    status flow: draft -> submitted -> triage -> open -> closed
    anonymous=True hides reporter identity from non-admin users.
    """
    __tablename__ = "incidents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    incident_no: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    incident_type: Mapped[str] = mapped_column(String(50), nullable=False, default="ruh")  # ruh | near_miss | injury | observation
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="low")  # low | medium | high | critical
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reported_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    messages: Mapped[list["IncidentMessage"]] = relationship(back_populates="incident", lazy="noload")


class IncidentMessage(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """2-way messaging thread on an incident."""
    __tablename__ = "incident_messages"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sender_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # internal = only visible to admin/HS
    incident: Mapped["Incident"] = relationship(back_populates="messages")
