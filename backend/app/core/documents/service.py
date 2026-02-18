import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.documents.models import (
    DocTemplate, DocTemplateVersion,
    ProjectDoc, ProjectDocVersion,
    AckRequest, AckResponse,
)
from app.core.documents.schemas import (
    DocTemplateCreate, DocTemplateVersionCreate,
    ProjectDocCreate, ProjectDocVersionCreate,
    AckResponseCreate, IssueRequest,
)


# ── Library ───────────────────────────────────────────────────────────────────

async def create_template(
    db: AsyncSession, tenant_id: uuid.UUID, data: DocTemplateCreate, created_by: uuid.UUID
) -> DocTemplate:
    t = DocTemplate(tenant_id=tenant_id, created_by=created_by, **data.model_dump())
    db.add(t)
    await db.flush()
    await db.refresh(t)
    return t


async def get_template(db: AsyncSession, template_id: uuid.UUID) -> DocTemplate | None:
    result = await db.execute(
        select(DocTemplate).where(DocTemplate.id == template_id, DocTemplate.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def list_templates(db: AsyncSession, tenant_id: uuid.UUID) -> list[DocTemplate]:
    result = await db.execute(
        select(DocTemplate).where(DocTemplate.tenant_id == tenant_id, DocTemplate.is_deleted == False)
        .order_by(DocTemplate.created_at.desc())
    )
    return list(result.scalars().all())


async def create_template_version(
    db: AsyncSession, tenant_id: uuid.UUID, template: DocTemplate, data: DocTemplateVersionCreate
) -> DocTemplateVersion:
    result = await db.execute(
        select(func.max(DocTemplateVersion.version_no))
        .where(DocTemplateVersion.template_id == template.id)
    )
    last = result.scalar_one_or_none() or 0
    v = DocTemplateVersion(
        tenant_id=tenant_id,
        template_id=template.id,
        version_no=last + 1,
        content=data.content,
        change_summary=data.change_summary,
        status="draft",
    )
    db.add(v)
    await db.flush()
    await db.refresh(v)
    return v


async def publish_template_version(
    db: AsyncSession, version: DocTemplateVersion, published_by: uuid.UUID, tenant_id: uuid.UUID
) -> DocTemplateVersion:
    from fastapi import HTTPException
    if version.status != "draft":
        raise HTTPException(400, f"Cannot publish version with status '{version.status}'")

    # Supersede previous published version
    result = await db.execute(
        select(DocTemplateVersion).where(
            DocTemplateVersion.template_id == version.template_id,
            DocTemplateVersion.status == "published",
            DocTemplateVersion.id != version.id,
        )
    )
    for old in result.scalars().all():
        old.status = "superseded"

    version.status = "published"
    version.published_at = datetime.now(timezone.utc)
    version.published_by = published_by

    # Update template status
    result = await db.execute(
        select(DocTemplate).where(DocTemplate.id == version.template_id)
    )
    template = result.scalar_one_or_none()
    if template:
        template.status = "published"

    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=published_by,
        action="doc_template.published", resource_type="doc_template_version",
        resource_id=str(version.id),
        detail={"version_no": version.version_no},
    )
    await db.refresh(version)
    return version


# ── Project docs ──────────────────────────────────────────────────────────────

async def generate_doc_no(
    db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID
) -> str:
    year = datetime.now(timezone.utc).year
    yy = str(year)[-2:]
    result = await db.execute(
        select(func.count(ProjectDoc.id)).where(
            ProjectDoc.tenant_id == tenant_id,
            ProjectDoc.project_id == project_id,
        )
    )
    count = result.scalar_one() or 0
    return f"DOC-{yy}-{count + 1:04d}"


async def create_project_doc(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    data: ProjectDocCreate,
    owner_user_id: uuid.UUID,
) -> tuple[ProjectDoc, ProjectDocVersion]:
    # Resolve template linkage
    template_id = None
    content = data.content

    if data.template_version_id:
        result = await db.execute(
            select(DocTemplateVersion).where(DocTemplateVersion.id == data.template_version_id)
        )
        tv = result.scalar_one_or_none()
        if tv:
            template_id = tv.template_id
            if content is None:
                content = tv.content

    doc_no = await generate_doc_no(db, tenant_id, project_id)
    doc = ProjectDoc(
        tenant_id=tenant_id,
        project_id=project_id,
        template_id=template_id,
        template_version_id=data.template_version_id,
        title=data.title,
        doc_no=doc_no,
        doc_type=data.doc_type,
        status="draft",
        owner_user_id=owner_user_id,
    )
    db.add(doc)
    await db.flush()

    version = ProjectDocVersion(
        tenant_id=tenant_id,
        doc_id=doc.id,
        version_no=1,
        content=content,
        status="draft",
        requires_ack=False,
    )
    db.add(version)
    await db.flush()
    await db.refresh(doc)
    await db.refresh(version)
    return doc, version


async def get_project_doc(db: AsyncSession, doc_id: uuid.UUID) -> ProjectDoc | None:
    result = await db.execute(
        select(ProjectDoc).where(ProjectDoc.id == doc_id, ProjectDoc.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def list_project_docs(
    db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID
) -> list[ProjectDoc]:
    result = await db.execute(
        select(ProjectDoc).where(
            ProjectDoc.tenant_id == tenant_id,
            ProjectDoc.project_id == project_id,
            ProjectDoc.is_deleted == False,
        ).order_by(ProjectDoc.created_at.desc())
    )
    return list(result.scalars().all())


async def create_doc_version(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    doc: ProjectDoc,
    data: ProjectDocVersionCreate,
) -> ProjectDocVersion:
    from fastapi import HTTPException
    if doc.status == "issued":
        raise HTTPException(400, "Cannot add version to issued document")

    result = await db.execute(
        select(func.max(ProjectDocVersion.version_no))
        .where(ProjectDocVersion.doc_id == doc.id)
    )
    last = result.scalar_one_or_none() or 0

    v = ProjectDocVersion(
        tenant_id=tenant_id,
        doc_id=doc.id,
        version_no=last + 1,
        content=data.content,
        change_summary=data.change_summary,
        status="draft",
        requires_ack=data.requires_ack,
    )
    db.add(v)
    await db.flush()
    await db.refresh(v)
    return v


async def get_doc_version(db: AsyncSession, version_id: uuid.UUID) -> ProjectDocVersion | None:
    result = await db.execute(
        select(ProjectDocVersion).where(
            ProjectDocVersion.id == version_id, ProjectDocVersion.is_deleted == False
        )
    )
    return result.scalar_one_or_none()


async def list_doc_versions(
    db: AsyncSession, doc_id: uuid.UUID
) -> list[ProjectDocVersion]:
    result = await db.execute(
        select(ProjectDocVersion).where(
            ProjectDocVersion.doc_id == doc_id,
            ProjectDocVersion.is_deleted == False,
        ).order_by(ProjectDocVersion.version_no.desc())
    )
    return list(result.scalars().all())


async def approve_doc_version(
    db: AsyncSession,
    version: ProjectDocVersion,
    approved_by: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ProjectDocVersion:
    from fastapi import HTTPException
    if version.status not in ("draft", "under_review"):
        raise HTTPException(400, f"Cannot approve version with status '{version.status}'")

    version.status = "approved"
    version.approved_at = datetime.now(timezone.utc)
    version.approved_by = approved_by
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=approved_by,
        action="project_doc.approved", resource_type="project_doc_version",
        resource_id=str(version.id),
        detail={"version_no": version.version_no},
    )
    await db.refresh(version)
    return version


async def issue_doc_version(
    db: AsyncSession,
    version: ProjectDocVersion,
    issued_by: uuid.UUID,
    tenant_id: uuid.UUID,
    data: IssueRequest,
) -> ProjectDocVersion:
    from fastapi import HTTPException
    if version.status != "approved":
        raise HTTPException(400, f"Cannot issue version with status '{version.status}'. Must be approved first.")

    now = datetime.now(timezone.utc)

    # Supersede previous issued version
    result = await db.execute(
        select(ProjectDocVersion).where(
            ProjectDocVersion.doc_id == version.doc_id,
            ProjectDocVersion.status == "issued",
            ProjectDocVersion.id != version.id,
        )
    )
    for old in result.scalars().all():
        old.status = "superseded"

    version.status = "issued"
    version.issued_at = now
    version.issued_by = issued_by
    await db.flush()

    # Update parent doc status
    result = await db.execute(
        select(ProjectDoc).where(ProjectDoc.id == version.doc_id)
    )
    doc = result.scalar_one_or_none()
    if doc:
        doc.status = "issued"

    # Auto-create ack requests
    if version.requires_ack and data.ack_user_ids:
        for user_id in data.ack_user_ids:
            db.add(AckRequest(
                tenant_id=tenant_id,
                doc_version_id=version.id,
                project_id=doc.project_id if doc else version.doc_id,
                user_id=user_id,
                status="pending",
            ))

    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=issued_by,
        action="project_doc.issued", resource_type="project_doc_version",
        resource_id=str(version.id),
        detail={"version_no": version.version_no, "ack_count": len(data.ack_user_ids)},
    )
    await db.refresh(version)
    return version


# ── Acknowledgements ──────────────────────────────────────────────────────────

async def acknowledge(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    ack_request_id: uuid.UUID,
    user_id: uuid.UUID,
    data: AckResponseCreate,
) -> AckResponse:
    from fastapi import HTTPException
    result = await db.execute(
        select(AckRequest).where(
            AckRequest.id == ack_request_id,
            AckRequest.tenant_id == tenant_id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Ack request not found")
    if req.user_id != user_id:
        raise HTTPException(403, "You can only acknowledge your own requests")
    if req.status == "acknowledged":
        raise HTTPException(400, "Already acknowledged")

    req.status = "acknowledged"
    response = AckResponse(
        tenant_id=tenant_id,
        ack_request_id=ack_request_id,
        user_id=user_id,
        acknowledged_at=datetime.now(timezone.utc),
        comment=data.comment,
    )
    db.add(response)
    await db.flush()
    await db.refresh(response)
    return response


async def get_ack_report(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    doc_version_id: uuid.UUID,
) -> list[dict]:
    result = await db.execute(
        select(AckRequest).where(
            AckRequest.doc_version_id == doc_version_id,
            AckRequest.tenant_id == tenant_id,
        )
    )
    rows = []
    for req in result.scalars().all():
        resp_result = await db.execute(
            select(AckResponse).where(AckResponse.ack_request_id == req.id)
        )
        resp = resp_result.scalar_one_or_none()
        rows.append({
            "user_id": req.user_id,
            "status": req.status,
            "acknowledged_at": resp.acknowledged_at if resp else None,
        })
    return rows
