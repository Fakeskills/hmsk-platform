import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.nonconformance.models import Nonconformance, CapaAction
from app.core.nonconformance.schemas import (
    NonconformanceCreate, NonconformanceUpdate,
    CapaActionCreate, CapaActionUpdate,
)

CAPA_VALID_TRANSITIONS = {
    "open": ["done"],
    "done": ["verified"],
    "verified": [],
}


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
        owner_user_id=data.owner_user_id,
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
    owner_user_id: uuid.UUID | None,
) -> Nonconformance:
    data = NonconformanceCreate(
        title=title,
        description=description,
        source_type="incident",
        source_id=incident_id,
        owner_user_id=owner_user_id,
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


async def update_nc(
    db: AsyncSession,
    nc: Nonconformance,
    data: NonconformanceUpdate,
    updated_by: uuid.UUID,
    tenant_id: uuid.UUID,
) -> Nonconformance:
    old_owner = nc.owner_user_id
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(nc, field, value)
    await db.flush()

    # Audit ownership change
    if data.owner_user_id is not None and data.owner_user_id != old_owner:
        from app.core.audit.service import audit
        await audit(
            db,
            tenant_id=tenant_id,
            user_id=updated_by,
            action="nc.owner_changed",
            resource_type="nonconformance",
            resource_id=str(nc.id),
            detail={"old_owner": str(old_owner), "new_owner": str(data.owner_user_id)},
        )

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


async def transition_capa(
    db: AsyncSession,
    action: CapaAction,
    to_status: str,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> CapaAction:
    from fastapi import HTTPException
    allowed = CAPA_VALID_TRANSITIONS.get(action.status, [])
    if to_status not in allowed:
        raise HTTPException(400, f"Cannot transition CAPA from '{action.status}' to '{to_status}'")

    now_iso = datetime.now(timezone.utc).isoformat()
    action.status = to_status

    if to_status == "done":
        action.done_at = now_iso
    elif to_status == "verified":
        action.verified_at = now_iso
        action.verified_by = user_id

    await db.flush()

    from app.core.audit.service import audit
    await audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        action=f"capa.{to_status}",
        resource_type="capa_action",
        resource_id=str(action.id),
        detail={"new_status": to_status},
    )

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
