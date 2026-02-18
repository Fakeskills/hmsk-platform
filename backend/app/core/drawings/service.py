import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.drawings.models import Drawing
from app.core.drawings.schemas import DrawingCreate, DrawingFromInboxRequest


async def register_drawing(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    data: DrawingCreate,
    registered_by: uuid.UUID,
    source_thread_id: uuid.UUID | None = None,
    source_message_id: uuid.UUID | None = None,
) -> Drawing:
    from fastapi import HTTPException
    from app.core.audit.service import audit

    supersedes_id = None

    if data.status == "active":
        # Find existing active drawing with same drawing_no
        result = await db.execute(
            select(Drawing).where(
                Drawing.tenant_id == tenant_id,
                Drawing.project_id == project_id,
                Drawing.drawing_no == data.drawing_no,
                Drawing.status == "active",
                Drawing.is_deleted == False,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if existing.revision == data.revision:
                raise HTTPException(
                    400,
                    f"Drawing {data.drawing_no} revision {data.revision} already exists and is active"
                )
            existing.status = "superseded"
            supersedes_id = existing.id
            await db.flush()
            await audit(
                db, tenant_id=tenant_id, user_id=registered_by,
                action="drawing.superseded",
                resource_type="drawing",
                resource_id=str(existing.id),
                detail={
                    "drawing_no": data.drawing_no,
                    "old_revision": existing.revision,
                    "new_revision": data.revision,
                },
            )

    now = datetime.now(timezone.utc)
    drawing = Drawing(
        tenant_id=tenant_id,
        project_id=project_id,
        drawing_no=data.drawing_no,
        title=data.title,
        discipline=data.discipline,
        revision=data.revision,
        status=data.status,
        file_id=data.file_id,
        supersedes_drawing_id=supersedes_id,
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
        registered_by=registered_by,
        registered_at=now,
    )
    db.add(drawing)
    await db.flush()

    await audit(
        db, tenant_id=tenant_id, user_id=registered_by,
        action="drawing.registered",
        resource_type="drawing",
        resource_id=str(drawing.id),
        detail={
            "drawing_no": data.drawing_no,
            "revision": data.revision,
            "discipline": data.discipline,
            "status": data.status,
            "supersedes_id": str(supersedes_id) if supersedes_id else None,
        },
    )
    await db.refresh(drawing)
    return drawing


async def register_from_inbox(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    data: DrawingFromInboxRequest,
    registered_by: uuid.UUID,
) -> Drawing:
    from fastapi import HTTPException
    from app.core.inbox.models import IncomingMessage

    # Resolve source message + thread
    result = await db.execute(
        select(IncomingMessage).where(
            IncomingMessage.id == data.message_id,
            IncomingMessage.tenant_id == tenant_id,
            IncomingMessage.is_deleted == False,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(404, "Inbox message not found")

    draw_data = DrawingCreate(
        drawing_no=data.drawing_no,
        title=data.title,
        discipline=data.discipline,
        revision=data.revision,
        status="active",
        file_id=data.attachment_file_id,
    )

    drawing = await register_drawing(
        db, tenant_id, project_id, draw_data,
        registered_by=registered_by,
        source_thread_id=message.thread_id,
        source_message_id=message.id,
    )

    # Optionally close thread + tasks
    if data.close_thread_on_register and message.thread_id:
        from app.core.inbox.service import close_thread
        await close_thread(db, tenant_id, message.thread_id)

    return drawing


async def get_drawing(db: AsyncSession, drawing_id: uuid.UUID) -> Drawing | None:
    result = await db.execute(
        select(Drawing).where(
            Drawing.id == drawing_id,
            Drawing.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_drawings(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    only_active: bool = False,
    discipline: str | None = None,
    drawing_no: str | None = None,
    status: str | None = None,
) -> list[Drawing]:
    q = select(Drawing).where(
        Drawing.tenant_id == tenant_id,
        Drawing.project_id == project_id,
        Drawing.is_deleted == False,
    )
    if only_active:
        q = q.where(Drawing.status == "active")
    if discipline:
        q = q.where(Drawing.discipline.ilike(f"%{discipline}%"))
    if drawing_no:
        q = q.where(Drawing.drawing_no.ilike(f"%{drawing_no}%"))
    if status:
        q = q.where(Drawing.status == status)
    q = q.order_by(Drawing.drawing_no, Drawing.registered_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())
