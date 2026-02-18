import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class AttachmentInput(BaseModel):
    filename: str
    content_type: str | None = None
    size_bytes: int | None = None

class IngestRequest(BaseModel):
    sender_email: str
    sender_name: str | None = None
    subject: str = Field(..., max_length=500)
    body_text: str | None = None
    body_html: str | None = None
    message_id_header: str | None = None
    attachments: list[AttachmentInput] = []

class ThreadRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    subject: str
    status: str
    assigned_to: uuid.UUID | None
    created_at: datetime

class MessageRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    thread_id: uuid.UUID
    sender_email: str
    sender_name: str | None
    subject_raw: str
    subject_normalized: str
    body_text: str | None
    is_new_thread: bool
    created_at: datetime

class IngestResponse(BaseModel):
    thread: ThreadRead
    message_id: uuid.UUID
    is_new_thread: bool
