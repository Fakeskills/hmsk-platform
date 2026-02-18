import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.projects.models import Project, ProjectSequence
from app.core.projects.schemas import ProjectCreate

INBOX_DOMAIN = "hmsk.app"


async def generate_project_no(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    year = datetime.now(timezone.utc).year
    yy = str(year)[-2:]
    result = await db.execute(
        select(ProjectSequence)
        .where(ProjectSequence.tenant_id == tenant_id, ProjectSequence.year == year)
        .with_for_update()
    )
    seq = result.scalar_one_or_none()
    if seq is None:
        seq = ProjectSequence(tenant_id=tenant_id, year=year, last_seq=0)
        db.add(seq)
        await db.flush()
        result = await db.execute(
            select(ProjectSequence)
            .where(ProjectSequence.tenant_id == tenant_id, ProjectSequence.year == year)
            .with_for_update()
        )
        seq = result.scalar_one()
    seq.last_seq += 1
    await db.flush()
    return f"{yy}-{seq.last_seq:04d}"


async def create_project(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: ProjectCreate,
    created_by: uuid.UUID | None = None,
) -> Project:
    from app.core.tenants.models import Tenant
    t_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = t_result.scalar_one()
    project_no = await generate_project_no(db, tenant_id)
    inbox_email = f"{tenant.slug}+{project_no}@{INBOX_DOMAIN}"
    project = Project(
        tenant_id=tenant_id,
        project_no=project_no,
        name=data.name,
        description=data.description,
        inbox_email=inbox_email,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)

    # Fix #3 – audit project create
    if created_by:
        from app.core.audit.service import audit
        await audit(
            db, tenant_id=tenant_id, user_id=created_by,
            action="project.create",
            resource_type="project",
            resource_id=str(project.id),
            detail={"project_no": project_no, "name": data.name},
        )

    return project


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project | None:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def list_projects(db: AsyncSession, tenant_id: uuid.UUID) -> list[Project]:
    result = await db.execute(
        select(Project)
        .where(Project.tenant_id == tenant_id, Project.is_deleted == False)
        .order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())
