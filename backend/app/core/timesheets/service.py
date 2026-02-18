import json
import uuid
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timesheets.models import (
    Timesheet, TimeEntry, ComplianceRule, ComplianceResult,
    PayrollExport, PayrollExportLine,
)
from app.core.timesheets.schemas import (
    TimesheetCreate, TimeEntryCreate, TimeEntryUpdate,
    AdjustmentCreate, ComplianceRuleCreate,
    PayrollExportCreate, ViolationResolveRequest,
    ReopenRequest, VoidExportRequest,
)

IMMUTABLE_TIMESHEET_STATUSES = {"locked"}
EDITABLE_TIMESHEET_STATUSES = {"open"}


# ── Tenant timezone ───────────────────────────────────────────────────────────

async def _get_tenant_tz(db: AsyncSession, tenant_id: uuid.UUID) -> ZoneInfo:
    from app.core.tenants.models import Tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    tz_name = getattr(tenant, "timezone", None) or "UTC"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


# ── Timesheets ────────────────────────────────────────────────────────────────

def _week_end(week_start: date) -> date:
    return week_start + timedelta(days=6)


async def create_timesheet(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: TimesheetCreate,
) -> Timesheet:
    from fastapi import HTTPException
    if data.week_start.weekday() != 0:
        raise HTTPException(400, "week_start must be a Monday")
    week_end = _week_end(data.week_start)

    sheet = Timesheet(
        tenant_id=tenant_id,
        project_id=data.project_id,
        user_id=user_id,
        week_start=data.week_start,
        week_end=week_end,
        status="open",
    )
    db.add(sheet)
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=user_id,
        action="timesheet.create", resource_type="timesheet",
        resource_id=str(sheet.id),
        detail={"week_start": str(data.week_start), "project_id": str(data.project_id)},
    )
    await db.refresh(sheet)
    return sheet


async def get_timesheet(db: AsyncSession, timesheet_id: uuid.UUID) -> Timesheet | None:
    result = await db.execute(
        select(Timesheet).where(Timesheet.id == timesheet_id, Timesheet.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def get_timesheet_locked(db: AsyncSession, timesheet_id: uuid.UUID) -> Timesheet | None:
    """Row-level lock for state transitions."""
    result = await db.execute(
        select(Timesheet)
        .where(Timesheet.id == timesheet_id, Timesheet.is_deleted == False)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def list_timesheets(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[Timesheet]:
    q = select(Timesheet).where(
        Timesheet.tenant_id == tenant_id,
        Timesheet.is_deleted == False,
    )
    if project_id:
        q = q.where(Timesheet.project_id == project_id)
    if user_id:
        q = q.where(Timesheet.user_id == user_id)
    if status:
        q = q.where(Timesheet.status == status)
    q = q.order_by(Timesheet.week_start.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


# ── State machine ─────────────────────────────────────────────────────────────

async def submit_timesheet(
    db: AsyncSession,
    timesheet_id: uuid.UUID,
    submitted_by: uuid.UUID,
    tenant_id: uuid.UUID,
) -> Timesheet:
    from fastapi import HTTPException
    sheet = await get_timesheet_locked(db, timesheet_id)
    if not sheet:
        raise HTTPException(404, "Timesheet not found")

    # Idempotent
    if sheet.status == "submitted":
        return sheet
    if sheet.status != "open":
        raise HTTPException(400, f"Cannot submit timesheet with status '{sheet.status}'")

    # Run compliance before submit
    violations = await run_compliance(db, sheet, tenant_id)
    blocking = [v for v in violations if v.severity in ("block", "critical") and v.status == "violation"]
    if blocking:
        raise HTTPException(422, {
            "message": "Compliance violations block submission",
            "violations": [{"rule_code": v.rule_code, "severity": v.severity} for v in blocking],
        })

    sheet.status = "submitted"
    sheet.submitted_at = datetime.now(timezone.utc)
    sheet.submitted_by = submitted_by
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=submitted_by,
        action="timesheet.submit", resource_type="timesheet",
        resource_id=str(sheet.id), detail={},
    )
    await db.refresh(sheet)
    return sheet


async def approve_timesheet(
    db: AsyncSession,
    timesheet_id: uuid.UUID,
    approved_by: uuid.UUID,
    tenant_id: uuid.UUID,
) -> Timesheet:
    from fastapi import HTTPException
    sheet = await get_timesheet_locked(db, timesheet_id)
    if not sheet:
        raise HTTPException(404, "Timesheet not found")

    # Idempotent
    if sheet.status == "approved":
        return sheet
    if sheet.status != "submitted":
        raise HTTPException(400, f"Cannot approve timesheet with status '{sheet.status}'")

    # Re-run compliance at approve
    violations = await run_compliance(db, sheet, tenant_id)
    blocking = [v for v in violations if v.severity in ("block", "critical") and v.status == "violation"]
    if blocking:
        raise HTTPException(422, {
            "message": "Compliance violations block approval",
            "violations": [{"rule_code": v.rule_code, "severity": v.severity} for v in blocking],
        })

    sheet.status = "approved"
    sheet.approved_at = datetime.now(timezone.utc)
    sheet.approved_by = approved_by
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=approved_by,
        action="timesheet.approve", resource_type="timesheet",
        resource_id=str(sheet.id), detail={},
    )
    await db.refresh(sheet)
    return sheet


async def reject_timesheet(
    db: AsyncSession,
    timesheet_id: uuid.UUID,
    rejected_by: uuid.UUID,
    tenant_id: uuid.UUID,
    reason: str,
) -> Timesheet:
    from fastapi import HTTPException
    sheet = await get_timesheet_locked(db, timesheet_id)
    if not sheet:
        raise HTTPException(404, "Timesheet not found")
    if sheet.status == "locked":
        raise HTTPException(400, "Cannot reject a locked timesheet")
    if sheet.status not in ("submitted", "approved"):
        raise HTTPException(400, f"Cannot reject timesheet with status '{sheet.status}'")

    sheet.status = "open"
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=rejected_by,
        action="timesheet.reject", resource_type="timesheet",
        resource_id=str(sheet.id), detail={"reason": reason},
    )
    await db.refresh(sheet)
    return sheet


async def lock_timesheet(
    db: AsyncSession,
    timesheet_id: uuid.UUID,
    locked_by: uuid.UUID,
    tenant_id: uuid.UUID,
) -> Timesheet:
    from fastapi import HTTPException
    sheet = await get_timesheet_locked(db, timesheet_id)
    if not sheet:
        raise HTTPException(404, "Timesheet not found")
    if sheet.status == "locked":
        return sheet  # idempotent
    if sheet.status != "approved":
        raise HTTPException(400, f"Cannot lock timesheet with status '{sheet.status}'")

    sheet.status = "locked"
    sheet.locked_at = datetime.now(timezone.utc)
    sheet.locked_by = locked_by
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=locked_by,
        action="timesheet.lock", resource_type="timesheet",
        resource_id=str(sheet.id), detail={},
    )
    await db.refresh(sheet)
    return sheet


async def reopen_timesheet(
    db: AsyncSession,
    timesheet_id: uuid.UUID,
    reopened_by: uuid.UUID,
    tenant_id: uuid.UUID,
    data: ReopenRequest,
) -> Timesheet:
    from fastapi import HTTPException
    sheet = await get_timesheet_locked(db, timesheet_id)
    if not sheet:
        raise HTTPException(404, "Timesheet not found")
    if sheet.status != "locked":
        raise HTTPException(400, f"Only locked timesheets can be reopened. Current status: '{sheet.status}'")

    sheet.status = "open"
    sheet.reopened_at = datetime.now(timezone.utc)
    sheet.reopened_by = reopened_by
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=reopened_by,
        action="timesheet.reopen", resource_type="timesheet",
        resource_id=str(sheet.id), detail={"reason": data.reason},
    )

    # Re-run compliance after reopen
    await run_compliance(db, sheet, tenant_id)

    await db.refresh(sheet)
    return sheet


# ── Time entries ──────────────────────────────────────────────────────────────

def _calc_net_minutes(start: datetime, end: datetime, break_minutes: int) -> int:
    total = int((end - start).total_seconds() / 60)
    return max(0, total - break_minutes)


async def _check_overlap(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    work_date: date,
    start_time: datetime,
    end_time: datetime,
    exclude_entry_id: uuid.UUID | None = None,
) -> None:
    from fastapi import HTTPException
    q = select(TimeEntry).where(
        TimeEntry.tenant_id == tenant_id,
        TimeEntry.user_id == user_id,
        TimeEntry.work_date == work_date,
        TimeEntry.status != "rejected",
        TimeEntry.is_deleted == False,
        # Overlap condition: not (end <= other.start OR start >= other.end)
        and_(
            TimeEntry.start_time < end_time,
            TimeEntry.end_time > start_time,
        ),
    )
    if exclude_entry_id:
        q = q.where(TimeEntry.id != exclude_entry_id)
    result = await db.execute(q)
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            400,
            f"Time entry overlaps with existing entry "
            f"{existing.start_time.isoformat()} – {existing.end_time.isoformat()}"
        )


async def create_entry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    sheet: Timesheet,
    data: TimeEntryCreate,
    created_by: uuid.UUID,
) -> TimeEntry:
    from fastapi import HTTPException

    if sheet.status not in EDITABLE_TIMESHEET_STATUSES:
        raise HTTPException(400, f"Cannot add entries to timesheet with status '{sheet.status}'")

    # user_id on entry must match timesheet
    if created_by != sheet.user_id:
        raise HTTPException(403, "Entry user must match timesheet user")

    # entry must lie within timesheet week
    if not (sheet.week_start <= data.work_date <= sheet.week_end):
        raise HTTPException(400, f"work_date {data.work_date} is outside timesheet week "
                                 f"{sheet.week_start} – {sheet.week_end}")

    await _check_overlap(db, tenant_id, sheet.user_id, data.work_date,
                         data.start_time, data.end_time)

    net = _calc_net_minutes(data.start_time, data.end_time, data.break_minutes)
    entry = TimeEntry(
        tenant_id=tenant_id,
        timesheet_id=sheet.id,
        user_id=sheet.user_id,
        project_id=sheet.project_id,
        work_date=data.work_date,
        start_time=data.start_time,
        end_time=data.end_time,
        break_minutes=data.break_minutes,
        net_minutes=net,
        description=data.description,
        status="active",
        is_adjustment=False,
    )
    db.add(entry)
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=created_by,
        action="timeentry.create", resource_type="time_entry",
        resource_id=str(entry.id),
        detail={"work_date": str(data.work_date), "net_minutes": net},
    )
    await db.refresh(entry)
    return entry


async def update_entry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    entry: TimeEntry,
    sheet: Timesheet,
    data: TimeEntryUpdate,
    updated_by: uuid.UUID,
) -> TimeEntry:
    from fastapi import HTTPException

    if sheet.status not in EDITABLE_TIMESHEET_STATUSES:
        raise HTTPException(400, f"Cannot edit entries on timesheet with status '{sheet.status}'")
    if entry.is_adjustment:
        raise HTTPException(400, "Adjustment entries cannot be edited")

    new_start = data.start_time or entry.start_time
    new_end = data.end_time or entry.end_time
    new_break = data.break_minutes if data.break_minutes is not None else entry.break_minutes

    if new_end <= new_start:
        raise HTTPException(400, "end_time must be after start_time")

    await _check_overlap(db, tenant_id, entry.user_id, entry.work_date,
                         new_start, new_end, exclude_entry_id=entry.id)

    entry.start_time = new_start
    entry.end_time = new_end
    entry.break_minutes = new_break
    entry.net_minutes = _calc_net_minutes(new_start, new_end, new_break)
    if data.description is not None:
        entry.description = data.description
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=updated_by,
        action="timeentry.update", resource_type="time_entry",
        resource_id=str(entry.id),
        detail={"net_minutes": entry.net_minutes},
    )
    await db.refresh(entry)
    return entry


async def delete_entry(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    entry: TimeEntry,
    sheet: Timesheet,
    deleted_by: uuid.UUID,
) -> None:
    from fastapi import HTTPException
    if sheet.status not in EDITABLE_TIMESHEET_STATUSES:
        raise HTTPException(400, f"Cannot delete entries on timesheet with status '{sheet.status}'")
    if entry.is_adjustment:
        raise HTTPException(400, "Adjustment entries cannot be deleted")

    entry.is_deleted = True
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=deleted_by,
        action="timeentry.delete", resource_type="time_entry",
        resource_id=str(entry.id), detail={},
    )


async def create_adjustment(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    sheet: Timesheet,
    data: AdjustmentCreate,
    created_by: uuid.UUID,
) -> TimeEntry:
    from fastapi import HTTPException

    # Adjustments allowed only after lock
    if sheet.status != "locked":
        raise HTTPException(400, "Adjustments can only be added to locked timesheets")

    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.id == data.original_entry_id,
            TimeEntry.tenant_id == tenant_id,
            TimeEntry.is_deleted == False,
        )
    )
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(404, "Original entry not found")

    adj = TimeEntry(
        tenant_id=tenant_id,
        timesheet_id=sheet.id,
        user_id=sheet.user_id,
        project_id=sheet.project_id,
        work_date=original.work_date,
        start_time=original.start_time,
        end_time=original.end_time,
        break_minutes=0,
        net_minutes=data.delta_minutes,
        description=data.description or f"Adjustment on entry {data.original_entry_id}",
        status="active",
        is_adjustment=True,
        original_entry_id=data.original_entry_id,
        delta_minutes=data.delta_minutes,
    )
    db.add(adj)
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=created_by,
        action="timeentry.adjustment", resource_type="time_entry",
        resource_id=str(adj.id),
        detail={"original_entry_id": str(data.original_entry_id), "delta_minutes": data.delta_minutes},
    )
    await db.refresh(adj)
    return adj


async def get_entry(db: AsyncSession, entry_id: uuid.UUID) -> TimeEntry | None:
    result = await db.execute(
        select(TimeEntry).where(TimeEntry.id == entry_id, TimeEntry.is_deleted == False)
    )
    return result.scalar_one_or_none()


async def list_entries(db: AsyncSession, timesheet_id: uuid.UUID) -> list[TimeEntry]:
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.timesheet_id == timesheet_id,
            TimeEntry.is_deleted == False,
        ).order_by(TimeEntry.work_date, TimeEntry.start_time)
    )
    return list(result.scalars().all())


# ── Compliance engine ─────────────────────────────────────────────────────────

def _split_entry_by_day(
    entry: TimeEntry, tz: ZoneInfo
) -> dict[date, int]:
    """
    Split a cross-midnight entry into per-local-day minutes.
    Returns {local_date: net_minutes_on_that_day}
    """
    result: dict[date, int] = {}
    start_local = entry.start_time.astimezone(tz)
    end_local = entry.end_time.astimezone(tz)

    current = start_local
    while current.date() < end_local.date():
        # End of current day
        day_end = current.replace(hour=23, minute=59, second=59, microsecond=999999)
        minutes = int((day_end - current).total_seconds() / 60) + 1
        result[current.date()] = result.get(current.date(), 0) + minutes
        # Move to next day start
        next_day = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        current = next_day

    # Remaining time on final day
    minutes = int((end_local - current).total_seconds() / 60)
    if minutes > 0:
        result[current.date()] = result.get(current.date(), 0) + minutes

    # Apply break to longest day proportionally (simple: subtract from first day)
    if result and entry.break_minutes > 0:
        first_day = min(result.keys())
        result[first_day] = max(0, result[first_day] - entry.break_minutes)

    return result


async def run_compliance(
    db: AsyncSession,
    sheet: Timesheet,
    tenant_id: uuid.UUID,
) -> list[ComplianceResult]:
    """
    Evaluate all active compliance rules against a timesheet.
    Uses rule snapshot at evaluation time.
    Stores per-day breakdown.
    """
    tz = await _get_tenant_tz(db, tenant_id)
    now = datetime.now(timezone.utc)

    # Load only entries for this sheet
    entries_result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.timesheet_id == sheet.id,
            TimeEntry.is_deleted == False,
            TimeEntry.status != "rejected",
            TimeEntry.is_adjustment == False,
        )
    )
    entries = list(entries_result.scalars().all())

    # Build per-day map (local timezone)
    per_day: dict[date, int] = {}
    for entry in entries:
        day_minutes = _split_entry_by_day(entry, tz)
        for d, mins in day_minutes.items():
            per_day[d] = per_day.get(d, 0) + mins

    # Load lookback entries (7 days before week_start, for rest period checks)
    lookback_start = sheet.week_start - timedelta(days=7)
    lookback_result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.tenant_id == tenant_id,
            TimeEntry.user_id == sheet.user_id,
            TimeEntry.work_date >= lookback_start,
            TimeEntry.work_date < sheet.week_start,
            TimeEntry.is_deleted == False,
            TimeEntry.status != "rejected",
            TimeEntry.is_adjustment == False,
        )
    )
    lookback_entries = list(lookback_result.scalars().all())

    # Load active rules
    rules_result = await db.execute(
        select(ComplianceRule).where(
            ComplianceRule.tenant_id == tenant_id,
            ComplianceRule.is_active == True,
            ComplianceRule.is_deleted == False,
        )
    )
    rules = list(rules_result.scalars().all())

    results = []
    for rule in rules:
        params = {}
        if rule.parameters_json:
            try:
                params = json.loads(rule.parameters_json)
            except Exception:
                params = {}

        rule_snapshot = {
            "rule_code": rule.rule_code,
            "severity": rule.severity,
            "action": rule.action,
            "parameters": params,
        }

        violations = _evaluate_rule(rule, params, per_day, entries, lookback_entries, tz)

        for violation in violations:
            # Check idempotency: skip if same rule+sheet+day already has violation record
            existing_result = await db.execute(
                select(ComplianceResult).where(
                    ComplianceResult.timesheet_id == sheet.id,
                    ComplianceResult.rule_id == rule.id,
                    ComplianceResult.occurred_on == violation["occurred_on"],
                    ComplianceResult.status == "violation",
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                results.append(existing)
                continue

            cr = ComplianceResult(
                tenant_id=tenant_id,
                timesheet_id=sheet.id,
                rule_id=rule.id,
                rule_code=rule.rule_code,
                severity=rule.severity,
                status="violation",
                occurred_on=violation["occurred_on"],
                rule_snapshot_json=json.dumps(rule_snapshot),
                per_day_json=json.dumps({str(k): v for k, v in per_day.items()}),
                details_json=json.dumps(violation["details"]),
                evaluated_at=now,
            )
            db.add(cr)
            await db.flush()
            results.append(cr)

            # Auto-NC for critical rules
            if rule.action == "auto_nc" and rule.severity == "critical":
                await _create_compliance_nc(db, tenant_id, sheet, cr, rule)

        # If no violations, record a pass (update or create)
        if not violations:
            pass_result = await db.execute(
                select(ComplianceResult).where(
                    ComplianceResult.timesheet_id == sheet.id,
                    ComplianceResult.rule_id == rule.id,
                    ComplianceResult.status == "pass",
                )
            )
            if not pass_result.scalar_one_or_none():
                cr = ComplianceResult(
                    tenant_id=tenant_id,
                    timesheet_id=sheet.id,
                    rule_id=rule.id,
                    rule_code=rule.rule_code,
                    severity=rule.severity,
                    status="pass",
                    evaluated_at=now,
                    rule_snapshot_json=json.dumps(rule_snapshot),
                    per_day_json=json.dumps({str(k): v for k, v in per_day.items()}),
                )
                db.add(cr)
                await db.flush()

    return results


def _evaluate_rule(
    rule: ComplianceRule,
    params: dict,
    per_day: dict[date, int],
    entries: list[TimeEntry],
    lookback_entries: list[TimeEntry],
    tz: ZoneInfo,
) -> list[dict]:
    """
    Returns list of violations: [{"occurred_on": date, "details": dict}]
    Supports rule codes:
      MAX_DAILY_HOURS   – max_minutes per day
      MAX_WEEKLY_HOURS  – max_minutes per week
      MIN_REST_PERIOD   – min_rest_minutes between shifts
    """
    violations = []

    if rule.rule_code == "MAX_DAILY_HOURS":
        max_min = params.get("max_minutes", 600)
        for day, minutes in per_day.items():
            if minutes > max_min:
                violations.append({
                    "occurred_on": day,
                    "details": {
                        "actual_minutes": minutes,
                        "max_minutes": max_min,
                        "excess_minutes": minutes - max_min,
                    }
                })

    elif rule.rule_code == "MAX_WEEKLY_HOURS":
        max_min = params.get("max_minutes", 2400)
        total = sum(per_day.values())
        if total > max_min:
            violations.append({
                "occurred_on": None,
                "details": {
                    "actual_minutes": total,
                    "max_minutes": max_min,
                    "excess_minutes": total - max_min,
                }
            })

    elif rule.rule_code == "MIN_REST_PERIOD":
        min_rest = params.get("min_rest_minutes", 660)  # 11 hours default
        all_entries = sorted(lookback_entries + entries, key=lambda e: e.start_time)
        for i in range(1, len(all_entries)):
            prev = all_entries[i - 1]
            curr = all_entries[i]
            gap = int((curr.start_time - prev.end_time).total_seconds() / 60)
            if gap < min_rest:
                violations.append({
                    "occurred_on": curr.work_date,
                    "details": {
                        "actual_rest_minutes": gap,
                        "min_rest_minutes": min_rest,
                        "deficit_minutes": min_rest - gap,
                        "prev_entry_id": str(prev.id),
                        "curr_entry_id": str(curr.id),
                    }
                })

    return violations


async def _create_compliance_nc(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    sheet: Timesheet,
    cr: ComplianceResult,
    rule: ComplianceRule,
) -> None:
    from app.core.nonconformance.models import Nonconformance
    from app.core.nonconformance.service import generate_nc_no
    from app.core.audit.service import audit

    # Idempotency: source_key = timesheet_id + rule_code + occurred_on
    source_key = f"{sheet.id}:{rule.rule_code}:{cr.occurred_on}"
    existing = await db.execute(
        select(Nonconformance).where(
            Nonconformance.tenant_id == tenant_id,
            Nonconformance.source_type == "compliance",
            Nonconformance.source_id == sheet.id,
            Nonconformance.source_key == source_key,
            Nonconformance.is_deleted == False,
        )
    )
    if existing.scalar_one_or_none():
        return  # already created

    nc_no = await generate_nc_no(db, tenant_id, sheet.project_id)
    nc = Nonconformance(
        tenant_id=tenant_id,
        project_id=sheet.project_id,
        nc_no=nc_no,
        title=f"Compliance: {rule.title}",
        description=f"Auto-NC fra compliance regel {rule.rule_code}. Timesheet: {sheet.id}",
        nc_type="nonconformance",
        severity="high",
        status="open",
        source_type="compliance",
        source_id=sheet.id,
        source_key=source_key,
        owner_user_id=None,
    )
    db.add(nc)
    await db.flush()

    await audit(db, tenant_id=tenant_id, user_id=sheet.user_id,
        action="compliance.auto_nc", resource_type="compliance_result",
        resource_id=str(cr.id),
        detail={"rule_code": rule.rule_code, "nc_no": nc_no, "source_key": source_key},
    )


async def resolve_violation(
    db: AsyncSession,
    result_id: uuid.UUID,
    resolved_by: uuid.UUID,
    tenant_id: uuid.UUID,
    data: ViolationResolveRequest,
) -> ComplianceResult:
    from fastapi import HTTPException
    result = await db.execute(
        select(ComplianceResult).where(
            ComplianceResult.id == result_id,
            ComplianceResult.tenant_id == tenant_id,
        )
    )
    cr = result.scalar_one_or_none()
    if not cr:
        raise HTTPException(404, "Compliance result not found")
    if cr.status != "violation":
        raise HTTPException(400, f"Cannot resolve result with status '{cr.status}'")

    cr.status = "resolved"
    cr.resolved_at = datetime.now(timezone.utc)
    cr.resolved_by = resolved_by
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=resolved_by,
        action="compliance.resolve", resource_type="compliance_result",
        resource_id=str(cr.id),
        detail={"resolution_note": data.resolution_note},
    )
    await db.refresh(cr)
    return cr


# ── Compliance rules CRUD ─────────────────────────────────────────────────────

async def create_rule(
    db: AsyncSession, tenant_id: uuid.UUID, data: ComplianceRuleCreate
) -> ComplianceRule:
    rule = ComplianceRule(tenant_id=tenant_id, **data.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


async def list_rules(db: AsyncSession, tenant_id: uuid.UUID) -> list[ComplianceRule]:
    result = await db.execute(
        select(ComplianceRule).where(
            ComplianceRule.tenant_id == tenant_id,
            ComplianceRule.is_deleted == False,
        ).order_by(ComplianceRule.rule_code)
    )
    return list(result.scalars().all())


# ── Payroll export ────────────────────────────────────────────────────────────

async def generate_export(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: PayrollExportCreate,
    generated_by: uuid.UUID,
) -> PayrollExport:
    from fastapi import HTTPException
    now = datetime.now(timezone.utc)

    # Find approved sheets in period
    q = select(Timesheet).where(
        Timesheet.tenant_id == tenant_id,
        Timesheet.status == "approved",
        Timesheet.week_start >= data.period_start,
        Timesheet.week_end <= data.period_end,
        Timesheet.is_deleted == False,
    )
    if data.project_id:
        q = q.where(Timesheet.project_id == data.project_id)
    result = await db.execute(q)
    sheets = list(result.scalars().all())

    if not sheets:
        raise HTTPException(400, "No approved timesheets found for the given period")

    # Double export prevention – check no sheet already in non-voided export
    sheet_ids = [s.id for s in sheets]
    existing_lines = await db.execute(
        select(PayrollExportLine)
        .join(PayrollExport, PayrollExport.id == PayrollExportLine.export_id)
        .where(
            PayrollExportLine.timesheet_id.in_(sheet_ids),
            PayrollExport.status != "voided",
            PayrollExport.tenant_id == tenant_id,
        )
    )
    dupes = list(existing_lines.scalars().all())
    if dupes:
        raise HTTPException(400, f"{len(dupes)} timesheet(s) already included in a non-voided export")

    export = PayrollExport(
        tenant_id=tenant_id,
        period_start=data.period_start,
        period_end=data.period_end,
        status="generated",
        generated_by=generated_by,
        generated_at=now,
    )
    db.add(export)
    await db.flush()

    for sheet in sheets:
        # Load entries for this sheet
        entries_result = await db.execute(
            select(TimeEntry).where(
                TimeEntry.timesheet_id == sheet.id,
                TimeEntry.is_deleted == False,
                TimeEntry.status != "rejected",
            )
        )
        entries = list(entries_result.scalars().all())

        # Net minutes = sum of regular entries + adjustments
        net_minutes = sum(
            e.delta_minutes if e.is_adjustment else e.net_minutes
            for e in entries
        )
        entry_ids = [str(e.id) for e in entries if not e.is_adjustment]

        line = PayrollExportLine(
            tenant_id=tenant_id,
            export_id=export.id,
            timesheet_id=sheet.id,
            user_id=sheet.user_id,
            project_id=sheet.project_id,
            net_minutes=net_minutes,
            source_entry_ids_json=json.dumps(entry_ids),
        )
        db.add(line)

    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=generated_by,
        action="payroll_export.generate", resource_type="payroll_export",
        resource_id=str(export.id),
        detail={"period_start": str(data.period_start), "period_end": str(data.period_end),
                "sheet_count": len(sheets)},
    )
    await db.refresh(export)
    return export


async def mark_export_sent(
    db: AsyncSession,
    export_id: uuid.UUID,
    sent_by: uuid.UUID,
    tenant_id: uuid.UUID,
) -> PayrollExport:
    from fastapi import HTTPException
    result = await db.execute(
        select(PayrollExport).where(
            PayrollExport.id == export_id,
            PayrollExport.tenant_id == tenant_id,
        ).with_for_update()
    )
    export = result.scalar_one_or_none()
    if not export:
        raise HTTPException(404, "Export not found")
    if export.status == "sent":
        return export  # idempotent
    if export.status != "generated":
        raise HTTPException(400, f"Cannot mark sent with status '{export.status}'")

    export.status = "sent"
    export.sent_at = datetime.now(timezone.utc)
    export.sent_by = sent_by
    await db.flush()

    # Lock all related timesheets
    lines_result = await db.execute(
        select(PayrollExportLine).where(PayrollExportLine.export_id == export.id)
    )
    for line in lines_result.scalars().all():
        sheet_result = await db.execute(
            select(Timesheet).where(Timesheet.id == line.timesheet_id).with_for_update()
        )
        sheet = sheet_result.scalar_one_or_none()
        if sheet and sheet.status == "approved":
            sheet.status = "locked"
            sheet.locked_at = datetime.now(timezone.utc)
            sheet.locked_by = sent_by

    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=sent_by,
        action="payroll_export.sent", resource_type="payroll_export",
        resource_id=str(export.id), detail={},
    )
    await db.refresh(export)
    return export


async def void_export(
    db: AsyncSession,
    export_id: uuid.UUID,
    voided_by: uuid.UUID,
    tenant_id: uuid.UUID,
    data: VoidExportRequest,
) -> PayrollExport:
    from fastapi import HTTPException
    result = await db.execute(
        select(PayrollExport).where(
            PayrollExport.id == export_id,
            PayrollExport.tenant_id == tenant_id,
        ).with_for_update()
    )
    export = result.scalar_one_or_none()
    if not export:
        raise HTTPException(404, "Export not found")
    if export.status == "voided":
        return export  # idempotent
    if export.status == "sent":
        raise HTTPException(400, "Cannot void a sent export. Unlock timesheets manually first.")

    export.status = "voided"
    export.voided_at = datetime.now(timezone.utc)
    export.voided_by = voided_by
    export.void_reason = data.reason
    await db.flush()

    from app.core.audit.service import audit
    await audit(db, tenant_id=tenant_id, user_id=voided_by,
        action="payroll_export.void", resource_type="payroll_export",
        resource_id=str(export.id), detail={"reason": data.reason},
    )
    await db.refresh(export)
    return export


async def get_export(db: AsyncSession, export_id: uuid.UUID) -> PayrollExport | None:
    result = await db.execute(
        select(PayrollExport).where(
            PayrollExport.id == export_id,
            PayrollExport.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_exports(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[PayrollExport]:
    result = await db.execute(
        select(PayrollExport).where(
            PayrollExport.tenant_id == tenant_id,
            PayrollExport.is_deleted == False,
        ).order_by(PayrollExport.generated_at.desc())
    )
    return list(result.scalars().all())
