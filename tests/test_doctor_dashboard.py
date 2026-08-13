from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.api.deps import require_doctor
from app.api.v1 import doctors
from app.main import app

DOCTOR_ID = "00000000-0000-0000-0000-000000000010"
PATIENT_ID = "00000000-0000-0000-0000-000000000020"
OTHER_PATIENT_ID = "00000000-0000-0000-0000-000000000021"


class Query:
    def __init__(self, client: "FakeClient", name: str):
        self.client = client
        self.name = name
        self.filters: list[tuple[str, str, object]] = []
        self.order_field: str | None = None
        self.desc = False
        self.row_limit: int | None = None

    def select(self, *_args): return self
    def eq(self, field, value): self.filters.append((field, "eq", value)); return self
    def gte(self, field, value): self.filters.append((field, "gte", value)); return self
    def lte(self, field, value): self.filters.append((field, "lte", value)); return self
    def lt(self, field, value): self.filters.append((field, "lt", value)); return self
    def in_(self, field, values): self.filters.append((field, "in", {str(value) for value in values})); return self
    def order(self, field, desc=False): self.order_field = field; self.desc = desc; return self
    def limit(self, value): self.row_limit = value; return self

    def execute(self):
        rows = [dict(row) for row in self.client.tables.get(self.name, [])]
        for field, operation, expected in self.filters:
            if operation == "eq": rows = [row for row in rows if str(row.get(field)).lower() == str(expected).lower()]
            elif operation == "in": rows = [row for row in rows if str(row.get(field)) in expected]
            elif operation == "gte": rows = [row for row in rows if str(row.get(field)) >= str(expected)]
            elif operation == "lte": rows = [row for row in rows if str(row.get(field)) <= str(expected)]
            elif operation == "lt": rows = [row for row in rows if str(row.get(field)) < str(expected)]
        if self.order_field:
            rows.sort(key=lambda row: str(row.get(self.order_field, "")), reverse=self.desc)
        if self.row_limit is not None: rows = rows[:self.row_limit]
        return SimpleNamespace(data=rows)


class FakeClient:
    def __init__(self):
        now = datetime.now(timezone.utc)
        today_wib = now.astimezone(ZoneInfo("Asia/Jakarta")).date()
        yesterday = today_wib - timedelta(days=1)
        yesterday_at_noon_wib = datetime.combine(yesterday, datetime.min.time(), ZoneInfo("Asia/Jakarta")) + timedelta(hours=12)
        self.tables = {
            "users": [
                {"id": PATIENT_ID, "doctor_id": DOCTOR_ID, "role": "child", "is_active": True},
                {"id": OTHER_PATIENT_ID, "doctor_id": "other-doctor", "role": "child", "is_active": True},
            ],
            "blood_glucose_records": [
                {"id": "g-2", "patient_id": PATIENT_ID, "value_mg_dl": 130, "recorded_at": (now - timedelta(hours=1)).isoformat()},
                {"id": "g-1", "patient_id": PATIENT_ID, "value_mg_dl": 120, "recorded_at": (now - timedelta(days=1)).isoformat()},
            ],
            "food_logs": [
                {"id": "f-1", "child_id": PATIENT_ID, "consumed_at": yesterday_at_noon_wib.astimezone(timezone.utc).isoformat(), "nutrition": {"sugar_g": 3, "carbs_g": 20, "protein_g": 5, "fiber_g": 2, "fat_g": 4}},
                {"id": "f-2", "child_id": PATIENT_ID, "consumed_at": (yesterday_at_noon_wib + timedelta(hours=2)).astimezone(timezone.utc).isoformat(), "nutrition": {"sugar_g": 2, "carbs_g": 10, "protein_g": 4, "fiber_g": 1, "fat_g": 3}},
            ],
            "schedule_occurrences": [
                {"id": "o-1", "child_id": PATIENT_ID, "schedule_id": "s-1", "occurrence_date": yesterday.isoformat(), "status": "done", "completed_at": None},
                {"id": "o-2", "child_id": PATIENT_ID, "schedule_id": "s-1", "occurrence_date": (yesterday - timedelta(days=1)).isoformat(), "status": "late", "completed_at": None},
                {"id": "o-3", "child_id": PATIENT_ID, "schedule_id": "s-1", "occurrence_date": (yesterday - timedelta(days=2)).isoformat(), "status": "not_yet", "completed_at": None},
                {"id": "o-4", "child_id": PATIENT_ID, "schedule_id": "meal-1", "occurrence_date": yesterday.isoformat(), "status": "skipped", "completed_at": None},
            ],
            "custom_meal_schedules": [
                {"id": "s-1", "schedule_type": "medicine", "start_time": "08:00:00", "end_time": "09:00:00"},
                {"id": "meal-1", "schedule_type": "meal", "start_time": "08:00:00", "end_time": "09:00:00"},
            ],
            "doctor_appointments": [
                {"id": "a-future", "patient_id": PATIENT_ID, "doctor_id": DOCTOR_ID, "title": "Future", "starts_at": (now + timedelta(days=2)).isoformat(), "status": "scheduled", "note": None, "price_amount": None, "currency": None},
                {"id": "a-past", "patient_id": PATIENT_ID, "doctor_id": DOCTOR_ID, "title": "Elapsed", "starts_at": (now - timedelta(days=2)).isoformat(), "status": "scheduled", "note": "Review", "price_amount": 100000, "currency": "IDR"},
            ],
        }

    def table(self, name): return Query(self, name)


def setup(monkeypatch):
    client = FakeClient()
    activities = []
    monkeypatch.setattr(doctors, "get_supabase_service_client", lambda: client)
    monkeypatch.setattr(doctors, "record_activity", lambda **kwargs: activities.append(kwargs))
    app.dependency_overrides[require_doctor] = lambda: {"id": DOCTOR_ID, "role": "doctor"}
    return activities


def request(monkeypatch, path):
    activities = setup(monkeypatch)
    try:
        response = TestClient(app).get(path)
    finally:
        app.dependency_overrides.clear()
    return response, activities


def test_glucose_returns_latest_records_oldest_to_newest_and_audits(monkeypatch):
    response, activities = request(monkeypatch, f"/api/v1/doctors/me/patients/{PATIENT_ID}/blood-glucose?limit=5")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["g-1", "g-2"]
    assert response.json()["items"][-1]["recordedAt"].endswith("Z")
    assert activities[0]["action"] == "blood_glucose.list"
    assert activities[0]["child_id"] == PATIENT_ID


def test_nutrition_returns_seven_wib_days_and_zero_fills(monkeypatch):
    response, activities = request(monkeypatch, f"/api/v1/doctors/me/patients/{PATIENT_ID}/nutrition?days=7&timezone=Asia%2FJakarta")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 7
    assert body["period"]["timezone"] == "Asia/Jakarta"
    assert sum(item["sugarGrams"] for item in body["items"]) == 5
    assert sum(item["carbohydratesGrams"] for item in body["items"]) == 30
    assert activities[0]["action"] == "nutrition.view"


def test_adherence_counts_only_medicine_occurrences_and_elapsed_not_yet(monkeypatch):
    response, activities = request(monkeypatch, f"/api/v1/doctors/me/patients/{PATIENT_ID}/medication-adherence?days=30&timezone=Asia%2FJakarta")
    assert response.status_code == 200
    assert response.json()["counts"] == {"taken": 1, "takenLate": 1, "skipped": 1}
    assert activities[0]["action"] == "medication_adherence.view"


def test_appointments_move_elapsed_schedule_to_history_without_completing(monkeypatch):
    response, activities = request(monkeypatch, f"/api/v1/doctors/me/patients/{PATIENT_ID}/appointments")
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["upcoming"]] == ["a-future"]
    assert [item["id"] for item in body["history"]] == ["a-past"]
    assert body["history"][0]["status"] == "scheduled"
    assert activities[0]["action"] == "appointment.list"


def test_clinical_reads_reject_cross_doctor_patient_without_audit(monkeypatch):
    response, activities = request(monkeypatch, f"/api/v1/doctors/me/patients/{OTHER_PATIENT_ID}/blood-glucose")
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert OTHER_PATIENT_ID not in response.text
    assert activities == []
