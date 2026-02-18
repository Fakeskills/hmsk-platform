import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100, pattern=r"^[a-z0-9-]+$")
    plan: str | None = None
    notes: str | None = None


class TenantUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    status: str | None = None
    plan: str | None = None
    notes: str | None = None


class TenantRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    slug: str
    status: str
    plan: str | None
    created_at: datetime
    updated_at: datetime
