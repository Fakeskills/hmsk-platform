import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.documents import service
from app.core.documents.schemas import (
    DocTemplateCreate, DocTemplateRead,
    DocTemplateVersionCreate, DocTemplateVersionRead,
    ProjectDocCreate, ProjectDocRead,
    ProjectDocVersionCreate, ProjectDocVersionRead,
    AckRequestRead, AckResponseCreate, AckResponseRead,
    AckReportRow, IssueRequest,
)
from app.core.documents.models import DocTemplateVersion, ProjectDocVersion
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["documents"])


# ── Library templates ─────────────────────────────────────────────────────────

@router.post("/library/templates", response_model=DocTemplateRead, status_code=201)
async def create_template(
    data: DocTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.create_template(db, current.tenant_id, data, current.user_id)


@router.get("/library/templates", response_model=list[DocTemplateRead])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_templates(db, current.tenant_id)


@router.get("/library/templates/{template_id}", response_model=DocTemplateRead)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    t = await service.get_template(db, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    return t


@router.post("/library/templates/{template_id}/versions", response_model=DocTemplateVersionRead, status_code=201)
async def create_template_version(
    template_id: uuid.UUID,
    data: DocTemplateVersionCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    t = await service.get_template(db, template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    return await service.create_template_version(db, current.tenant_id, t, data)


@router.get("/library/templates/{template_id}/versions", response_model=list[DocTemplateVersionRead])
async def list_template_versions(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        select(DocTemplateVersion).where(
            DocTemplateVersion.template_id == template_id,
            DocTemplateVersion.is_deleted == False,
        ).order_by(DocTemplateVersion.version_no.desc())
    )
    return list(result.scalars().all())


@router.post("/library/templates/{template_id}/versions/{version_id}/publish", response_model=DocTemplateVersionRead)
async def publish_template_version(
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    # Only superadmin / HMSK-leder can publish
    if not current.user.is_superadmin:
        raise HTTPException(403, "Only HMSK-leder can publish template versions")
    result = await db.execute(
        select(DocTemplateVersion).where(
            DocTemplateVersion.id == version_id,
            DocTemplateVersion.template_id == template_id,
            DocTemplateVersion.is_deleted == False,
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(404, "Version not found")
    return await service.publish_template_version(db, version, current.user_id, current.tenant_id)


# ── Project docs ──────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/docs", response_model=ProjectDocRead, status_code=201)
async def create_project_doc(
    project_id: uuid.UUID,
    data: ProjectDocCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    doc, _ = await service.create_project_doc(db, current.tenant_id, project_id, data, current.user_id)
    return doc


@router.get("/projects/{project_id}/docs", response_model=list[ProjectDocRead])
async def list_project_docs(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_project_docs(db, current.tenant_id, project_id)


@router.get("/projects/{project_id}/docs/{doc_id}", response_model=ProjectDocRead)
async def get_project_doc(
    project_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    doc = await service.get_project_doc(db, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/projects/{project_id}/docs/{doc_id}/versions", response_model=list[ProjectDocVersionRead])
async def list_doc_versions(
    project_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    return await service.list_doc_versions(db, doc_id)


@router.post("/projects/{project_id}/docs/{doc_id}/versions", response_model=ProjectDocVersionRead, status_code=201)
async def create_doc_version(
    project_id: uuid.UUID,
    doc_id: uuid.UUID,
    data: ProjectDocVersionCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    doc = await service.get_project_doc(db, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return await service.create_doc_version(db, current.tenant_id, doc, data)


# ── Approval + Issue ──────────────────────────────────────────────────────────

@router.post("/doc-versions/{version_id}/approve", response_model=ProjectDocVersionRead)
async def approve_doc_version(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    version = await service.get_doc_version(db, version_id)
    if not version:
        raise HTTPException(404, "Version not found")
    return await service.approve_doc_version(db, version, current.user_id, current.tenant_id)


@router.post("/doc-versions/{version_id}/issue", response_model=ProjectDocVersionRead)
async def issue_doc_version(
    version_id: uuid.UUID,
    data: IssueRequest,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    version = await service.get_doc_version(db, version_id)
    if not version:
        raise HTTPException(404, "Version not found")
    return await service.issue_doc_version(db, version, current.user_id, current.tenant_id, data)


# ── Acknowledgements ──────────────────────────────────────────────────────────

@router.post("/ack-requests/{ack_request_id}/acknowledge", response_model=AckResponseRead)
async def acknowledge(
    ack_request_id: uuid.UUID,
    data: AckResponseCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.acknowledge(db, current.tenant_id, ack_request_id, current.user_id, data)


@router.get("/doc-versions/{version_id}/ack-report", response_model=list[AckReportRow])
async def ack_report(
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    rows = await service.get_ack_report(db, current.tenant_id, version_id)
    return [AckReportRow(**r) for r in rows]
