import uuid
from datetime import datetime, date
from pydantic import BaseModel, Field, model_validator
from typing import Literal

VALID_TIMESHEET_STATUSES = Literal["open", "submitted", "approved", "locked"]
VALID_SEVERITY = Literal["info", "warn", "block", "critical"]
VALID_EXPORT_STATUSES = Literal["generated", "sent", "voided"]


# ── Timesheet ─────────────────────────────────────────────────────────────────

class TimesheetCreate(BaseModel):
    project_id: uuid.UUID
    week_start: date  # Must be Monday


class TimesheetRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    week_start: date
    week_end: date
    status: str
    submitted_at: datetime | None
    submitted_by: uuid.UUID | None
    approved_at: datetime | None
    approved_by: uuid.UUID | None
    locked_at: datetime | None
    locked_by: uuid.UUID | None
    reopened_at: datetime | None
    reopened_by: uuid.UUID | None
    created_at: datetime


class ReopenRequest(BaseModel):
    reason: str = Field(..., min_length=1)


# ── Time entries ──────────────────────────────────────────────────────────────

class TimeEntryCreate(BaseModel):
    work_date: date
    start_time: datetime
    end_time: datetime
    break_minutes: int = Field(0, ge=0)
    description: str | None = None

    @model_validator(mode="after")
    def validate_times(self) -> "TimeEntryCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        if self.break_minutes < 0:
            raise ValueError("break_minutes must be >= 0")
        return self


class TimeEntryUpdate(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    break_minutes: int | None = Field(None, ge=0)
    description: str | None = None

    @model_validator(mode="after")
    def validate_times(self) -> "TimeEntryUpdate":
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValueError("end_time must be after start_time")
        return self


class AdjustmentCreate(BaseModel):
    original_entry_id: uuid.UUID
    delta_minutes: int  # can be negative
    description: str | None = None


class TimeEntryRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    timesheet_id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    work_date: date
    start_time: datetime
    end_time: datetime
    break_minutes: int
    net_minutes: int
    description: str | None
    status: str
    is_adjustment: bool
    original_entry_id: uuid.UUID | None
    delta_minutes: int | None
    created_at: datetime


# ── Compliance ────────────────────────────────────────────────────────────────

class ComplianceRuleCreate(BaseModel):
    rule_code: str = Field(..., max_length=100)
    title: str = Field(..., max_length=500)
    description: str | None = None
    severity: VALID_SEVERITY = "warn"
    action: Literal["log", "auto_nc"] = "log"
    parameters_json: str | None = None  # JSON string


class ComplianceRuleRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    rule_code: str
    title: str
    description: str | None
    severity: str
    action: str
    parameters_json: str | None
    is_active: bool
    created_at: datetime


class ComplianceResultRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    timesheet_id: uuid.UUID
    rule_id: uuid.UUID
    rule_code: str
    severity: str
    status: str
    occurred_on: date | None
    rule_snapshot_json: str | None
    per_day_json: str | None
    details_json: str | None
    evaluated_at: datetime
    resolved_at: datetime | None
    resolved_by: uuid.UUID | None


class ViolationResolveRequest(BaseModel):
    resolution_note: str = Field(..., min_length=1)


# ── Payroll export ────────────────────────────────────────────────────────────

class PayrollExportCreate(BaseModel):
    period_start: date
    period_end: date
    project_id: uuid.UUID | None = None  # None = all projects in tenant


class PayrollExportRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    period_start: date
    period_end: date
    status: str
    generated_by: uuid.UUID
    generated_at: datetime
    sent_at: datetime | None
    sent_by: uuid.UUID | None
    voided_at: datetime | None
    voided_by: uuid.UUID | None
    void_reason: str | None
    created_at: datetime


class PayrollExportLineRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    export_id: uuid.UUID
    timesheet_id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    net_minutes: int
    source_entry_ids_json: str | None


class VoidExportRequest(BaseModel):
    reason: str = Field(..., min_length=1)
