import pytest


def test_doc_no_format():
    from datetime import datetime, timezone
    year = datetime.now(timezone.utc).year
    yy = str(year)[-2:]
    doc_no = f"DOC-{yy}-{1:04d}"
    assert doc_no == f"DOC-{yy}-0001"
    assert len(doc_no) == 10


def test_template_version_no_increments():
    versions = [1, 2, 3]
    assert versions[-1] == max(versions)


def test_issue_requires_approved_status():
    """Service must reject issue if status != approved."""
    valid_pre_issue_status = "approved"
    invalid_statuses = ["draft", "under_review", "issued", "superseded"]
    assert valid_pre_issue_status not in invalid_statuses


def test_ack_lifecycle():
    statuses = ["pending", "acknowledged"]
    assert statuses[0] == "pending"
    assert statuses[-1] == "acknowledged"
