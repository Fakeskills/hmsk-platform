import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal, Any

VALID_CATEGORIES = Literal["HMS", "MILJO", "KVALITET", "ANNET"]


# ── Library ───────────────────────────────────────────────────────────────────

class ChecklistTemplateCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str | None = None
    category: VALID_CATEGORIES = "ANNET"


class ChecklistTemplateRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    checklist_no: str
    title: str
    description: str | None
    category: str
    status: str
    owner_user_id: uuid.UUID | None
    created_at: datetime


class ChecklistTemplateVersionCreate(BaseModel):
    schema_json: str  # JSON string – validated by service
    change_summary: str | None = None


class ChecklistTemplateVersionRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    template_id: uuid.UUID
    tenant_id: uuid.UUID
    version_no: int
    schema_json: str | None
    change_summary: str | None
    status: str
    published_at: datetime | None
    published_by: uuid.UUID | None
    created_at: datetime


# ── Project import ────────────────────────────────────────────────────────────

class ChecklistImportRequest(BaseModel):
    """Import a published library version into the project."""
    checklist_template_version_id: uuid.UUID


class ProjectChecklistTemplateRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    source_checklist_template_version_id: uuid.UUID | None
    checklist_no: str
    title: str
    category: str
    status: str
    created_at: datetime


class ProjectChecklistTemplateVersionRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    checklist_id: uuid.UUID
    tenant_id: uuid.UUID
    version_no: int
    schema_json: str | None
    change_summary: str | None
    status: str
    created_at: datetime


# ── Execution ─────────────────────────────────────────────────────────────────

class ChecklistRunCreate(BaseModel):
    """Start a new run against the active template version."""
    template_version_id: uuid.UUID


class ChecklistRunUpdate(BaseModel):
    """Save answers in progress (only when status=open)."""
    answers_json: str  # JSON string


class ChecklistRunRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    checklist_id: uuid.UUID
    template_version_id: uuid.UUID
    status: str
    answers_json: str | None
    run_by: uuid.UUID | None
    submitted_at: datetime | None
    approved_at: datetime | None
    approved_by: uuid.UUID | None
    rejected_at: datetime | None
    rejected_by: uuid.UUID | None
    rejection_reason: str | None
    created_at: datetime


class ChecklistRunReject(BaseModel):
    reason: str = Field(..., min_length=1)


class ChecklistRunSubmit(BaseModel):
    answers_json: str  # Final answers at submit time
