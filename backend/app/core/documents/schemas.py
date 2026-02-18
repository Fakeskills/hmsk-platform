import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal

VALID_CATEGORIES = Literal["HMS", "MILJO", "KVALITET", "ANNET"]


# ── Library ───────────────────────────────────────────────────────────────────

class DocTemplateCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str | None = None
    doc_type: str = "procedure"
    category: VALID_CATEGORIES = "ANNET"


class DocTemplateRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    description: str | None
    doc_type: str
    category: str
    status: str
    created_by: uuid.UUID | None
    created_at: datetime


class DocTemplateVersionCreate(BaseModel):
    content: str | None = None
    change_summary: str | None = None


class DocTemplateVersionUpdate(BaseModel):
    content: str | None = None
    change_summary: str | None = None


class DocTemplateVersionRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    template_id: uuid.UUID
    tenant_id: uuid.UUID
    version_no: int
    content: str | None
    change_summary: str | None
    status: str
    published_at: datetime | None
    published_by: uuid.UUID | None
    created_at: datetime


# ── Project docs ──────────────────────────────────────────────────────────────

class ProjectDocCreate(BaseModel):
    title: str = Field(..., max_length=500)
    doc_type: str = "procedure"
    category: VALID_CATEGORIES = "ANNET"
    template_version_id: uuid.UUID | None = None
    content: str | None = None


class ProjectDocRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    template_id: uuid.UUID | None
    source_template_version_id: uuid.UUID | None
    title: str
    doc_no: str
    doc_type: str
    category: str
    status: str
    owner_user_id: uuid.UUID | None
    created_at: datetime


class ProjectDocVersionCreate(BaseModel):
    content: str | None = None
    change_summary: str | None = None
    requires_ack: bool = False


class ProjectDocVersionUpdate(BaseModel):
    content: str | None = None
    change_summary: str | None = None
    requires_ack: bool | None = None


class ProjectDocVersionRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    doc_id: uuid.UUID
    tenant_id: uuid.UUID
    version_no: int
    content: str | None
    change_summary: str | None
    status: str
    requires_ack: bool
    approved_at: datetime | None
    approved_by: uuid.UUID | None
    issued_at: datetime | None
    issued_by: uuid.UUID | None
    created_at: datetime


# ── Acknowledgements ──────────────────────────────────────────────────────────

class AckRequestRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    doc_version_id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    created_at: datetime


class AckResponseCreate(BaseModel):
    comment: str | None = None


class AckResponseRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    ack_request_id: uuid.UUID
    user_id: uuid.UUID
    acknowledged_at: datetime
    comment: str | None


class AckReportRow(BaseModel):
    user_id: uuid.UUID
    status: str
    acknowledged_at: datetime | None


class IssueRequest(BaseModel):
    ack_user_ids: list[uuid.UUID] = Field(default_factory=list)
