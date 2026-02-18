import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None

class ProjectRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    project_no: str
    name: str
    description: str | None
    status: str
    inbox_email: str | None
    created_at: datetime
