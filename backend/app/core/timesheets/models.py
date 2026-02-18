import uuid
from datetime import datetime, date
from sqlalchemy import (
    Boolean, DateTime, Date, String, Text,
    ForeignKey, Integer, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin


class Timesheet(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    One timesheet per user per ISO week.
    status: open → submitted → approved → locked
    Reopen requires explicit admin action + audit.
    Row-level locked on all transitions.
    """
    __tablename__ = "timesheets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopened_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    entries: Mapped[list["TimeEntry"]] = relationship(back_populates="timesheet", lazy="noload")
    compliance_results: Mapped[list["ComplianceResult"]] = relationship(back_populates="timesheet", lazy="noload")
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "user_id", "week_start", name="uq_timesheet_user_week"),
    )


class TimeEntry(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    Single time entry within a timesheet.
    Immutable once timesheet is locked.
    is_adjustment=True entries reference original_entry_id and contain delta_minutes.
    Cross-midnight entries allowed; compliance splits per local day.
    Overlap check excludes rejected entries.
    """
    __tablename__ = "time_entries"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timesheet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("timesheets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    break_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    # Adjustment fields
    is_adjustment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    original_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("time_entries.id", ondelete="SET NULL"), nullable=True)
    delta_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timesheet: Mapped["Timesheet"] = relationship(back_populates="entries")


class ComplianceRule(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    Configurable compliance rules per tenant.
    rule_code: unique identifier (e.g. MAX_DAILY_HOURS, MIN_REST_PERIOD)
    severity: info | warn | block | critical
    action: log | auto_nc
    parameters_json: rule-specific thresholds/config
    """
    __tablename__ = "compliance_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="warn")
    action: Mapped[str] = mapped_column(String(50), nullable=False, default="log")
    parameters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    __table_args__ = (
        UniqueConstraint("tenant_id", "rule_code", name="uq_compliance_rule_code"),
    )


class ComplianceResult(Base, TimestampMixin, TenantScopedMixin):
    """
    Stored result of one compliance evaluation for one timesheet.
    rule_snapshot_json: copy of rule parameters at evaluation time (immutable record).
    per_day_json: per-day breakdown of what was evaluated.
    details_json: structured violation details.
    status: pass | violation | resolved
    """
    __tablename__ = "compliance_results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timesheet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("timesheets.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pass")
    occurred_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    rule_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    per_day_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    timesheet: Mapped["Timesheet"] = relationship(back_populates="compliance_results")


class PayrollExport(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    """
    Payroll export batch.
    status: generated → sent → voided
    When marked sent: related timesheets set to locked.
    Double export prevention: timesheets cannot be in two non-voided exports.
    period_start/period_end: inclusive date range for export.
    """
    __tablename__ = "payroll_exports"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="generated")
    generated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    lines: Mapped[list["PayrollExportLine"]] = relationship(back_populates="export", lazy="noload")


class PayrollExportLine(Base, TimestampMixin, TenantScopedMixin):
    """
    One line per user per timesheet in the export.
    net_minutes: netto minutter etter justeringer.
    source_entry_ids_json: list of entry UUIDs included.
    """
    __tablename__ = "payroll_export_lines"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    export_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payroll_exports.id", ondelete="CASCADE"), nullable=False, index=True)
    timesheet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("timesheets.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False)
    net_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_entry_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    export: Mapped["PayrollExport"] = relationship(back_populates="lines")
    __table_args__ = (
        UniqueConstraint("export_id", "timesheet_id", name="uq_export_line_timesheet"),
    )
