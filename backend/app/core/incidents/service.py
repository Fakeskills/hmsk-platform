import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.incidents.models import Incident, IncidentMessage
from app.core.incidents.schemas import IncidentCreate, IncidentMessageCreate, IncidentTriageUpdate


VALID_TRANSITIONS = {
    "draft": ["submitted"],
    "submitted": ["triage"],
    "triage": ["open"],
    "open": ["closed"],
    "closed": [],
}


async def generate_incident_no(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID) -> str:
    year = datetime.now(timezone.utc).year
    yy = str(year)[-2:]
    result = await db.execute(
        select(func.count(Incident.id)).where(
            Incident.tenant_id == tenant_id,
            Incident.project_id == project_id,
        )
    )
    count = result.scalar_one() or 0
    return f"RUH-{yy}-{count + 1:04d}"


async def create_incident(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    data: IncidentCreate,
    reported_by: uuid.UUID | None,
) -> Incident:
    incident_no = await generate_incident_no(db, tenant_id, project_id)

    if data.anonymous:
        reporter_visibility = "anonymous"
        reporter_user_id_internal = reported_by
        reporter_user_id_visible = None
    else:
        reporter_visibility = "named"
        reporter_user_id_internal = reported_by
        reporter_user_id_visible = reported_by

    incident = Incident(
        tenant_id=tenant_id,
        project_id=project_id,
        incident_no=incident_no,
        title=data.title,
        description=data.description,
        incident_type=data.incident_type,
        severity=data.severity,
        status="draft",
        reporter_visibility=reporter_visibility,
        reporter_user_id_internal=reporter_user_id_internal,
        reporter_user_id_visible=reporter_user_id_visible,
        occurred_at=data.occurred_at,
        location=data.location,
    )
    db.add(incident)
    await db.flush()
    await db.refresh(incident)
    return incident


async def get_incident(db: AsyncSession, incident_id: uuid.UUID) -> Incident | None:
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id, Incident.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def list_incidents(db: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID) -> list[Incident]:
    result = await db.execute(
        select(Incident).where(
            Incident.tenant_id == tenant_id,
            Incident.project_id == project_id,
            Incident.is_deleted == False,
        ).order_by(Incident.created_at.desc())
    )
    return list(result.scalars().all())


async def transition_incident(db: AsyncSession, incident: Incident, to_status: str) -> Incident:
    from fastapi import HTTPException
    allowed = VALID_TRANSITIONS.get(incident.status, [])
    if to_status not in allowed:
        raise HTTPException(400, f"Cannot transition from '{incident.status}' to '{to_status}'")
    incident.status = to_status
    await db.flush()
    await db.refresh(incident)
    return incident


async def triage_incident(db: AsyncSession, incident: Incident, data: IncidentTriageUpdate) -> Incident:
    if data.assigned_to is not None:
        incident.assigned_to = data.assigned_to
    if data.severity is not None:
        incident.severity = data.severity
    await db.flush()
    await db.refresh(incident)
    return incident


async def reveal_reporter(
    db: AsyncSession,
    incident: Incident,
    revealed_by: uuid.UUID,
    tenant_id: uuid.UUID,
) -> Incident:
    from fastapi import HTTPException
    if incident.reporter_visibility == "named":
        raise HTTPException(400, "Reporter is already visible")
    incident.reporter_user_id_visible = incident.reporter_user_id_internal
    incident.reporter_visibility = "named"
    await db.flush()
    # Audit log
    from app.core.audit.service import audit
    await audit(
        db,
        tenant_id=tenant_id,
        user_id=revealed_by,
        action="incident.reveal_reporter",
        resource_type="incident",
        resource_id=str(incident.id),
        detail={"incident_no": incident.incident_no},
    )
    await db.refresh(incident)
    return incident


async def add_message(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    incident: Incident,
    data: IncidentMessageCreate,
    sender_id: uuid.UUID | None,
) -> IncidentMessage:
    msg = IncidentMessage(
        tenant_id=tenant_id,
        incident_id=incident.id,
        body=data.body,
        sender_id=sender_id,
        is_internal=data.is_internal,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


async def list_messages(
    db: AsyncSession, tenant_id: uuid.UUID, incident_id: uuid.UUID
) -> list[IncidentMessage]:
    result = await db.execute(
        select(IncidentMessage).where(
            IncidentMessage.incident_id == incident_id,
            IncidentMessage.tenant_id == tenant_id,
            IncidentMessage.is_deleted == False,
        ).order_by(IncidentMessage.created_at.asc())
    )
    return list(result.scalars().all())
