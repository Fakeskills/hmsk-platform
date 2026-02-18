import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.inbox import service as inbox_service
from app.core.inbox.models import IncomingMessage
from app.core.inbox.schemas import MessageRead, ThreadRead
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["inbox"])

@router.get("/threads/{thread_id}/messages", response_model=list[MessageRead])
async def list_messages(thread_id: uuid.UUID, db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    result = await db.execute(
        select(IncomingMessage).where(
            IncomingMessage.thread_id == thread_id,
            IncomingMessage.tenant_id == current.tenant_id,
            IncomingMessage.is_deleted == False,
        ).order_by(IncomingMessage.created_at.asc())
    )
    return list(result.scalars().all())

@router.post("/threads/{thread_id}/close", response_model=ThreadRead)
async def close_thread(thread_id: uuid.UUID, db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return await inbox_service.close_thread(db, current.tenant_id, thread_id)
