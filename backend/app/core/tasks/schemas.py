import uuid
from datetime import datetime
from pydantic import BaseModel

class TaskRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    thread_id: uuid.UUID | None
    title: str
    description: str | None
    status: str
    assigned_to: uuid.UUID | None
    due_date: datetime | None
    created_at: datetime

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    assigned_to: uuid.UUID | None = None
    due_date: datetime | None = None
