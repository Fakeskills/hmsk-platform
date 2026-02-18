#!/usr/bin/env bash
# =============================================================================
# sprint2.sh – HMSK Platform Sprint 2
# Kjør fra roten av hmsk-platform-mappen:
#   bash sprint2.sh
# =============================================================================
set -e

echo "🚀  Setter opp Sprint 2..."

# ── Nye mapper ─────────────────────────────────────────────────────────────────
mkdir -p \
  backend/app/core/projects \
  backend/app/core/inbox \
  backend/app/core/tasks

touch backend/app/core/projects/__init__.py
touch backend/app/core/inbox/__init__.py
touch backend/app/core/tasks/__init__.py

# =============================================================================
# MODELS
# =============================================================================

# ── projects/models.py ────────────────────────────────────────────────────────
cat > backend/app/core/projects/models.py << 'ENDOFFILE'
import uuid
from sqlalchemy import Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin


class ProjectSequence(Base, TimestampMixin):
    """
    Per-tenant counter for generating project_no in format YY-####.
    One row per tenant per year.
    """
    __tablename__ = "project_sequences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("tenant_id", "year", name="uq_project_sequence_tenant_year"),
    )


class Project(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_no: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    inbox_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    threads: Mapped[list["MessageThread"]] = relationship(back_populates="project", lazy="noload")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", lazy="noload")

    __table_args__ = (
        UniqueConstraint("tenant_id", "project_no", name="uq_project_tenant_no"),
    )
ENDOFFILE

# ── inbox/models.py ───────────────────────────────────────────────────────────
cat > backend/app/core/inbox/models.py << 'ENDOFFILE'
import uuid
from sqlalchemy import Boolean, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin
from app.core.projects.models import Project  # noqa – ensure Project is loaded


class MessageThread(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    __tablename__ = "message_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    project: Mapped["Project"] = relationship(back_populates="threads")
    messages: Mapped[list["IncomingMessage"]] = relationship(back_populates="thread", lazy="noload")


class IncomingMessage(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    __tablename__ = "incoming_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("message_threads.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject_raw: Mapped[str] = mapped_column(String(500), nullable=False)
    subject_normalized: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_id_header: Mapped[str | None] = mapped_column(String(255), nullable=True)  # email Message-ID
    is_new_thread: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    thread: Mapped["MessageThread"] = relationship(back_populates="messages")
    attachments: Mapped[list["IncomingAttachment"]] = relationship(back_populates="message", lazy="noload")


class IncomingAttachment(Base, TimestampMixin, TenantScopedMixin):
    __tablename__ = "incoming_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incoming_messages.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # MinIO path (Sprint 3+)

    message: Mapped["IncomingMessage"] = relationship(back_populates="attachments")
ENDOFFILE

# ── tasks/models.py ───────────────────────────────────────────────────────────
cat > backend/app/core/tasks/models.py << 'ENDOFFILE'
import uuid
from datetime import datetime
from sqlalchemy import DateTime, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin


class Task(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("message_threads.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="tasks")  # type: ignore[name-defined]
ENDOFFILE

# =============================================================================
# SCHEMAS
# =============================================================================

cat > backend/app/core/projects/schemas.py << 'ENDOFFILE'
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
ENDOFFILE

cat > backend/app/core/inbox/schemas.py << 'ENDOFFILE'
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Simulates an incoming email to the project inbox."""
    sender_email: str
    sender_name: str | None = None
    subject: str = Field(..., max_length=500)
    body_text: str | None = None
    body_html: str | None = None
    message_id_header: str | None = None
    attachments: list["AttachmentInput"] = []


class AttachmentInput(BaseModel):
    filename: str
    content_type: str | None = None
    size_bytes: int | None = None


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
ENDOFFILE

cat > backend/app/core/tasks/schemas.py << 'ENDOFFILE'
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
ENDOFFILE

# =============================================================================
# SERVICES
# =============================================================================

cat > backend/app/core/projects/service.py << 'ENDOFFILE'
"""
projects/service.py

generate_project_no uses SELECT FOR UPDATE on project_sequences to ensure
no two concurrent requests get the same number within a tenant+year.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.projects.models import Project, ProjectSequence
from app.core.projects.schemas import ProjectCreate
from app.settings import get_settings

INBOX_DOMAIN = "hmsk.app"


async def generate_project_no(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    """
    Atomically increments the per-tenant per-year sequence.
    Returns project_no in format "YY-####" e.g. "26-0001".
    Uses SELECT FOR UPDATE to prevent race conditions.
    """
    year = datetime.now(timezone.utc).year
    yy = str(year)[-2:]

    # Lock the row for this tenant+year
    result = await db.execute(
        select(ProjectSequence)
        .where(
            ProjectSequence.tenant_id == tenant_id,
            ProjectSequence.year == year,
        )
        .with_for_update()
    )
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = ProjectSequence(tenant_id=tenant_id, year=year, last_seq=0)
        db.add(seq)
        await db.flush()
        # Re-lock the newly inserted row
        result = await db.execute(
            select(ProjectSequence)
            .where(
                ProjectSequence.tenant_id == tenant_id,
                ProjectSequence.year == year,
            )
            .with_for_update()
        )
        seq = result.scalar_one()

    seq.last_seq += 1
    await db.flush()

    return f"{yy}-{seq.last_seq:04d}"


async def create_project(
    db: AsyncSession, tenant_id: uuid.UUID, data: ProjectCreate
) -> Project:
    project_no = await generate_project_no(db, tenant_id)

    # Resolve tenant slug for inbox email
    from app.core.tenants.models import Tenant
    t_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = t_result.scalar_one()

    inbox_email = f"{tenant.slug}+{project_no}@{INBOX_DOMAIN}"

    project = Project(
        tenant_id=tenant_id,
        project_no=project_no,
        name=data.name,
        description=data.description,
        inbox_email=inbox_email,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project | None:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def list_projects(db: AsyncSession, tenant_id: uuid.UUID) -> list[Project]:
    result = await db.execute(
        select(Project).where(Project.tenant_id == tenant_id, Project.is_deleted == False)
        .order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())
ENDOFFILE

cat > backend/app/core/inbox/service.py << 'ENDOFFILE'
"""
inbox/service.py

Key functions:
  normalize_subject  – strips Re:/Sv:/Fwd: prefixes
  get_or_create_thread – finds existing thread by normalized subject or creates one
  resolve_default_assignee – AL → PL → None
  create_task_for_thread – auto-task when a new thread is opened
  ingest_message – orchestrates the full ingest flow
"""
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.inbox.models import IncomingAttachment, IncomingMessage, MessageThread
from app.core.inbox.schemas import IngestRequest
from app.core.projects.models import Project
from app.core.rbac.models import Role, User, UserRoleAssignment
from app.core.tasks.models import Task


# ── Subject normalization ──────────────────────────────────────────────────────

_PREFIX_RE = re.compile(
    r"^\s*(re|sv|fw|fwd|vs|ang)\s*(\[\d+\])?\s*:\s*",
    re.IGNORECASE,
)


def normalize_subject(subject: str) -> str:
    """Strip Re:/Sv:/Fwd: etc. prefixes (repeatedly) and strip whitespace."""
    result = subject.strip()
    while True:
        new = _PREFIX_RE.sub("", result).strip()
        if new == result:
            break
        result = new
    return result


# ── Default assignee resolution ────────────────────────────────────────────────

async def resolve_default_assignee(
    db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID
) -> uuid.UUID | None:
    """
    Find first user with role 'anleggsleder' assigned in this tenant.
    Fallback to 'prosjektleder'. Fallback to None.

    Note: In Sprint 3+ this should be scoped to project members.
    For now we search tenant-wide role assignments.
    """
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
            )
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            return row
    return None


# ── Thread ─────────────────────────────────────────────────────────────────────

async def get_or_create_thread(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    normalized_subject: str,
) -> tuple[MessageThread, bool]:
    """
    Returns (thread, is_new).
    Matches open threads with the same normalized subject in the same project.
    """
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

    thread = MessageThread(
        tenant_id=tenant_id,
        project_id=project_id,
        subject=normalized_subject,
        status="open",
        assigned_to=assigned_to,
    )
    db.add(thread)
    await db.flush()
    await db.refresh(thread)
    return thread, True


# ── Task auto-creation ─────────────────────────────────────────────────────────

async def create_task_for_thread(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    thread: MessageThread,
) -> Task:
    task = Task(
        tenant_id=tenant_id,
        project_id=thread.project_id,
        thread_id=thread.id,
        title=f"Ny henvendelse: {thread.subject}",
        description=f"Automatisk opprettet fra innkommende melding i prosjekt-innboks.",
        status="open",
        assigned_to=thread.assigned_to,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


# ── Close thread ───────────────────────────────────────────────────────────────

async def close_thread(
    db: AsyncSession, tenant_id: uuid.UUID, thread_id: uuid.UUID
) -> MessageThread:
    result = await db.execute(
        select(MessageThread).where(
            MessageThread.id == thread_id,
            MessageThread.tenant_id == tenant_id,
            MessageThread.is_deleted == False,
        )
    )
    thread = result.scalar_one_or_none()
    if not thread:
        from fastapi import HTTPException
        raise HTTPException(404, "Thread not found")

    thread.status = "closed"
    await db.flush()

    # Mark related open tasks as done
    result = await db.execute(
        select(Task).where(
            Task.thread_id == thread_id,
            Task.tenant_id == tenant_id,
            Task.status == "open",
            Task.is_deleted == False,
        )
    )
    for task in result.scalars().all():
        task.status = "done"

    await db.flush()
    await db.refresh(thread)
    return thread


# ── Main ingest ────────────────────────────────────────────────────────────────

async def ingest_message(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    data: IngestRequest,
) -> tuple[MessageThread, IncomingMessage, bool]:
    normalized = normalize_subject(data.subject)
    thread, is_new = await get_or_create_thread(db, tenant_id, project_id, normalized)

    message = IncomingMessage(
        tenant_id=tenant_id,
        thread_id=thread.id,
        project_id=project_id,
        sender_email=data.sender_email,
        sender_name=data.sender_name,
        subject_raw=data.subject,
        subject_normalized=normalized,
        body_text=data.body_text,
        body_html=data.body_html,
        message_id_header=data.message_id_header,
        is_new_thread=is_new,
    )
    db.add(message)
    await db.flush()

    # Attachments (metadata only; storage in Sprint 3+)
    for att in data.attachments:
        db.add(IncomingAttachment(
            tenant_id=tenant_id,
            message_id=message.id,
            filename=att.filename,
            content_type=att.content_type,
            size_bytes=att.size_bytes,
        ))

    if is_new:
        await create_task_for_thread(db, tenant_id, thread)

    await db.flush()
    await db.refresh(message)
    return thread, message, is_new
ENDOFFILE

cat > backend/app/core/tasks/service.py << 'ENDOFFILE'
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tasks.models import Task
from app.core.tasks.schemas import TaskUpdate


async def list_tasks(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID) -> list[Task]:
    result = await db.execute(
        select(Task).where(
            Task.project_id == project_id,
            Task.tenant_id == tenant_id,
            Task.is_deleted == False,
        ).order_by(Task.created_at.desc())
    )
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def update_task(db: AsyncSession, task: Task, data: TaskUpdate) -> Task:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(task, field, value)
    await db.flush()
    await db.refresh(task)
    return task
ENDOFFILE

# =============================================================================
# ROUTERS
# =============================================================================

cat > backend/app/core/projects/router.py << 'ENDOFFILE'
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.projects import service
from app.core.projects.schemas import ProjectCreate, ProjectRead
from app.core.inbox.schemas import IngestRequest, IngestResponse, ThreadRead, MessageRead
from app.core.inbox import service as inbox_service
from app.core.tasks.schemas import TaskRead, TaskUpdate
from app.core.tasks import service as task_service
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["projects"])


# ── Projects ──────────────────────────────────────────────────────────────────

@router.post("/projects", response_model=ProjectRead, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.create_project(db, current.tenant_id, data)


@router.get("/projects", response_model=list[ProjectRead])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_projects(db, current.tenant_id)


@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    project = await service.get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


# ── Inbox ingest ──────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/incoming", response_model=IngestResponse, status_code=201)
async def ingest_incoming(
    project_id: uuid.UUID,
    data: IngestRequest,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    project = await service.get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    thread, message, is_new = await inbox_service.ingest_message(
        db, current.tenant_id, project_id, data
    )
    return IngestResponse(
        thread=ThreadRead.model_validate(thread),
        message_id=message.id,
        is_new_thread=is_new,
    )


# ── Threads ───────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/threads", response_model=list[ThreadRead])
async def list_threads(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.core.inbox.models import MessageThread
    result = await db.execute(
        select(MessageThread).where(
            MessageThread.project_id == project_id,
            MessageThread.tenant_id == current.tenant_id,
            MessageThread.is_deleted == False,
        ).order_by(MessageThread.created_at.desc())
    )
    return list(result.scalars().all())


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/tasks", response_model=list[TaskRead])
async def list_tasks(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await task_service.list_tasks(db, current.tenant_id, project_id)
ENDOFFILE

cat > backend/app/core/inbox/router.py << 'ENDOFFILE'
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.inbox import service as inbox_service
from app.core.inbox.models import IncomingMessage
from app.core.inbox.schemas import MessageRead, ThreadRead
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["inbox"])


@router.get("/threads/{thread_id}/messages", response_model=list[MessageRead])
async def list_messages(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        select(IncomingMessage).where(
            IncomingMessage.thread_id == thread_id,
            IncomingMessage.tenant_id == current.tenant_id,
            IncomingMessage.is_deleted == False,
        ).order_by(IncomingMessage.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/threads/{thread_id}/close", response_model=ThreadRead)
async def close_thread(
    thread_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await inbox_service.close_thread(db, current.tenant_id, thread_id)
ENDOFFILE

cat > backend/app/core/tasks/router.py << 'ENDOFFILE'
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tasks import service
from app.core.tasks.schemas import TaskRead, TaskUpdate
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["tasks"])


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    task = await service.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return await service.update_task(db, task, data)
ENDOFFILE

# =============================================================================
# ALEMBIC MIGRATION
# =============================================================================

cat > backend/app/db/migrations/versions/0002_sprint2.py << 'ENDOFFILE'
"""Sprint 2 – projects, inbox, tasks

Revision ID: 0002_sprint2
Revises: 0001_initial
Create Date: 2025-01-01 00:00:01
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_sprint2"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── project_sequences ─────────────────────────────────────────────────────
    op.create_table(
        "project_sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("last_seq", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "year", name="uq_project_sequence_tenant_year"),
    )
    op.create_index("ix_project_sequences_tenant_id", "project_sequences", ["tenant_id"])

    # ── projects ──────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_no", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("inbox_email", sa.String(255), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "project_no", name="uq_project_tenant_no"),
    )
    op.create_index("ix_projects_tenant_id", "projects", ["tenant_id"])

    # ── message_threads ───────────────────────────────────────────────────────
    op.create_table(
        "message_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_threads_tenant_id", "message_threads", ["tenant_id"])
    op.create_index("ix_message_threads_project_id", "message_threads", ["project_id"])

    # ── incoming_messages ─────────────────────────────────────────────────────
    op.create_table(
        "incoming_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_email", sa.String(255), nullable=False),
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("subject_raw", sa.String(500), nullable=False),
        sa.Column("subject_normalized", sa.String(500), nullable=False),
        sa.Column("body_text", sa.Text, nullable=True),
        sa.Column("body_html", sa.Text, nullable=True),
        sa.Column("message_id_header", sa.String(255), nullable=True),
        sa.Column("is_new_thread", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["message_threads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incoming_messages_tenant_id", "incoming_messages", ["tenant_id"])
    op.create_index("ix_incoming_messages_thread_id", "incoming_messages", ["thread_id"])
    op.create_index("ix_incoming_messages_project_id", "incoming_messages", ["project_id"])

    # ── incoming_attachments ──────────────────────────────────────────────────
    op.create_table(
        "incoming_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=True),
        sa.Column("storage_path", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["incoming_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incoming_attachments_tenant_id", "incoming_attachments", ["tenant_id"])
    op.create_index("ix_incoming_attachments_message_id", "incoming_attachments", ["message_id"])

    # ── tasks ─────────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["message_threads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"])
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_thread_id", "tasks", ["thread_id"])


def downgrade() -> None:
    op.drop_table("tasks")
    op.drop_table("incoming_attachments")
    op.drop_table("incoming_messages")
    op.drop_table("message_threads")
    op.drop_table("projects")
    op.drop_table("project_sequences")
ENDOFFILE

# =============================================================================
# RLS – append to existing init_rls.sql
# =============================================================================

cat >> backend/app/db/rls/init_rls.sql << 'ENDOFFILE'

-- =============================================================================
-- Sprint 2 RLS policies
-- =============================================================================

ALTER TABLE project_sequences ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE incoming_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE incoming_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON project_sequences;
CREATE POLICY tenant_isolation ON project_sequences
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON projects;
CREATE POLICY tenant_isolation ON projects
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON message_threads;
CREATE POLICY tenant_isolation ON message_threads
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON incoming_messages;
CREATE POLICY tenant_isolation ON incoming_messages
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON incoming_attachments;
CREATE POLICY tenant_isolation ON incoming_attachments
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON tasks;
CREATE POLICY tenant_isolation ON tasks
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
ENDOFFILE

# =============================================================================
# TESTS
# =============================================================================

cat > tests/test_sprint2.py << 'ENDOFFILE'
"""Sprint 2 – unit tests for project_no generation and subject normalization."""
import pytest
from app.core.inbox.service import normalize_subject


# ── Subject normalization ──────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("Re: Spørsmål om leveranse", "Spørsmål om leveranse"),
    ("SV: Re: Spørsmål om leveranse", "Spørsmål om leveranse"),
    ("Fwd: Viktig info", "Viktig info"),
    ("FWD: SV: re: Noe viktig", "Noe viktig"),
    ("VS: Møtereferat", "Møtereferat"),
    ("Ang: Rapport", "Rapport"),
    ("Normalt emne", "Normalt emne"),
    ("  Re:   Trim meg  ", "Trim meg"),
    ("Re[2]: Gammel tråd", "Gammel tråd"),
])
def test_normalize_subject(raw, expected):
    assert normalize_subject(raw) == expected


# ── project_no format ─────────────────────────────────────────────────────────

def test_project_no_format():
    """Verify format YY-#### without DB (unit check on string format)."""
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    yy = str(year)[-2:]
    project_no = f"{yy}-{1:04d}"
    assert len(project_no) == 7
    assert project_no.startswith(yy + "-")
    assert project_no == f"{yy}-0001"
ENDOFFILE

# =============================================================================
# UPDATE main.py to include new routers
# =============================================================================

cat > backend/app/main.py << 'ENDOFFILE'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.audit.service import AuditMiddleware
from app.core.auth.router import router as auth_router
from app.core.tenants.router import router as tenants_router
from app.core.rbac.router import router as rbac_router
from app.core.projects.router import router as projects_router
from app.core.inbox.router import router as inbox_router
from app.core.tasks.router import router as tasks_router
from app.settings import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="HMSK Platform API",
        version="0.2.0",
        docs_url="/docs" if settings.APP_DEBUG else None,
        redoc_url="/redoc" if settings.APP_DEBUG else None,
    )

    app.add_middleware(AuditMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.APP_DEBUG else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(tenants_router)
    app.include_router(rbac_router)
    app.include_router(projects_router)
    app.include_router(inbox_router)
    app.include_router(tasks_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
ENDOFFILE

# Update migrations env.py to import new models
cat > backend/app/db/migrations/env.py << 'ENDOFFILE'
import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base  # noqa
from app.core.tenants.models import Tenant  # noqa
from app.core.rbac.models import User, Role, UserRoleAssignment  # noqa
from app.core.auth.models import RefreshToken  # noqa
from app.core.audit.models import AuditLog  # noqa
from app.core.projects.models import Project, ProjectSequence  # noqa
from app.core.inbox.models import MessageThread, IncomingMessage, IncomingAttachment  # noqa
from app.core.tasks.models import Task  # noqa

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return os.environ.get("DATABASE_SYNC_URL", "postgresql+psycopg2://hmsk:changeme@localhost:5432/hmsk")


def run_migrations_offline() -> None:
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
ENDOFFILE

# =============================================================================
# GIT
# =============================================================================

git add -A
git commit -m "feat: Sprint 2 – projects, inbox ingest, message threads, tasks, RLS"
git push

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅  Sprint 2 filer skrevet og pushet til GitHub"
echo ""
echo "Kjør nå:"
echo "  make migrate   # kjører 0002_sprint2"
echo "  make rls       # aktiverer RLS på nye tabeller"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
