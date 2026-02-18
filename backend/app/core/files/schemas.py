import uuid
from datetime import datetime
from pydantic import BaseModel

class FileRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    filename: str
    content_type: str | None
    size_bytes: int | None
    storage_path: str | None
    created_at: datetime

class FileCreate(BaseModel):
    filename: str
    content_type: str | None = None
    size_bytes: int | None = None
    storage_path: str | None = None
