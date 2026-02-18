import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timesheets import service
from app.core.timesheets.schemas import (
    TimesheetCreate, TimesheetRead, ReopenRequest,
    TimeEntryCreate, TimeEntryUpdate, TimeEntryRead,
    AdjustmentCreate,
    ComplianceRuleCreate, ComplianceRuleRead, ComplianceResultRead,
    ViolationResolveRequest,
    PayrollExportCreate, PayrollExportRead, PayrollExportLineRead,
    VoidExportRequest,
)
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["timesheets"])


# ── Timesheets ────────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/timesheets", response_model=TimesheetRead, status_code=201)
async def create_timesheet(
    project_id: uuid.UUID,
    data: TimesheetCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    data.project_id = project_id
    return await service.create_timesheet(db, current.tenant_id, current.user_id, data)


@router.get("/projects/{project_id}/timesheets", response_model=list[TimesheetRead])
async def list_timesheets(
    project_id: uuid.UUID,
    status: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_timesheets(
        db, current.tenant_id, project_id=project_id,
        user_id=user_id, status=status,
    )


@router.get("/timesheets/{timesheet_id}", response_model=TimesheetRead)
async def get_timesheet(
    timesheet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    sheet = await service.get_timesheet(db, timesheet_id)
    if not sheet:
        raise HTTPException(404, "Timesheet not found")
    return sheet


@router.post("/timesheets/{timesheet_id}/submit", response_model=TimesheetRead)
async def submit_timesheet(
    timesheet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.submit_timesheet(db, timesheet_id, current.user_id, current.tenant_id)


@router.post("/timesheets/{timesheet_id}/approve", response_model=TimesheetRead)
async def approve_timesheet(
    timesheet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.approve_timesheet(db, timesheet_id, current.user_id, current.tenant_id)


@router.post("/timesheets/{timesheet_id}/reject", response_model=TimesheetRead)
async def reject_timesheet(
    timesheet_id: uuid.UUID,
    reason: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.reject_timesheet(db, timesheet_id, current.user_id, current.tenant_id, reason)


@router.post("/timesheets/{timesheet_id}/lock", response_model=TimesheetRead)
async def lock_timesheet(
    timesheet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.lock_timesheet(db, timesheet_id, current.user_id, current.tenant_id)


@router.post("/timesheets/{timesheet_id}/reopen", response_model=TimesheetRead)
async def reopen_timesheet(
    timesheet_id: uuid.UUID,
    data: ReopenRequest,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.reopen_timesheet(db, timesheet_id, current.user_id, current.tenant_id, data)


# ── Time entries ──────────────────────────────────────────────────────────────

@router.post("/timesheets/{timesheet_id}/entries", response_model=TimeEntryRead, status_code=201)
async def create_entry(
    timesheet_id: uuid.UUID,
    data: TimeEntryCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    sheet = await service.get_timesheet(db, timesheet_id)
    if not sheet:
        raise HTTPException(404, "Timesheet not found")
    return await service.create_entry(db, current.tenant_id, sheet, data, current.user_id)


@router.get("/timesheets/{timesheet_id}/entries", response_model=list[TimeEntryRead])
async def list_entries(
    timesheet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    return await service.list_entries(db, timesheet_id)


@router.patch("/time-entries/{entry_id}", response_model=TimeEntryRead)
async def update_entry(
    entry_id: uuid.UUID,
    data: TimeEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    entry = await service.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    sheet = await service.get_timesheet(db, entry.timesheet_id)
    if not sheet:
        raise HTTPException(404, "Timesheet not found")
    return await service.update_entry(db, current.tenant_id, entry, sheet, data, current.user_id)


@router.delete("/time-entries/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    entry = await service.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    sheet = await service.get_timesheet(db, entry.timesheet_id)
    if not sheet:
        raise HTTPException(404, "Timesheet not found")
    await service.delete_entry(db, current.tenant_id, entry, sheet, current.user_id)


@router.post("/timesheets/{timesheet_id}/adjustments", response_model=TimeEntryRead, status_code=201)
async def create_adjustment(
    timesheet_id: uuid.UUID,
    data: AdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    sheet = await service.get_timesheet(db, timesheet_id)
    if not sheet:
        raise HTTPException(404, "Timesheet not found")
    return await service.create_adjustment(db, current.tenant_id, sheet, data, current.user_id)


# ── Compliance ────────────────────────────────────────────────────────────────

@router.post("/compliance/rules", response_model=ComplianceRuleRead, status_code=201)
async def create_rule(
    data: ComplianceRuleCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.create_rule(db, current.tenant_id, data)


@router.get("/compliance/rules", response_model=list[ComplianceRuleRead])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_rules(db, current.tenant_id)


@router.post("/timesheets/{timesheet_id}/compliance/evaluate", response_model=list[ComplianceResultRead])
async def evaluate_compliance(
    timesheet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Manual re-evaluation trigger."""
    sheet = await service.get_timesheet(db, timesheet_id)
    if not sheet:
        raise HTTPException(404, "Timesheet not found")
    return await service.run_compliance(db, sheet, current.tenant_id)


@router.get("/timesheets/{timesheet_id}/compliance", response_model=list[ComplianceResultRead])
async def get_compliance_results(
    timesheet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.core.timesheets.models import ComplianceResult
    result = await db.execute(
        select(ComplianceResult).where(
            ComplianceResult.timesheet_id == timesheet_id
        ).order_by(ComplianceResult.evaluated_at.desc())
    )
    return list(result.scalars().all())


@router.post("/compliance/results/{result_id}/resolve", response_model=ComplianceResultRead)
async def resolve_violation(
    result_id: uuid.UUID,
    data: ViolationResolveRequest,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.resolve_violation(db, result_id, current.user_id, current.tenant_id, data)


# ── Payroll export ────────────────────────────────────────────────────────────

@router.post("/payroll/exports", response_model=PayrollExportRead, status_code=201)
async def generate_export(
    data: PayrollExportCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.generate_export(db, current.tenant_id, data, current.user_id)


@router.get("/payroll/exports", response_model=list[PayrollExportRead])
async def list_exports(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.list_exports(db, current.tenant_id)


@router.get("/payroll/exports/{export_id}", response_model=PayrollExportRead)
async def get_export(
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    export = await service.get_export(db, export_id)
    if not export:
        raise HTTPException(404, "Export not found")
    return export


@router.get("/payroll/exports/{export_id}/lines", response_model=list[PayrollExportLineRead])
async def get_export_lines(
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    from sqlalchemy import select
    from app.core.timesheets.models import PayrollExportLine
    result = await db.execute(
        select(PayrollExportLine).where(PayrollExportLine.export_id == export_id)
    )
    return list(result.scalars().all())


@router.post("/payroll/exports/{export_id}/send", response_model=PayrollExportRead)
async def mark_export_sent(
    export_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.mark_export_sent(db, export_id, current.user_id, current.tenant_id)


@router.post("/payroll/exports/{export_id}/void", response_model=PayrollExportRead)
async def void_export(
    export_id: uuid.UUID,
    data: VoidExportRequest,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    return await service.void_export(db, export_id, current.user_id, current.tenant_id, data)
