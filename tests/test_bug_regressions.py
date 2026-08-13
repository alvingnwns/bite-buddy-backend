import asyncio
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.api.v1 import children, parents
from app.services.gamification_service import GamificationService


CHILD_ID = "00000000-0000-0000-0000-000000000020"
PARENT_ID = "00000000-0000-0000-0000-000000000030"


def upload(data: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(data),
        filename="camera-image",
        headers=Headers({"content-type": content_type}),
    )


def test_octet_stream_jpeg_is_detected_from_file_signature():
    data, mime_type = asyncio.run(
        children._image_bytes(upload(b"\xff\xd8\xff\xe0image", "application/octet-stream"))
    )
    assert data.startswith(b"\xff\xd8\xff")
    assert mime_type == "image/jpeg"


def test_invalid_octet_stream_remains_rejected():
    with pytest.raises(HTTPException) as error:
        asyncio.run(children._image_bytes(upload(b"not-an-image", "application/octet-stream")))
    assert error.value.status_code == 415


def test_parent_reminder_targets_child_account_only(monkeypatch):
    inserted = {}

    class Query:
        def insert(self, payload):
            inserted.update(payload)
            return self

        def execute(self):
            return SimpleNamespace(data=[{"id": "reminder-1", **inserted}])

    class Client:
        def table(self, name):
            assert name == "alerts"
            return Query()

    monkeypatch.setattr(parents, "assert_parent_child", lambda *_args: {})
    monkeypatch.setattr(parents, "get_supabase_service_client", lambda: Client())
    monkeypatch.setattr(parents, "record_activity", lambda **_kwargs: None)

    result = parents.send_reminder(
        CHILD_ID,
        parents.ReminderRequest(reminderType="eat"),
        identity={"id": PARENT_ID, "role": "parent"},
    )

    assert inserted["child_id"] == CHILD_ID
    assert inserted["recipient_user_id"] == CHILD_ID
    assert result["notification"]["childId"] == CHILD_ID


def test_level_progression_uses_level_aware_threshold_and_reward():
    assert GamificationService.level_threshold(1) == 250
    assert GamificationService.level_threshold(2) == 350
    assert GamificationService.xp_gain(1) == 12
    assert GamificationService.xp_gain(2) == 23


def test_food_progression_migration_wraps_atomic_confirmation():
    sql = open(
        "migrations/017_food_analysis_corrections_pet_progression.sql",
        encoding="utf-8",
    ).read()
    assert "confirm_child_analysis_legacy" in sql
    assert "v_hp_delta := CASE WHEN p_is_healthy THEN 5 ELSE -15 END" in sql
    assert "v_threshold := (100 * v_level) + 150" in sql
    assert "recipient_user_id" in sql
