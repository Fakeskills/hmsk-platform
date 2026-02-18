import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin


# ── Library ───────────────────────────────────────────────────────────────────

class DocTemplate(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    Master document template in the library.
    Only HMSK-leder can publish versions.
    status: draft | published | archived
    """
    __tablename__ = "doc_templates"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_type: Mapped[str] = mapped_column(String(100), nullable=False, default="procedure")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    versions: Mapped[list["DocTemplateVersion"]] = relationship(back_populates="template", lazy="noload")


class DocTemplateVersion(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    Immutable once published.
    status: draft | published | superseded
    """
    __tablename__ = "doc_template_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("doc_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    template: Mapped["DocTemplate"] = relationship(back_populates="versions")


# ── Project docs ──────────────────────────────────────────────────────────────

class ProjectDoc(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    A document imported into a project from a library template (or created manually).
    status: draft | under_review | approved | issued | superseded
    """
    __tablename__ = "project_docs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("doc_templates.id", ondelete="SET NULL"), nullable=True)
    template_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("doc_template_versions.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_no: Mapped[str] = mapped_column(String(50), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(100), nullable=False, default="procedure")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    versions: Mapped[list["ProjectDocVersion"]] = relationship(back_populates="doc", lazy="noload")


class ProjectDocVersion(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    Immutable once issued.
    status: draft | under_review | approved | issued | superseded
    """
    __tablename__ = "project_doc_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project_docs.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    requires_ack: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    doc: Mapped["ProjectDoc"] = relationship(back_populates="versions")
    ack_requests: Mapped[list["AckRequest"]] = relationship(back_populates="doc_version", lazy="noload")


# ── Acknowledgements ──────────────────────────────────────────────────────────

class AckRequest(Base, TimestampMixin, TenantScopedMixin):
    """
    Created automatically when a version is issued with requires_ack=True.
    One row per user that must acknowledge.
    """
    __tablename__ = "ack_requests"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project_doc_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    doc_version: Mapped["ProjectDocVersion"] = relationship(back_populates="ack_requests")
    response: Mapped["AckResponse | None"] = relationship(back_populates="request", lazy="noload")


class AckResponse(Base, TimestampMixin, TenantScopedMixin):
    """
    Immutable read receipt. One per AckRequest.
    """
    __tablename__ = "ack_responses"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ack_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ack_requests.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    request: Mapped["AckRequest"] = relationship(back_populates="response")
