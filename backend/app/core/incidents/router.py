import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.incidents import service
from app.core.incidents.schemas import (
    IncidentCreate, IncidentRead, IncidentTriageUpdate,
    IncidentMessageCreate, IncidentMessageRead,
)
from app.core.files.schemas import FileCreate
from app.core.files.service import create_file, link_file
from app.core.projects.service import get_project
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["incidents"])


@router.post("/projects/{project_id}/incidents", response_model=IncidentRead, status_code=201)
async def create_incident(
    project_id: uuid.UUID,
    data: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return await service.create_incident(db, current.tenant_id, project_id, data, current.user_id)


@router.get("/projects/{project_id}/incidents", response_model=list[IncidentRead])
async def list_incidents(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_incidents(db, current.tenant_id, project_id)


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
async def get_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    incident = await service.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident


@router.post("/incidents/{incident_id}/submit", response_model=IncidentRead)
async def submit_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    incident = await service.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return await service.transition_incident(db, incident, "submitted")


@router.post("/incidents/{incident_id}/triage", response_model=IncidentRead)
async def triage_incident(
    incident_id: uuid.UUID,
    data: IncidentTriageUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    incident = await service.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    await service.triage_incident(db, incident, data)
    return await service.transition_incident(db, incident, "triage")


@router.post("/incidents/{incident_id}/close", response_model=IncidentRead)
async def close_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    incident = await service.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    if incident.status == "triage":
        await service.transition_incident(db, incident, "open")
    return await service.transition_incident(db, incident, "closed")


@router.post("/incidents/{incident_id}/reveal-reporter", response_model=IncidentRead)
async def reveal_reporter(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    incident = await service.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return await service.reveal_reporter(db, incident, current.user_id, current.tenant_id)


@router.post("/incidents/{incident_id}/messages", response_model=IncidentMessageRead, status_code=201)
async def add_message(
    incident_id: uuid.UUID,
    data: IncidentMessageCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    incident = await service.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return await service.add_message(db, current.tenant_id, incident, data, current.user_id)


@router.get("/incidents/{incident_id}/messages", response_model=list[IncidentMessageRead])
async def list_messages(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_messages(db, current.tenant_id, incident_id)


@router.post("/incidents/{incident_id}/files", status_code=201)
async def attach_file(
    incident_id: uuid.UUID,
    data: FileCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    incident = await service.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    f = await create_file(db, current.tenant_id, data, current.user_id)
    await link_file(db, current.tenant_id, f.id, "incident", incident_id)
    return {"file_id": f.id, "filename": f.filename}


@router.post("/incidents/{incident_id}/create-nonconformance", status_code=201)
async def create_nc_from_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    incident = await service.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    from app.core.nonconformance.service import create_nc_from_incident
    from app.core.nonconformance.schemas import NonconformanceRead
    nc = await create_nc_from_incident(
        db, current.tenant_id, incident_id,
        incident.project_id, incident.title, incident.description,
        owner_user_id=current.user_id,
    )
    return NonconformanceRead.model_validate(nc)
