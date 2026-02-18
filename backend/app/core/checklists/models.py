import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, Text, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin


# ── Library ───────────────────────────────────────────────────────────────────

class ChecklistTemplate(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    Library master checklist template.
    checklist_no unique per tenant (e.g. CL-001)
    category: HMS | MILJO | KVALITET | ANNET
    status: draft | published | archived
    """
    __tablename__ = "checklist_templates"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checklist_no: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="ANNET")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    versions: Mapped[list["ChecklistTemplateVersion"]] = relationship(back_populates="template", lazy="noload")
    __table_args__ = (
        UniqueConstraint("tenant_id", "checklist_no", name="uq_checklist_template_no"),
    )


class ChecklistTemplateVersion(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    Immutable once published.
    schema_json: JSON array of field definitions.
    Field shape:
    {
      "id": "field_uuid",
      "label": "Is scaffolding secured?",
      "field_type": "yes_no",       // yes_no | text | number | date | photo
      "required": true,
      "requires_image": false,
      "creates_nc_on_no": true       // only for yes_no fields
    }
    status: draft | published | superseded
    """
    __tablename__ = "checklist_template_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("checklist_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    schema_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    template: Mapped["ChecklistTemplate"] = relationship(back_populates="versions")


# ── Project ───────────────────────────────────────────────────────────────────

class ProjectChecklistTemplate(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    Freeze copy of a library checklist version imported into a project.
    checklist_no unique per tenant+project.
    source_checklist_template_version_id: the library version frozen from.
    """
    __tablename__ = "project_checklist_templates"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    source_checklist_template_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("checklist_template_versions.id", ondelete="SET NULL"), nullable=True)
    checklist_no: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="ANNET")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    versions: Mapped[list["ProjectChecklistTemplateVersion"]] = relationship(back_populates="checklist", lazy="noload")
    runs: Mapped[list["ChecklistRun"]] = relationship(back_populates="checklist", lazy="noload")
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "checklist_no", name="uq_project_checklist_no"),
    )


class ProjectChecklistTemplateVersion(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    Versioned schema copy in project scope.
    Immutable once a run has been submitted against it.
    status: draft | active | superseded
    """
    __tablename__ = "project_checklist_template_versions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checklist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project_checklist_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    schema_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    checklist: Mapped["ProjectChecklistTemplate"] = relationship(back_populates="versions")
    runs: Mapped[list["ChecklistRun"]] = relationship(back_populates="template_version")


# ── Execution ─────────────────────────────────────────────────────────────────

class ChecklistRun(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    A filled-in execution of a project checklist template version.
    status: open -> submitted -> approved | rejected
    rejected transitions back to open (editable again, no new run created).

    answers_json shape:
    {
      "field_id": {
        "value": "Yes" | "No" | "some text" | 123,
        "file_ids": ["uuid1", "uuid2"]   // for photo fields or requires_image
      }
    }
    """
    __tablename__ = "checklist_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    checklist_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project_checklist_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    template_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project_checklist_template_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    answers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    checklist: Mapped["ProjectChecklistTemplate"] = relationship(back_populates="runs")
    template_version: Mapped["ProjectChecklistTemplateVersion"] = relationship(back_populates="runs")
