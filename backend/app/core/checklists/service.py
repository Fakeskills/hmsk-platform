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


# ── Immutability guard ────────────────────────────────────────────────────────

def _assert_template_version_mutable(version: ChecklistTemplateVersion) -> None:
    from fastapi import HTTPException
    if version.status in ("published", "superseded"):
        raise HTTPException(400, f"Checklist template version is '{version.status}' and immutable")


# ── Schema validation ─────────────────────────────────────────────────────────

def _parse_schema(schema_json: str) -> list[dict]:
    from fastapi import HTTPException
    try:
        fields = json.loads(schema_json)
    except Exception:
        raise HTTPException(400, "schema_json must be valid JSON")
    if not isinstance(fields, list):
        raise HTTPException(400, "schema_json must be a JSON array of field definitions")
    for f in fields:
        if "id" not in f or "label" not in f or "field_type" not in f:
            raise HTTPException(400, f"Field missing required keys (id, label, field_type): {f}")
        if f["field_type"] not in ("yes_no", "text", "number", "date", "photo"):
            raise HTTPException(400, f"Invalid field_type '{f['field_type']}'")
    return fields


def _validate_answers(
    schema: list[dict], answers: dict, file_ids_by_field: dict[str, list]
) -> list[str]:
    """
    Returns list of validation error messages.
    Checks:
    - required fields are answered
    - requires_image fields have at least 1 file_id
    """
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
    _parse_schema(data.schema_json)  # validate
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
    if version.status != "draft":
        raise HTTPException(400, f"Cannot publish version with status '{version.status}'")

    # Supersede previous published
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
) -> tuple[ProjectChecklistTemplate, ProjectChecklistTemplateVersion]:
    from fastapi import HTTPException

    # Load source version
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

    # Load parent template for metadata
    result = await db.execute(
        select(ChecklistTemplate).where(ChecklistTemplate.id == source_version.template_id)
    )
    source_template = result.scalar_one_or_none()
    if not source_template:
        raise HTTPException(404, "Checklist template not found")

    checklist_no = await generate_project_checklist_no(db, tenant_id, project_id)

    checklist = ProjectChecklistTemplate(
        tenant_id=tenant_id,
        project_id=project_id,
        source_checklist_template_version_id=source_version.id,
        checklist_no=checklist_no,
        title=source_template.title,
        category=source_template.category,
        status="active",
    )
    db.add(checklist)
    await db.flush()

    # Freeze copy of schema
    version = ProjectChecklistTemplateVersion(
        tenant_id=tenant_id,
        checklist_id=checklist.id,
        version_no=1,
        schema_json=source_version.schema_json,
        change_summary=f"Imported from library {source_template.checklist_no} v{source_version.version_no}",
        status="active",
    )
    db.add(version)
    await db.flush()
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

    run = ChecklistRun(
        tenant_id=tenant_id,
        project_id=project_id,
        checklist_id=version.checklist_id,
        template_version_id=version.id,
        status="open",
        run_by=run_by,
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
    json.loads(data.answers_json)  # validate JSON
    run.answers_json = data.answers_json
    await db.flush()
    await db.refresh(run)
    return run


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

    # Load schema
    version = await get_project_checklist_version(db, run.template_version_id)
    if not version or not version.schema_json:
        raise HTTPException(400, "Checklist schema not found")

    schema = _parse_schema(version.schema_json)

    # Parse and validate answers
    try:
        answers = json.loads(data.answers_json)
    except Exception:
        raise HTTPException(400, "answers_json must be valid JSON")

    errors = _validate_answers(schema, answers, {})
    if errors:
        raise HTTPException(422, {"message": "Validation failed", "errors": errors})

    run.answers_json = data.answers_json
    run.status = "submitted"
    run.submitted_at = datetime.now(timezone.utc)
    await db.flush()

    # Auto-create NCs for critical "No" answers
    await _auto_create_ncs(db, tenant_id, run, schema, answers)

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
) -> None:
    from app.core.nonconformance.models import Nonconformance
    from app.core.nonconformance.service import generate_nc_no

    owner_user_id = await _resolve_nc_assignee(db, tenant_id, run.project_id)

    for field in schema:
        if not field.get("creates_nc_on_no"):
            continue
        fid = field["id"]
        answer = answers.get(fid, {})
        value = answer.get("value")
        if str(value).strip().lower() == "no":
            nc_no = await generate_nc_no(db, tenant_id, run.project_id)
            nc = Nonconformance(
                tenant_id=tenant_id,
                project_id=run.project_id,
                nc_no=nc_no,
                title=f"Avvik: {field['label']}",
                description=f"Automatisk opprettet fra sjekkliste-svar. Felt: {field['label']}",
                nc_type="nonconformance",
                severity="low",
                status="open",
                source_type="checklist",
                source_id=run.id,
                owner_user_id=owner_user_id,
            )
            db.add(nc)

    await db.flush()


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

    # Transition back to open – same run, editable again
    run.status = "open"
    run.rejected_at = datetime.now(timezone.utc)
    run.rejected_by = rejected_by
    run.rejection_reason = data.reason
    # Clear approval fields in case of re-review
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
