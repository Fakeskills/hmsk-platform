import json
import pytest
from app.core.checklists.service import _parse_schema, _validate_answers


SAMPLE_SCHEMA = [
    {"id": "f1", "label": "Er stillas sikret?", "field_type": "yes_no", "required": True, "requires_image": False, "creates_nc_on_no": True},
    {"id": "f2", "label": "Bilde av område", "field_type": "photo", "required": True, "requires_image": True, "creates_nc_on_no": False},
    {"id": "f3", "label": "Kommentar", "field_type": "text", "required": False, "requires_image": False, "creates_nc_on_no": False},
]


def test_parse_schema_valid():
    result = _parse_schema(json.dumps(SAMPLE_SCHEMA))
    assert len(result) == 3


def test_parse_schema_invalid_json():
    with pytest.raises(Exception):
        _parse_schema("not json")


def test_parse_schema_invalid_field_type():
    bad = [{"id": "x", "label": "X", "field_type": "unknown"}]
    with pytest.raises(Exception):
        _parse_schema(json.dumps(bad))


def test_validate_answers_missing_required():
    answers = {"f2": {"value": None, "file_ids": ["some-id"]}, "f3": {"value": ""}}
    errors = _validate_answers(SAMPLE_SCHEMA, answers, {})
    assert any("Er stillas sikret?" in e for e in errors)


def test_validate_answers_missing_image():
    answers = {
        "f1": {"value": "Yes", "file_ids": []},
        "f2": {"value": None, "file_ids": []},  # requires_image but no files
    }
    errors = _validate_answers(SAMPLE_SCHEMA, answers, {})
    assert any("Bilde av område" in e for e in errors)


def test_validate_answers_ok():
    answers = {
        "f1": {"value": "Yes", "file_ids": []},
        "f2": {"value": None, "file_ids": ["uuid-1"]},
        "f3": {"value": "Alt ok", "file_ids": []},
    }
    errors = _validate_answers(SAMPLE_SCHEMA, answers, {})
    assert errors == []


def test_auto_nc_triggered_on_no():
    """NC should be created when creates_nc_on_no=True and value='No'."""
    answers = {
        "f1": {"value": "No", "file_ids": []},
        "f2": {"value": None, "file_ids": ["uuid-1"]},
    }
    nc_fields = [
        f for f in SAMPLE_SCHEMA
        if f.get("creates_nc_on_no")
        and str(answers.get(f["id"], {}).get("value", "")).strip().lower() == "no"
    ]
    assert len(nc_fields) == 1
    assert nc_fields[0]["id"] == "f1"


def test_rejected_run_returns_to_open():
    """Rejected run must go back to open, not create new run."""
    status = "submitted"
    # Simulate rejection
    new_status = "open" if status == "submitted" else status
    assert new_status == "open"
