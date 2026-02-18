import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class NonconformanceCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str | None = None
    nc_type: str = "nonconformance"
    severity: str = "low"
    assigned_to: uuid.UUID | None = None
    source_type: str | None = None
    source_id: uuid.UUID | None = None

class NonconformanceRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    nc_no: str
    title: str
    description: str | None
    nc_type: str
    severity: str
    status: str
    source_type: str | None
    source_id: uuid.UUID | None
    assigned_to: uuid.UUID | None
    root_cause: str | None
    created_at: datetime

class NonconformanceUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    status: str | None = None
    assigned_to: uuid.UUID | None = None
    root_cause: str | None = None

class CapaActionCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str | None = None
    action_type: str = "corrective"
    assigned_to: uuid.UUID | None = None
    due_date: str | None = None

class CapaActionRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    nonconformance_id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    description: str | None
    action_type: str
    status: str
    assigned_to: uuid.UUID | None
    due_date: str | None
    created_at: datetime

class CapaActionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    assigned_to: uuid.UUID | None = None
    due_date: str | None = None
