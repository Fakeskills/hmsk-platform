import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.nonconformance.models import Nonconformance, CapaAction
from app.core.nonconformance.schemas import NonconformanceCreate, NonconformanceUpdate, CapaActionCreate, CapaActionUpdate


async def generate_nc_no(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID) -> str:
    year = datetime.now(timezone.utc).year
    yy = str(year)[-2:]
    result = await db.execute(
        select(func.count(Nonconformance.id)).where(
            Nonconformance.tenant_id == tenant_id,
            Nonconformance.project_id == project_id,
        )
    )
    count = result.scalar_one() or 0
    return f"NC-{yy}-{count + 1:04d}"


async def create_nc(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    data: NonconformanceCreate,
) -> Nonconformance:
    nc_no = await generate_nc_no(db, tenant_id, project_id)
    nc = Nonconformance(
        tenant_id=tenant_id,
        project_id=project_id,
        nc_no=nc_no,
        title=data.title,
        description=data.description,
        nc_type=data.nc_type,
        severity=data.severity,
        status="open",
        assigned_to=data.assigned_to,
        source_type=data.source_type,
        source_id=data.source_id,
    )
    db.add(nc)
    await db.flush()
    await db.refresh(nc)
    return nc


async def create_nc_from_incident(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    incident_id: uuid.UUID,
    project_id: uuid.UUID,
    title: str,
    description: str | None,
) -> Nonconformance:
    data = NonconformanceCreate(
        title=title,
        description=description,
        source_type="incident",
        source_id=incident_id,
    )
    return await create_nc(db, tenant_id, project_id, data)


async def get_nc(db: AsyncSession, nc_id: uuid.UUID) -> Nonconformance | None:
    result = await db.execute(
        select(Nonconformance).where(Nonconformance.id == nc_id, Nonconformance.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def list_ncs(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID) -> list[Nonconformance]:
    result = await db.execute(
        select(Nonconformance).where(
            Nonconformance.tenant_id == tenant_id,
            Nonconformance.project_id == project_id,
            Nonconformance.is_deleted == False,
        ).order_by(Nonconformance.created_at.desc())
    )
    return list(result.scalars().all())


async def update_nc(db: AsyncSession, nc: Nonconformance, data: NonconformanceUpdate) -> Nonconformance:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(nc, field, value)
    await db.flush()
    await db.refresh(nc)
    return nc


async def create_capa(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    nc: Nonconformance,
    data: CapaActionCreate,
) -> CapaAction:
    action = CapaAction(
        tenant_id=tenant_id,
        nonconformance_id=nc.id,
        project_id=nc.project_id,
        title=data.title,
        description=data.description,
        action_type=data.action_type,
        status="open",
        assigned_to=data.assigned_to,
        due_date=data.due_date,
    )
    db.add(action)
    await db.flush()
    await db.refresh(action)
    return action


async def list_capas(db: AsyncSession, tenant_id: uuid.UUID, nc_id: uuid.UUID) -> list[CapaAction]:
    result = await db.execute(
        select(CapaAction).where(
            CapaAction.nonconformance_id == nc_id,
            CapaAction.tenant_id == tenant_id,
            CapaAction.is_deleted == False,
        ).order_by(CapaAction.created_at.asc())
    )
    return list(result.scalars().all())


async def update_capa(db: AsyncSession, action: CapaAction, data: CapaActionUpdate) -> CapaAction:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(action, field, value)
    await db.flush()
    await db.refresh(action)
    return action
