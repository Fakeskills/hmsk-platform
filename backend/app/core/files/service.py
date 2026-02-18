import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.files.models import File, FileLink
from app.core.files.schemas import FileCreate


async def create_file(db: AsyncSession, tenant_id: uuid.UUID, data: FileCreate, uploaded_by: uuid.UUID | None = None) -> File:
    f = File(tenant_id=tenant_id, uploaded_by=uploaded_by, **data.model_dump())
    db.add(f)
    await db.flush()
    await db.refresh(f)
    return f


async def link_file(db: AsyncSession, tenant_id: uuid.UUID, file_id: uuid.UUID, resource_type: str, resource_id: uuid.UUID) -> FileLink:
    link = FileLink(tenant_id=tenant_id, file_id=file_id, resource_type=resource_type, resource_id=resource_id)
    db.add(link)
    await db.flush()
    return link


async def get_links(db: AsyncSession, resource_type: str, resource_id: uuid.UUID) -> list[FileLink]:
    result = await db.execute(
        select(FileLink).where(FileLink.resource_type == resource_type, FileLink.resource_id == resource_id)
    )
    return list(result.scalars().all())
