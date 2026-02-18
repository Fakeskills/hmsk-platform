import re
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.inbox.models import IncomingAttachment, IncomingMessage, MessageThread
from app.core.inbox.schemas import IngestRequest
from app.core.rbac.models import Role, User, UserRoleAssignment
from app.core.tasks.models import Task

_PREFIX_RE = re.compile(r"^\s*(re|sv|fw|fwd|vs|ang)\s*(\[\d+\])?\s*:\s*", re.IGNORECASE)

def normalize_subject(subject: str) -> str:
    result = subject.strip()
    while True:
        new = _PREFIX_RE.sub("", result).strip()
        if new == result:
            break
        result = new
    return result

async def resolve_default_assignee(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID) -> uuid.UUID | None:
    for role_name in ("anleggsleder", "prosjektleder"):
        result = await db.execute(
            select(UserRoleAssignment.user_id)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .join(User, User.id == UserRoleAssignment.user_id)
            .where(
                UserRoleAssignment.tenant_id == tenant_id,
                Role.tenant_id == tenant_id,
                Role.name.ilike(role_name),
                Role.is_deleted == False,
                User.is_deleted == False,
                User.status == "active",
            ).limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            return row
    return None

async def get_or_create_thread(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID, normalized_subject: str) -> tuple[MessageThread, bool]:
    result = await db.execute(
        select(MessageThread).where(
            MessageThread.tenant_id == tenant_id,
            MessageThread.project_id == project_id,
            MessageThread.subject == normalized_subject,
            MessageThread.status == "open",
            MessageThread.is_deleted == False,
        )
    )
    thread = result.scalar_one_or_none()
    if thread:
        return thread, False
    assigned_to = await resolve_default_assignee(db, tenant_id, project_id)
    thread = MessageThread(tenant_id=tenant_id, project_id=project_id, subject=normalized_subject, status="open", assigned_to=assigned_to)
    db.add(thread)
    await db.flush()
    await db.refresh(thread)
    return thread, True

async def create_task_for_thread(db: AsyncSession, tenant_id: uuid.UUID, thread: MessageThread) -> Task:
    task = Task(
        tenant_id=tenant_id,
        project_id=thread.project_id,
        thread_id=thread.id,
        title=f"Ny henvendelse: {thread.subject}",
        description="Automatisk opprettet fra innkommende melding i prosjekt-innboks.",
        status="open",
        assigned_to=thread.assigned_to,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task

async def close_thread(db: AsyncSession, tenant_id: uuid.UUID, thread_id: uuid.UUID) -> MessageThread:
    from fastapi import HTTPException
    result = await db.execute(
        select(MessageThread).where(MessageThread.id == thread_id, MessageThread.tenant_id == tenant_id, MessageThread.is_deleted == False)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(404, "Thread not found")
    thread.status = "closed"
    await db.flush()
    result = await db.execute(
        select(Task).where(Task.thread_id == thread_id, Task.tenant_id == tenant_id, Task.status == "open", Task.is_deleted == False)
    )
    for task in result.scalars().all():
        task.status = "done"
    await db.flush()
    await db.refresh(thread)
    return thread

async def ingest_message(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID, data: IngestRequest) -> tuple[MessageThread, IncomingMessage, bool]:
    normalized = normalize_subject(data.subject)
    thread, is_new = await get_or_create_thread(db, tenant_id, project_id, normalized)
    message = IncomingMessage(
        tenant_id=tenant_id, thread_id=thread.id, project_id=project_id,
        sender_email=data.sender_email, sender_name=data.sender_name,
        subject_raw=data.subject, subject_normalized=normalized,
        body_text=data.body_text, body_html=data.body_html,
        message_id_header=data.message_id_header, is_new_thread=is_new,
    )
    db.add(message)
    await db.flush()
    for att in data.attachments:
        db.add(IncomingAttachment(tenant_id=tenant_id, message_id=message.id, filename=att.filename, content_type=att.content_type, size_bytes=att.size_bytes))
    if is_new:
        await create_task_for_thread(db, tenant_id, thread)
    await db.flush()
    await db.refresh(message)
    return thread, message, is_new
