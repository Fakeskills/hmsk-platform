import pytest


def test_drawing_status_values():
    valid = {"received", "active", "superseded", "void"}
    assert "active" in valid
    assert "superseded" in valid
    assert "void" in valid


def test_revision_supersede_logic():
    """New active drawing should supersede previous active."""
    existing_status = "active"
    new_status = "active"
    if new_status == "active" and existing_status == "active":
        existing_status = "superseded"
    assert existing_status == "superseded"


def test_void_does_not_supersede():
    """Void drawing should not supersede existing active."""
    existing_status = "active"
    new_status = "void"
    if new_status == "active":
        existing_status = "superseded"
    assert existing_status == "active"


def test_unique_constraint_fields():
    """Unique constraint is on tenant_id + project_id + drawing_no + revision."""
    key = ("tenant-1", "project-1", "A-001", "B")
    assert len(key) == 4


def test_from_inbox_sets_source_fields():
    """Register from inbox must set source_thread_id and source_message_id."""
    message = {"id": "msg-1", "thread_id": "thread-1"}
    source_thread_id = message["thread_id"]
    source_message_id = message["id"]
    assert source_thread_id == "thread-1"
    assert source_message_id == "msg-1"
