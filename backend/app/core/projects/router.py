import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.projects import service
from app.core.projects.schemas import ProjectCreate, ProjectRead
from app.core.inbox.schemas import IngestRequest, IngestResponse, ThreadRead
from app.core.inbox import service as inbox_service
from app.core.inbox.models import MessageThread
from app.core.tasks.schemas import TaskRead
from app.core.tasks import service as task_service
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["projects"])

@router.post("/projects", response_model=ProjectRead, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return await service.create_project(db, current.tenant_id, data)

@router.get("/projects", response_model=list[ProjectRead])
async def list_projects(db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return await service.list_projects(db, current.tenant_id)

@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    project = await service.get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project

@router.post("/projects/{project_id}/incoming", response_model=IngestResponse, status_code=201)
async def ingest_incoming(project_id: uuid.UUID, data: IngestRequest, db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    project = await service.get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    thread, message, is_new = await inbox_service.ingest_message(db, current.tenant_id, project_id, data)
    return IngestResponse(thread=ThreadRead.model_validate(thread), message_id=message.id, is_new_thread=is_new)

@router.get("/projects/{project_id}/threads", response_model=list[ThreadRead])
async def list_threads(project_id: uuid.UUID, db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    result = await db.execute(
        select(MessageThread).where(
            MessageThread.project_id == project_id,
            MessageThread.tenant_id == current.tenant_id,
            MessageThread.is_deleted == False,
        ).order_by(MessageThread.created_at.desc())
    )
    return list(result.scalars().all())

@router.get("/projects/{project_id}/tasks", response_model=list[TaskRead])
async def list_tasks(project_id: uuid.UUID, db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return await task_service.list_tasks(db, current.tenant_id, project_id)
