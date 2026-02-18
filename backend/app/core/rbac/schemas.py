import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RoleCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None
    permissions: str | None = None


class RoleRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    permissions: str | None
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    status: str | None = None


class UserRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str | None
    status: str
    is_superadmin: bool
    created_at: datetime


class RoleAssignRequest(BaseModel):
    role_id: uuid.UUID


class UserRoleAssignmentRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
