import pytest
from app.core.incidents.service import VALID_TRANSITIONS


def test_valid_transitions_complete():
    assert VALID_TRANSITIONS["draft"] == ["submitted"]
    assert VALID_TRANSITIONS["submitted"] == ["triage"]
    assert VALID_TRANSITIONS["triage"] == ["open"]
    assert VALID_TRANSITIONS["open"] == ["closed"]
    assert VALID_TRANSITIONS["closed"] == []


def test_incident_no_format():
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    yy = str(year)[-2:]
    no = f"RUH-{yy}-{1:04d}"
    assert no == f"RUH-{yy}-0001"
    assert len(no) == 11


def test_nc_no_format():
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    yy = str(year)[-2:]
    no = f"NC-{yy}-{1:04d}"
    assert no == f"NC-{yy}-0001"
    assert len(no) == 10
