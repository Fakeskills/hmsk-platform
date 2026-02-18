import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.checklists import service
from app.core.checklists.schemas import (
    ChecklistTemplateCreate, ChecklistTemplateRead,
    ChecklistTemplateVersionCreate, ChecklistTemplateVersionRead,
    ChecklistImportRequest,
    ProjectChecklistTemplateRead, ProjectChecklistTemplateVersionRead,
    ChecklistRunCreate, ChecklistRunUpdate, ChecklistRunRead,
    ChecklistRunSubmit, ChecklistRunReject,
)
from app.core.checklists.models import (
    ChecklistTemplateVersion, ProjectChecklistTemplateVersion, ChecklistRun
)
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["checklists"])


# ── Library templates ─────────────────────────────────────────────────────────

@router.post("/library/checklists", response_model=ChecklistTemplateRead, status_code=201)
async def create_template(
    data: ChecklistTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.create_template(db, current.tenant_id, data, current.user_id)


@router.get("/library/checklists", response_model=list[ChecklistTemplateRead])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_templates(db, current.tenant_id)


@router.get("/library/checklists/{template_id}", response_model=ChecklistTemplateRead)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    t = await service.get_template(db, template_id)
    if not t:
        raise HTTPException(404, "Checklist template not found")
    return t


@router.post("/library/checklists/{template_id}/versions", response_model=ChecklistTemplateVersionRead, status_code=201)
async def create_template_version(
    template_id: uuid.UUID,
    data: ChecklistTemplateVersionCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    t = await service.get_template(db, template_id)
    if not t:
        raise HTTPException(404, "Checklist template not found")
    return await service.create_template_version(db, current.tenant_id, t, data)


@router.get("/library/checklists/{template_id}/versions", response_model=list[ChecklistTemplateVersionRead])
async def list_template_versions(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    return await service.list_template_versions(db, template_id)


@router.post("/library/checklist-versions/{version_id}/publish", response_model=ChecklistTemplateVersionRead)
async def publish_template_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    version = await service.get_template_version(db, version_id)
    if not version:
        raise HTTPException(404, "Version not found")
    return await service.publish_template_version(db, version, current.user_id, current.tenant_id)


# ── Project import ────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/checklists/import", response_model=ProjectChecklistTemplateRead, status_code=201)
async def import_checklist(
    project_id: uuid.UUID,
    data: ChecklistImportRequest,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    checklist, _ = await service.import_checklist_to_project(
        db, current.tenant_id, project_id, data
    )
    return checklist


@router.get("/projects/{project_id}/checklists", response_model=list[ProjectChecklistTemplateRead])
async def list_project_checklists(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_project_checklists(db, current.tenant_id, project_id)


@router.get("/projects/{project_id}/checklists/{checklist_id}", response_model=ProjectChecklistTemplateRead)
async def get_project_checklist(
    project_id: uuid.UUID,
    checklist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    c = await service.get_project_checklist(db, checklist_id)
    if not c:
        raise HTTPException(404, "Checklist not found")
    return c


@router.get("/projects/{project_id}/checklists/{checklist_id}/versions", response_model=list[ProjectChecklistTemplateVersionRead])
async def list_checklist_versions(
    project_id: uuid.UUID,
    checklist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        select(ProjectChecklistTemplateVersion).where(
            ProjectChecklistTemplateVersion.checklist_id == checklist_id,
            ProjectChecklistTemplateVersion.is_deleted == False,
        ).order_by(ProjectChecklistTemplateVersion.version_no.desc())
    )
    return list(result.scalars().all())


# ── Runs ──────────────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/checklist-runs", response_model=ChecklistRunRead, status_code=201)
async def create_run(
    project_id: uuid.UUID,
    data: ChecklistRunCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.create_run(db, current.tenant_id, project_id, data, current.user_id)


@router.get("/projects/{project_id}/checklist-runs", response_model=list[ChecklistRunRead])
async def list_runs(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_runs(db, current.tenant_id, project_id)


@router.get("/checklist-runs/{run_id}", response_model=ChecklistRunRead)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    run = await service.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.patch("/checklist-runs/{run_id}", response_model=ChecklistRunRead)
async def update_run(
    run_id: uuid.UUID,
    data: ChecklistRunUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    run = await service.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return await service.update_run_answers(db, run, data)


@router.post("/checklist-runs/{run_id}/submit", response_model=ChecklistRunRead)
async def submit_run(
    run_id: uuid.UUID,
    data: ChecklistRunSubmit,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    run = await service.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return await service.submit_run(db, run, data, current.tenant_id, current.user_id)


@router.post("/checklist-runs/{run_id}/approve", response_model=ChecklistRunRead)
async def approve_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    run = await service.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return await service.approve_run(db, run, current.user_id, current.tenant_id)


@router.post("/checklist-runs/{run_id}/reject", response_model=ChecklistRunRead)
async def reject_run(
    run_id: uuid.UUID,
    data: ChecklistRunReject,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    run = await service.get_run(db, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return await service.reject_run(db, run, current.user_id, current.tenant_id, data)
