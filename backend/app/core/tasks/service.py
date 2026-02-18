import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.tasks.models import Task
from app.core.tasks.schemas import TaskUpdate

async def list_tasks(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID) -> list[Task]:
    result = await db.execute(
        select(Task).where(Task.project_id == project_id, Task.tenant_id == tenant_id, Task.is_deleted == False)
        .order_by(Task.created_at.desc())
    )
    return list(result.scalars().all())

async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id, Task.is_deleted == False))
    return result.scalar_one_or_none()

async def update_task(db: AsyncSession, task: Task, data: TaskUpdate) -> Task:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(task, field, value)
    await db.flush()
    await db.refresh(task)
    return task
