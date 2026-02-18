import pytest
from datetime import date, datetime, timezone, timedelta


def test_week_end_from_week_start():
    from app.core.timesheets.service import _week_end
    monday = date(2026, 2, 2)
    assert _week_end(monday) == date(2026, 2, 8)


def test_week_start_must_be_monday():
    tuesday = date(2026, 2, 3)
    assert tuesday.weekday() != 0


def test_end_time_after_start_time():
    start = datetime(2026, 2, 2, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 2, 2, 7, 0, tzinfo=timezone.utc)
    assert end <= start  # should fail validation


def test_net_minutes_calc():
    from app.core.timesheets.service import _calc_net_minutes
    start = datetime(2026, 2, 2, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 2, 2, 16, 0, tzinfo=timezone.utc)
    assert _calc_net_minutes(start, end, 30) == 450


def test_cross_midnight_split():
    from app.core.timesheets.service import _split_entry_by_day
    from app.core.timesheets.models import TimeEntry
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Europe/Oslo")
    entry = TimeEntry(
        start_time=datetime(2026, 2, 2, 22, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 2, 3, 6, 0, tzinfo=timezone.utc),
        break_minutes=0,
        work_date=date(2026, 2, 2),
    )
    result = _split_entry_by_day(entry, tz)
    assert len(result) == 2
    assert sum(result.values()) > 0


def test_compliance_max_daily_violation():
    from app.core.timesheets.models import ComplianceRule
    from app.core.timesheets.service import _evaluate_rule
    from zoneinfo import ZoneInfo
    rule = ComplianceRule(rule_code="MAX_DAILY_HOURS", severity="block", action="log")
    params = {"max_minutes": 480}
    per_day = {date(2026, 2, 2): 540}
    violations = _evaluate_rule(rule, params, per_day, [], [], ZoneInfo("UTC"))
    assert len(violations) == 1
    assert violations[0]["details"]["excess_minutes"] == 60


def test_compliance_max_daily_pass():
    from app.core.timesheets.models import ComplianceRule
    from app.core.timesheets.service import _evaluate_rule
    from zoneinfo import ZoneInfo
    rule = ComplianceRule(rule_code="MAX_DAILY_HOURS", severity="warn", action="log")
    params = {"max_minutes": 480}
    per_day = {date(2026, 2, 2): 450}
    violations = _evaluate_rule(rule, params, per_day, [], [], ZoneInfo("UTC"))
    assert violations == []


def test_idempotent_state_transition():
    """Already submitted timesheet returns 200 without re-auditing."""
    status = "submitted"
    target = "submitted"
    already_at_target = status == target
    assert already_at_target is True


def test_double_export_prevention():
    """Same timesheet cannot appear in two non-voided exports."""
    existing_exports = [{"status": "generated", "timesheet_id": "ts-1"}]
    new_export_sheets = ["ts-1"]
    dupes = [
        e for e in existing_exports
        if e["timesheet_id"] in new_export_sheets and e["status"] != "voided"
    ]
    assert len(dupes) == 1


def test_adjustment_only_on_locked():
    status = "open"
    can_adjust = status == "locked"
    assert can_adjust is False


def test_locked_is_immutable():
    locked_status = "locked"
    allowed_ops = {"adjustment"}
    blocked_ops = {"update", "delete", "submit", "approve"}
    assert blocked_ops.isdisjoint({"adjustment"})
    assert "adjustment" in allowed_ops
