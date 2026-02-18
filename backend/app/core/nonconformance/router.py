import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.nonconformance import service
from app.core.nonconformance.schemas import (
    NonconformanceCreate, NonconformanceRead, NonconformanceUpdate,
    CapaActionCreate, CapaActionRead, CapaActionUpdate, CapaTransitionRequest,
)
from app.core.projects.service import get_project
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["nonconformances"])


@router.post("/projects/{project_id}/nonconformances", response_model=NonconformanceRead, status_code=201)
async def create_nc(
    project_id: uuid.UUID,
    data: NonconformanceCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if data.owner_user_id is None:
        data.owner_user_id = current.user_id
    return await service.create_nc(db, current.tenant_id, project_id, data)


@router.get("/projects/{project_id}/nonconformances", response_model=list[NonconformanceRead])
async def list_ncs(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_ncs(db, current.tenant_id, project_id)


@router.get("/nonconformances/{nc_id}", response_model=NonconformanceRead)
async def get_nc(
    nc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    nc = await service.get_nc(db, nc_id)
    if not nc:
        raise HTTPException(404, "Nonconformance not found")
    return nc


@router.patch("/nonconformances/{nc_id}", response_model=NonconformanceRead)
async def update_nc(
    nc_id: uuid.UUID,
    data: NonconformanceUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    nc = await service.get_nc(db, nc_id)
    if not nc:
        raise HTTPException(404, "Nonconformance not found")
    return await service.update_nc(db, nc, data, current.user_id, current.tenant_id)


@router.post("/nonconformances/{nc_id}/actions", response_model=CapaActionRead, status_code=201)
async def create_capa(
    nc_id: uuid.UUID,
    data: CapaActionCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    nc = await service.get_nc(db, nc_id)
    if not nc:
        raise HTTPException(404, "Nonconformance not found")
    return await service.create_capa(db, current.tenant_id, nc, data)


@router.get("/nonconformances/{nc_id}/actions", response_model=list[CapaActionRead])
async def list_capas(
    nc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_capas(db, current.tenant_id, nc_id)


@router.patch("/nonconformances/{nc_id}/actions/{action_id}", response_model=CapaActionRead)
async def update_capa(
    nc_id: uuid.UUID,
    action_id: uuid.UUID,
    data: CapaActionUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    from app.core.nonconformance.models import CapaAction
    result = await db.execute(
        select(CapaAction).where(
            CapaAction.id == action_id,
            CapaAction.nonconformance_id == nc_id,
            CapaAction.is_deleted == False,
        )
    )
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(404, "Action not found")
    return await service.update_capa(db, action, data)


@router.post("/nonconformances/{nc_id}/actions/{action_id}/transition", response_model=CapaActionRead)
async def transition_capa(
    nc_id: uuid.UUID,
    action_id: uuid.UUID,
    data: CapaTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    from app.core.nonconformance.models import CapaAction
    result = await db.execute(
        select(CapaAction).where(
            CapaAction.id == action_id,
            CapaAction.nonconformance_id == nc_id,
            CapaAction.is_deleted == False,
        )
    )
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(404, "Action not found")
    return await service.transition_capa(db, action, data.to_status, current.user_id, current.tenant_id)
