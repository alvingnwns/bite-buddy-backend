import asyncio
from datetime import date
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.api.v1 import children, parents
from app.services.gamification_service import GamificationService
from app.services.integration_service import _schedule_occurs_on


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


def test_medium_sugar_is_healthy_and_high_sugar_is_not():
    assert children._is_healthy_sugar(5)
    assert children._is_healthy_sugar(14.99)
    assert not children._is_healthy_sugar(15)


def test_food_progression_migration_wraps_atomic_confirmation():
    sql = open(
        "migrations/017_food_analysis_corrections_pet_progression.sql",
        encoding="utf-8",
    ).read()
    assert "confirm_child_analysis_legacy" in sql
    assert "v_hp_delta := CASE WHEN p_is_healthy THEN 5 ELSE -15 END" in sql
    assert "v_threshold := (100 * v_level) + 150" in sql
    assert "recipient_user_id" in sql


def test_pet_progression_is_idempotent_and_medicine_does_not_change_pet():
    sql = open("migrations/018_pet_progression_idempotency.sql", encoding="utf-8").read()
    assert "FOR UPDATE" in sql
    assert "v_draft.status = 'confirmed'" in sql
    assert "confirm_child_analysis_legacy" in sql
    assert "p_analysis_type = 'medicine'" in sql
    assert "experience_points = v_previous_exp" in sql
    assert "recipient_user_id = p_child_id" in sql


def test_unhealthy_food_does_not_receive_xp():
    sql = open("migrations/019_healthy_food_xp_rule.sql", encoding="utf-8").read()
    assert "p_analysis_type = 'food' AND NOT p_is_healthy" in sql
    assert "experience_points = v_previous_exp" in sql
    assert "the -15 HP and warning created by the wrapped function remain unchanged" in sql


def test_doctor_medication_recurrence_is_visible_on_correct_dates():
    anchor = date(2026, 8, 14)
    base = {
        "schedule_type": "medicine",
        "day_of_week": anchor.weekday(),
        "recurrence_anchor_date": anchor.isoformat(),
    }
    assert _schedule_occurs_on({**base, "recurrence_type": "everyday"}, date(2026, 8, 15))
    assert _schedule_occurs_on({**base, "recurrence_type": "every_x_days", "recurrence_interval_days": 3}, date(2026, 8, 17))
    assert not _schedule_occurs_on({**base, "recurrence_type": "every_x_days", "recurrence_interval_days": 3}, date(2026, 8, 16))
    assert _schedule_occurs_on({**base, "recurrence_type": "once_a_week"}, date(2026, 8, 21))
    assert _schedule_occurs_on({**base, "recurrence_type": "once_a_month"}, date(2026, 9, 14))


def test_migration_materializes_and_backfills_doctor_medication_schedules():
    sql = open("migrations/020_doctor_medication_schedules.sql", encoding="utf-8").read()
    assert "sync_doctor_medication_schedules" in sql
    assert "managed_by_doctor" in sql
    assert "claim_patient_invitation_v012" in sql
    assert "Backfill schedules" in sql


def test_medicine_confirmation_has_no_python_pet_reward(monkeypatch):
    service = GamificationService()
    captured = {}

    def update(_child_id, exp_delta, happiness_delta, hunger_delta):
        captured.update(exp=exp_delta, happiness=happiness_delta, hunger=hunger_delta)
        return captured

    monkeypatch.setattr(service, "update_pet_status", update)
    service.evaluate_medicine_compliance(CHILD_ID)
    assert captured == {"exp": 0, "happiness": 0, "hunger": 0}
