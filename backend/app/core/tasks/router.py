import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.tasks import service
from app.core.tasks.schemas import TaskRead, TaskUpdate
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["tasks"])

@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(task_id: uuid.UUID, data: TaskUpdate, db: AsyncSession = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    task = await service.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return await service.update_task(db, task, data)
