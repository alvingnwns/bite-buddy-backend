from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.deps import require_doctor
from app.api.v1 import doctors
from app.main import app

DOCTOR_ID = "00000000-0000-0000-0000-000000000010"
OTHER_DOCTOR_ID = "00000000-0000-0000-0000-000000000011"
PATIENT_ID = "00000000-0000-0000-0000-000000000020"
OTHER_PATIENT_ID = "00000000-0000-0000-0000-000000000021"
INVITATION_ID = "00000000-0000-0000-0000-000000000030"


class Query:
    def __init__(self, client: "FakeClient", table: str):
        self.client = client
        self.name = table
        self.filters: list[tuple[str, object]] = []
        self.inserted = None
        self.updated = None
        self.row_limit = None

    def select(self, *_args): return self
    def order(self, *_args, **_kwargs): return self
    def limit(self, value): self.row_limit = value; return self
    def eq(self, field, value): self.filters.append((field, value)); return self
    def ilike(self, field, value): self.filters.append((field, str(value).lower())); return self
    def gt(self, field, value): self.filters.append((field, ("gt", value))); return self
    def in_(self, field, values): self.filters.append((field, set(str(v) for v in values))); return self
    def insert(self, value): self.inserted = dict(value); return self
    def update(self, value): self.updated = dict(value); return self
    def upsert(self, value, **_kwargs): self.inserted = dict(value); return self

    def execute(self):
        rows = self.client.tables.setdefault(self.name, [])
        if self.inserted is not None:
            row = {"id": INVITATION_ID, **self.inserted}
            rows.append(row)
            return SimpleNamespace(data=[dict(row)])
        matches = rows
        for field, expected in self.filters:
            if isinstance(expected, set):
                matches = [row for row in matches if str(row.get(field)) in expected]
            elif isinstance(expected, tuple) and expected[0] == "gt":
                matches = [row for row in matches if str(row.get(field, "9999")) > str(expected[1])]
            else:
                matches = [row for row in matches if str(row.get(field, "")).lower() == str(expected).lower()]
        if self.updated is not None:
            for row in matches: row.update(self.updated)
        result = matches[:self.row_limit] if self.row_limit else matches
        return SimpleNamespace(data=[dict(row) for row in result])


class FakeClient:
    def __init__(self):
        self.tables = {
            "patient_invitations": [{
                "id": INVITATION_ID, "doctor_id": DOCTOR_ID, "patient_code": "P123456",
                "full_name": "Pending Patient", "gender": "female", "birth_date": "2020-01-02",
                "address": "Jakarta", "height_cm": 100, "weight_kg": 25,
                "medical_history": "Allergy", "medication_instructions": ["07:00"],
                "status": "pending", "expires_at": "2026-09-13T00:00:00+00:00", "created_at": "2026-08-13T00:00:00+00:00",
            }],
            "users": [
                {"id": PATIENT_ID, "doctor_id": DOCTOR_ID, "role": "child", "is_active": True, "full_name": "Claimed Patient", "gender": "male", "birth_date": "2019-01-02", "address": "Bogor", "patient_code": "P654321"},
                {"id": OTHER_PATIENT_ID, "doctor_id": OTHER_DOCTOR_ID, "role": "child", "is_active": True, "full_name": "Other Patient", "gender": "female", "birth_date": "2019-01-02", "address": "Depok", "patient_code": "P999999"},
            ],
            "clinical_parameters": [{"id": "clinical-1", "child_id": PATIENT_ID, "height_cm": 110, "weight_kg": 30, "medical_conditions": ["Diabetes Type I"], "recorded_at": "2026-08-13T00:00:00+00:00"}],
            "doctor_patient_profiles": [{"patient_id": PATIENT_ID, "doctor_id": DOCTOR_ID, "medical_history": "None", "medication_instructions": ["08:00"]}],
            "virtual_pets": [{"child_id": PATIENT_ID, "is_active": True, "happiness": 80, "hunger": 60, "level": 5}],
        }

    def table(self, name): return Query(self, name)


def doctor_identity():
    return {"id": DOCTOR_ID, "role": "doctor"}


def setup_client(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(doctors, "get_supabase_service_client", lambda: client)
    monkeypatch.setattr(doctors, "record_activity", lambda **_kwargs: None)
    app.dependency_overrides[require_doctor] = doctor_identity
    return client


def teardown():
    app.dependency_overrides.clear()


def test_doctor_lists_only_owned_pending_and_claimed_patients(monkeypatch):
    setup_client(monkeypatch)
    try:
        response = TestClient(app).get("/api/v1/doctors/me/patients")
    finally:
        teardown()
    assert response.status_code == 200
    assert {item["id"] for item in response.json()["items"]} == {INVITATION_ID, PATIENT_ID}


def test_doctor_reads_owned_claimed_patient_profile(monkeypatch):
    setup_client(monkeypatch)
    try:
        response = TestClient(app).get(f"/api/v1/doctors/me/patients/{PATIENT_ID}")
    finally:
        teardown()
    assert response.status_code == 200
    assert response.json()["profile"]["heightCm"] == 110.0
    assert response.json()["profile"]["medicationSchedule"] == ["08:00"]


def test_cross_doctor_patient_access_is_denied_without_disclosure(monkeypatch):
    setup_client(monkeypatch)
    try:
        response = TestClient(app).get(f"/api/v1/doctors/me/patients/{OTHER_PATIENT_ID}")
    finally:
        teardown()
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert OTHER_PATIENT_ID not in response.text


def test_doctor_creates_server_coded_pending_invitation(monkeypatch):
    client = setup_client(monkeypatch)
    monkeypatch.setattr(doctors, "_new_patient_code", lambda: "P777777")
    try:
        response = TestClient(app).post("/api/v1/doctors/me/patients", json={
            "fullName": "New Patient", "gender": "female", "birthdate": "2021-05-06",
            "address": "Jakarta", "heightCm": 90, "weightKg": 24,
            "medicalHistory": "", "medicationSchedule": [" 07:00 ", ""],
        })
    finally:
        teardown()
    assert response.status_code == 201
    assert response.json()["code"] == "P777777"
    assert client.tables["patient_invitations"][-1]["medication_instructions"] == ["07:00"]


def test_patient_patch_rejects_server_owned_fields(monkeypatch):
    setup_client(monkeypatch)
    try:
        response = TestClient(app).patch(f"/api/v1/doctors/me/patients/{PATIENT_ID}", json={"doctorId": OTHER_DOCTOR_ID})
    finally:
        teardown()
    assert response.status_code == 422
    assert "doctorId" in response.json()["details"]["fields"]


def test_doctor_updates_owned_pending_profile(monkeypatch):
    client = setup_client(monkeypatch)
    try:
        response = TestClient(app).patch(
            f"/api/v1/doctors/me/patients/{INVITATION_ID}",
            json={"fullName": "Updated Patient", "medicationSchedule": [" 08:00 "]},
        )
    finally:
        teardown()
    assert response.status_code == 200
    assert response.json()["profile"]["fullName"] == "Updated Patient"
    assert client.tables["patient_invitations"][0]["medication_instructions"] == ["08:00"]
