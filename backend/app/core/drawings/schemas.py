import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal

VALID_STATUSES = Literal["received", "active", "superseded", "void"]


class DrawingCreate(BaseModel):
    drawing_no: str = Field(..., max_length=100)
    title: str = Field(..., max_length=500)
    discipline: str = Field(..., max_length=100)
    revision: str = Field(..., max_length=50)
    status: VALID_STATUSES = "active"
    file_id: uuid.UUID


class DrawingRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    drawing_no: str
    title: str
    discipline: str
    revision: str
    status: str
    file_id: uuid.UUID
    supersedes_drawing_id: uuid.UUID | None
    source_thread_id: uuid.UUID | None
    source_message_id: uuid.UUID | None
    registered_by: uuid.UUID
    registered_at: datetime
    created_at: datetime


class DrawingFromInboxRequest(BaseModel):
    message_id: uuid.UUID
    attachment_file_id: uuid.UUID
    drawing_no: str = Field(..., max_length=100)
    title: str = Field(..., max_length=500)
    discipline: str = Field(..., max_length=100)
    revision: str = Field(..., max_length=50)
    close_thread_on_register: bool = False
