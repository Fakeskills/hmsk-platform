import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str | None = None
    incident_type: str = "ruh"
    severity: str = "low"
    anonymous: bool = False
    occurred_at: datetime | None = None
    location: str | None = None


class IncidentRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    incident_no: str
    title: str
    description: str | None
    incident_type: str
    severity: str
    status: str
    reporter_visibility: str
    reporter_user_id_visible: uuid.UUID | None
    assigned_to: uuid.UUID | None
    occurred_at: datetime | None
    location: str | None
    created_at: datetime


class IncidentTriageUpdate(BaseModel):
    assigned_to: uuid.UUID | None = None
    severity: str | None = None


class IncidentMessageCreate(BaseModel):
    body: str = Field(..., min_length=1)
    is_internal: bool = False


class IncidentMessageRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    incident_id: uuid.UUID
    body: str
    sender_id: uuid.UUID | None
    is_internal: bool
    created_at: datetime
