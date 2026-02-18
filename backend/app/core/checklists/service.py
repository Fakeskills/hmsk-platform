import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.checklists.models import (
    ChecklistTemplate, ChecklistTemplateVersion,
    ProjectChecklistTemplate, ProjectChecklistTemplateVersion,
    ChecklistRun,
)
from app.core.checklists.schemas import (
    ChecklistTemplateCreate, ChecklistTemplateVersionCreate,
    ChecklistImportRequest, ChecklistRunCreate,
    ChecklistRunUpdate, ChecklistRunReject, ChecklistRunSubmit,
)

PERMISSION_CHECKLIST_PUBLISH = "checklist_template:publish"

# Fix #1 – extended status values
VALID_TEMPLATE_VERSION_STATUSES = {"draft", "in_review", "published", "superseded", "obsolete"}
IMMUTABLE_TEMPLATE_VERSION_STATUSES = {"published", "superseded", "obsolete"}


# ── Permission helper ─────────────────────────────────────────────────────────

async def _has_permission(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, permission: str
) -> bool:
    from app.core.rbac.models import User, Role, UserRoleAssignment
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and user.is_superadmin:
        return True
    result = await db.execute(
        select(Role.permissions)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .where(
            UserRoleAssignment.tenant_id == tenant_id,
            UserRoleAssignment.user_id == user_id,
            Role.is_deleted == False,
        )
    )
    for (perms,) in result.all():
        if perms and permission in [p.strip() for p in perms.split(",")]:
            return True
    return False


# ── Immutability guards ───────────────────────────────────────────────────────

def _assert_template_version_mutable(version: ChecklistTemplateVersion) -> None:
    from fastapi import HTTPException
    if version.status in IMMUTABLE_TEMPLATE_VERSION_STATUSES:
        raise HTTPException(400, f"Checklist template version is '{version.status}' and immutable")


# Fix #4 – guard active project checklist versions
def _assert_project_version_mutable(version: ProjectChecklistTemplateVersion) -> None:
    from fastapi import HTTPException
    if version.status in ("active", "approved"):
        raise HTTPException(
            400,
            f"Project checklist version is '{version.status}' and immutable. Create a new version instead."
        )


# ── Schema validation ─────────────────────────────────────────────────────────

def _parse_schema(schema_json: str) -> list[dict]:
    from fastapi import HTTPException
    try:
        fields = json.loads(schema_json)
    except Exception:
        raise HTTPException(400, "schema_json must be valid JSON")
    if not isinstance(fields, list):
        raise HTTPException(400, "schema_json must be a JSON array")
    for f in fields:
        if "id" not in f or "label" not in f or "field_type" not in f:
            raise HTTPException(400, f"Field missing required keys (id, label, field_type): {f}")
        if f["field_type"] not in ("yes_no", "text", "number", "date", "photo"):
            raise HTTPException(400, f"Invalid field_type '{f['field_type']}'")
    return fields


def _validate_answers(
    schema: list[dict],
    answers: dict,
    file_ids_by_field: dict[str, list],
) -> list[str]:
    errors = []
    for field in schema:
        fid = field["id"]
        answer = answers.get(fid, {})
        value = answer.get("value")
        file_ids = answer.get("file_ids", [])

        if field.get("required") and (value is None or value == ""):
            errors.append(f"Field '{field['label']}' is required")

        if field.get("requires_image") and not file_ids:
            errors.append(f"Field '{field['label']}' requires at least 1 image")

    return errors


# ── NC default assignee ───────────────────────────────────────────────────────

async def _resolve_nc_assignee(
    db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID
) -> uuid.UUID | None:
    from app.core.rbac.models import Role, User, UserRoleAssignment
    for role_name in ("anleggsleder", "prosjektleder"):
        result = await db.execute(
            select(UserRoleAssignment.user_id)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .join(User, User.id == UserRoleAssignment.user_id)
            .where(
                UserRoleAssignment.tenant_id == tenant_id,
                Role.tenant_id == tenant_id,
                Role.name.ilike(role_name),
                Role.is_deleted == False,
                User.is_deleted == False,
                User.status == "active",
            ).limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            return row
    return None


# ── Library ───────────────────────────────────────────────────────────────────

async def generate_checklist_no(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    result = await db.execute(
        select(func.count(ChecklistTemplate.id)).where(
            ChecklistTemplate.tenant_id == tenant_id,
        )
    )
    count = result.scalar_one() or 0
    return f"CL-{count + 1:03d}"


async def create_template(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: ChecklistTemplateCreate,
    owner_user_id: uuid.UUID,
) -> ChecklistTemplate:
    checklist_no = await generate_checklist_no(db, tenant_id)
    t = ChecklistTemplate(
        tenant_id=tenant_id,
        checklist_no=checklist_no,
        title=data.title,
        description=data.description,
        category=data.category,
        status="draft",
        owner_user_id=owner_user_id,
    )
    db.add(t)
    await db.flush()
    await db.refresh(t)
    return t


async def get_template(db: AsyncSession, template_id: uuid.UUID) -> ChecklistTemplate | None:
    result = await db.execute(
        select(ChecklistTemplate).where(
            ChecklistTemplate.id == template_id,
            ChecklistTemplate.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_templates(db: AsyncSession, tenant_id: uuid.UUID) -> list[ChecklistTemplate]:
    result = await db.execute(
        select(ChecklistTemplate).where(
            ChecklistTemplate.tenant_id == tenant_id,
            ChecklistTemplate.is_deleted == False,
        ).order_by(ChecklistTemplate.checklist_no)
    )
    return list(result.scalars().all())


async def create_template_version(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    template: ChecklistTemplate,
    data: ChecklistTemplateVersionCreate,
) -> ChecklistTemplateVersion:
    _parse_schema(data.schema_json)
    result = await db.execute(
        select(func.max(ChecklistTemplateVersion.version_no))
        .where(ChecklistTemplateVersion.template_id == template.id)
    )
    last = result.scalar_one_or_none() or 0
    v = ChecklistTemplateVersion(
        tenant_id=tenant_id,
        template_id=template.id,
        version_no=last + 1,
        schema_json=data.schema_json,
        change_summary=data.change_summary,
        status="draft",
    )
    db.add(v)
    await db.flush()
    await db.refresh(v)
    return v


async def get_template_version(
    db: AsyncSession, version_id: uuid.UUID
) -> ChecklistTemplateVersion | None:
    result = await db.execute(
        select(ChecklistTemplateVersion).where(
            ChecklistTemplateVersion.id == version_id,
            ChecklistTemplateVersion.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_template_versions(
    db: AsyncSession, template_id: uuid.UUID
) -> list[ChecklistTemplateVersion]:
    result = await db.execute(
        select(ChecklistTemplateVersion).where(
            ChecklistTemplateVersion.template_id == template_id,
            ChecklistTemplateVersion.is_deleted == False,
        ).order_by(ChecklistTemplateVersion.version_no.desc())
    )
    return list(result.scalars().all())


async def publish_template_version(
    db: AsyncSession,
    version: ChecklistTemplateVersion,
    published_by: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ChecklistTemplateVersion:
    from fastapi import HTTPException
    if not await _has_permission(db, tenant_id, published_by, PERMISSION_CHECKLIST_PUBLISH):
        raise HTTPException(403, "Permission denied: checklist_template:publish required")
    _assert_template_version_mutable(version)
    if version.status not in ("draft", "in_review"):
        raise HTTPException(400, f"Cannot publish version with status '{version.status}'")

    result = await db.execute(
        select(ChecklistTemplateVersion).where(
            ChecklistTemplateVersion.template_id == version.template_id,
            ChecklistTemplateVersion.status == "published",
            ChecklistTemplateVersion.id != version.id,
        )
    )
    for old in result.scalars().all():
        old.status = "superseded"

    version.status = "published"
    version.published_at = datetime.now(timezone.utc)
    version.published_by = published_by

    result = await db.execute(
        select(ChecklistTemplate).where(ChecklistTemplate.id == version.template_id)
    )
    template = result.scalar_one_or_none()
    if template:
        template.status = "published"

    await db.flush()

    from app.core.audit.service import audit
    await audit(
        db, tenant_id=tenant_id, user_id=published_by,
        action="checklist_template.published",
        resource_type="checklist_template_version",
        resource_id=str(version.id),
        detail={"version_no": version.version_no},
    )
    await db.refresh(version)
    return version


# ── Project import ────────────────────────────────────────────────────────────

async def generate_project_checklist_no(
    db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID
) -> str:
    result = await db.execute(
        select(func.count(ProjectChecklistTemplate.id)).where(
            ProjectChecklistTemplate.tenant_id == tenant_id,
            ProjectChecklistTemplate.project_id == project_id,
        )
    )
    count = result.scalar_one() or 0
    return f"PCL-{count + 1:03d}"


async def import_checklist_to_project(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    data: ChecklistImportRequest,
    imported_by: uuid.UUID,
) -> tuple[ProjectChecklistTemplate, ProjectChecklistTemplateVersion]:
    from fastapi import HTTPException

    result = await db.execute(
        select(ChecklistTemplateVersion).where(
            ChecklistTemplateVersion.id == data.checklist_template_version_id,
            ChecklistTemplateVersion.is_deleted == False,
        )
    )
    source_version = result.scalar_one_or_none()
    if not source_version:
        raise HTTPException(404, "Checklist template version not found")
    if source_version.status != "published":
        raise HTTPException(400, "Can only import published checklist template versions")

    result = await db.execute(
        select(ChecklistTemplate).where(ChecklistTemplate.id == source_version.template_id)
    )
    source_template = result.scalar_one_or_none()
    if not source_template:
        raise HTTPException(404, "Checklist template not found")

    checklist_no = await generate_project_checklist_no(db, tenant_id, project_id)

    # Fix #2 – source_checklist_template_version_id NOT NULL
    checklist = ProjectChecklistTemplate(
        tenant_id=tenant_id,
        project_id=project_id,
        source_checklist_template_version_id=source_version.id,  # always set
        checklist_no=checklist_no,
        title=source_template.title,
        category=source_template.category,
        status="active",
    )
    db.add(checklist)
    await db.flush()

    version = ProjectChecklistTemplateVersion(
        tenant_id=tenant_id,
        checklist_id=checklist.id,
        version_no=1,
        schema_json=source_version.schema_json,  # deep freeze copy
        change_summary=f"Imported from library {source_template.checklist_no} v{source_version.version_no}",
        status="active",
    )
    db.add(version)
    await db.flush()

    # Fix #7 – audit import
    from app.core.audit.service import audit
    await audit(
        db, tenant_id=tenant_id, user_id=imported_by,
        action="checklist.imported_to_project",
        resource_type="project_checklist_template",
        resource_id=str(checklist.id),
        detail={
            "source_version_id": str(source_version.id),
            "project_id": str(project_id),
            "checklist_no": checklist_no,
        },
    )

    await db.refresh(checklist)
    await db.refresh(version)
    return checklist, version


async def get_project_checklist(
    db: AsyncSession, checklist_id: uuid.UUID
) -> ProjectChecklistTemplate | None:
    result = await db.execute(
        select(ProjectChecklistTemplate).where(
            ProjectChecklistTemplate.id == checklist_id,
            ProjectChecklistTemplate.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_project_checklists(
    db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID
) -> list[ProjectChecklistTemplate]:
    result = await db.execute(
        select(ProjectChecklistTemplate).where(
            ProjectChecklistTemplate.tenant_id == tenant_id,
            ProjectChecklistTemplate.project_id == project_id,
            ProjectChecklistTemplate.is_deleted == False,
        ).order_by(ProjectChecklistTemplate.checklist_no)
    )
    return list(result.scalars().all())


async def get_project_checklist_version(
    db: AsyncSession, version_id: uuid.UUID
) -> ProjectChecklistTemplateVersion | None:
    result = await db.execute(
        select(ProjectChecklistTemplateVersion).where(
            ProjectChecklistTemplateVersion.id == version_id,
            ProjectChecklistTemplateVersion.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


# ── Execution ─────────────────────────────────────────────────────────────────

async def create_run(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    data: ChecklistRunCreate,
    run_by: uuid.UUID,
) -> ChecklistRun:
    from fastapi import HTTPException
    version = await get_project_checklist_version(db, data.template_version_id)
    if not version:
        raise HTTPException(404, "Checklist template version not found")
    if version.status not in ("active",):
        raise HTTPException(400, f"Cannot run against version with status '{version.status}'")

    # Fix #3 – created_by = run_by on creation
    run = ChecklistRun(
        tenant_id=tenant_id,
        project_id=project_id,
        checklist_id=version.checklist_id,
        template_version_id=version.id,
        status="open",
        run_by=run_by,
        submitted_by=None,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


async def get_run(db: AsyncSession, run_id: uuid.UUID) -> ChecklistRun | None:
    result = await db.execute(
        select(ChecklistRun).where(
            ChecklistRun.id == run_id,
            ChecklistRun.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_runs(
    db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID
) -> list[ChecklistRun]:
    result = await db.execute(
        select(ChecklistRun).where(
            ChecklistRun.tenant_id == tenant_id,
            ChecklistRun.project_id == project_id,
            ChecklistRun.is_deleted == False,
        ).order_by(ChecklistRun.created_at.desc())
    )
    return list(result.scalars().all())


async def update_run_answers(
    db: AsyncSession, run: ChecklistRun, data: ChecklistRunUpdate
) -> ChecklistRun:
    from fastapi import HTTPException
    if run.status != "open":
        raise HTTPException(400, f"Cannot edit run with status '{run.status}'")
    json.loads(data.answers_json)
    run.answers_json = data.answers_json
    await db.flush()
    await db.refresh(run)
    return run


# Fix #5 – link image file to run via file_links
async def attach_image_to_run(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    run: ChecklistRun,
    file_id: uuid.UUID,
) -> None:
    from app.core.files.service import link_file
    await link_file(db, tenant_id, file_id, "checklist_run", run.id)


async def submit_run(
    db: AsyncSession,
    run: ChecklistRun,
    data: ChecklistRunSubmit,
    tenant_id: uuid.UUID,
    submitted_by: uuid.UUID,
) -> ChecklistRun:
    from fastapi import HTTPException

    if run.status != "open":
        raise HTTPException(400, f"Cannot submit run with status '{run.status}'")

    version = await get_project_checklist_version(db, run.template_version_id)
    if not version or not version.schema_json:
        raise HTTPException(400, "Checklist schema not found")

    schema = _parse_schema(version.schema_json)

    try:
        answers = json.loads(data.answers_json)
    except Exception:
        raise HTTPException(400, "answers_json must be valid JSON")

    # Fix #5 – validate file_links for requires_image fields
    from app.core.files.models import FileLink
    for field in schema:
        if field.get("requires_image"):
            answer = answers.get(field["id"], {})
            file_ids_in_answer = answer.get("file_ids", [])
            if not file_ids_in_answer:
                raise HTTPException(
                    422,
                    f"Field '{field['label']}' requires at least 1 image (file_id missing in answers_json)"
                )
            # Verify at least one is actually linked
            result = await db.execute(
                select(func.count(FileLink.id)).where(
                    FileLink.resource_type == "checklist_run",
                    FileLink.resource_id == run.id,
                    FileLink.tenant_id == tenant_id,
                )
            )
            linked_count = result.scalar_one() or 0
            if linked_count == 0:
                raise HTTPException(
                    422,
                    f"Field '{field['label']}' requires at least 1 image linked via file_links"
                )

    errors = _validate_answers(schema, answers, {})
    if errors:
        raise HTTPException(422, {"message": "Validation failed", "errors": errors})

    run.answers_json = data.answers_json
    run.status = "submitted"
    run.submitted_at = datetime.now(timezone.utc)
    # Fix #3 – submitted_by
    run.submitted_by = submitted_by
    await db.flush()

    # Fix #6 + #7 – idempotent auto-NC with audit
    await _auto_create_ncs(db, tenant_id, run, schema, answers, submitted_by)

    from app.core.audit.service import audit
    await audit(
        db, tenant_id=tenant_id, user_id=submitted_by,
        action="checklist_run.submitted",
        resource_type="checklist_run",
        resource_id=str(run.id),
        detail={},
    )
    await db.refresh(run)
    return run


async def _auto_create_ncs(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    run: ChecklistRun,
    schema: list[dict],
    answers: dict,
    submitted_by: uuid.UUID,
) -> None:
    from app.core.nonconformance.models import Nonconformance
    from app.core.nonconformance.service import generate_nc_no
    from app.core.audit.service import audit

    owner_user_id = await _resolve_nc_assignee(db, tenant_id, run.project_id)
    nc_created = []

    for field in schema:
        if not field.get("creates_nc_on_no"):
            continue
        fid = field["id"]
        answer = answers.get(fid, {})
        value = answer.get("value")
        if str(value).strip().lower() != "no":
            continue

        # Fix #6 – idempotency: check source_key uniqueness
        source_key = fid
        existing = await db.execute(
            select(Nonconformance).where(
                Nonconformance.tenant_id == tenant_id,
                Nonconformance.source_type == "checklist",
                Nonconformance.source_id == run.id,
                Nonconformance.source_key == source_key,
                Nonconformance.is_deleted == False,
            )
        )
        if existing.scalar_one_or_none():
            continue  # already created – skip

        nc_no = await generate_nc_no(db, tenant_id, run.project_id)
        nc = Nonconformance(
            tenant_id=tenant_id,
            project_id=run.project_id,
            nc_no=nc_no,
            title=f"Avvik: {field['label']}",
            description=f"Automatisk opprettet fra sjekkliste. Felt: {field['label']}",
            nc_type="nonconformance",
            severity="low",
            status="open",
            source_type="checklist",
            source_id=run.id,
            source_key=source_key,
            owner_user_id=owner_user_id,
        )
        db.add(nc)
        await db.flush()
        nc_created.append({"nc_no": nc_no, "field_id": fid, "field_label": field["label"]})

    # Fix #7 – audit auto-NC creation
    if nc_created:
        await audit(
            db, tenant_id=tenant_id, user_id=submitted_by,
            action="checklist_run.auto_nc_created",
            resource_type="checklist_run",
            resource_id=str(run.id),
            detail={"nc_count": len(nc_created), "ncs": nc_created},
        )


async def approve_run(
    db: AsyncSession,
    run: ChecklistRun,
    approved_by: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ChecklistRun:
    from fastapi import HTTPException
    if run.status != "submitted":
        raise HTTPException(400, f"Cannot approve run with status '{run.status}'")
    run.status = "approved"
    run.approved_at = datetime.now(timezone.utc)
    run.approved_by = approved_by
    await db.flush()
    from app.core.audit.service import audit
    await audit(
        db, tenant_id=tenant_id, user_id=approved_by,
        action="checklist_run.approved",
        resource_type="checklist_run",
        resource_id=str(run.id),
        detail={},
    )
    await db.refresh(run)
    return run


async def reject_run(
    db: AsyncSession,
    run: ChecklistRun,
    rejected_by: uuid.UUID,
    tenant_id: uuid.UUID,
    data: ChecklistRunReject,
) -> ChecklistRun:
    from fastapi import HTTPException
    if run.status != "submitted":
        raise HTTPException(400, f"Cannot reject run with status '{run.status}'")
    run.status = "open"
    run.rejected_at = datetime.now(timezone.utc)
    run.rejected_by = rejected_by
    run.rejection_reason = data.reason
    run.approved_at = None
    run.approved_by = None
    await db.flush()
    from app.core.audit.service import audit
    await audit(
        db, tenant_id=tenant_id, user_id=rejected_by,
        action="checklist_run.rejected",
        resource_type="checklist_run",
        resource_id=str(run.id),
        detail={"reason": data.reason},
    )
    await db.refresh(run)
    return run
