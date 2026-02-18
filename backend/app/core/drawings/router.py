import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.drawings import service
from app.core.drawings.schemas import (
    DrawingCreate, DrawingRead, DrawingFromInboxRequest,
)
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["drawings"])


@router.post("/projects/{project_id}/drawings", response_model=DrawingRead, status_code=201)
async def register_drawing(
    project_id: uuid.UUID,
    data: DrawingCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.register_drawing(
        db, current.tenant_id, project_id, data, current.user_id
    )


@router.get("/projects/{project_id}/drawings", response_model=list[DrawingRead])
async def list_drawings(
    project_id: uuid.UUID,
    only_active: bool = Query(False),
    discipline: str | None = Query(None),
    drawing_no: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_drawings(
        db, current.tenant_id, project_id,
        only_active=only_active,
        discipline=discipline,
        drawing_no=drawing_no,
        status=status,
    )


@router.get("/projects/{project_id}/drawings/{drawing_id}", response_model=DrawingRead)
async def get_drawing(
    project_id: uuid.UUID,
    drawing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    drawing = await service.get_drawing(db, drawing_id)
    if not drawing:
        raise HTTPException(404, "Drawing not found")
    return drawing


@router.post("/projects/{project_id}/drawings/from-inbox", response_model=DrawingRead, status_code=201)
async def register_from_inbox(
    project_id: uuid.UUID,
    data: DrawingFromInboxRequest,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.register_from_inbox(
        db, current.tenant_id, project_id, data, current.user_id
    )
