"""Live BiteBuddy E2E against configured Supabase and Gemini services.

The scenario uses the FastAPI ASGI application as its transport boundary, creates
unique accounts, verifies cross-role journeys, and removes only records created by
this run unless ``--keep-data`` is supplied.
"""

from __future__ import annotations

import argparse
import sys
import time
from contextlib import ExitStack
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.supabase import get_supabase_service_client  # noqa: E402
from app.main import app  # noqa: E402


class LiveE2EFailure(RuntimeError):
    pass


class Scenario:
    def __init__(self, client: TestClient, *, keep_data: bool) -> None:
        self.client = client
        self.keep_data = keep_data
        self.user_ids: list[str] = []
        self.storage_objects: list[tuple[str, str]] = []
        self.tokens: dict[str, str] = {}
        self.refresh_tokens: dict[str, str] = {}
        self.results: list[tuple[str, float]] = []

    def step(self, name: str, operation: Callable[[], Any]) -> Any:
        started = time.perf_counter()
        try:
            value = operation()
        except Exception as exc:
            raise LiveE2EFailure(f"{name}: {exc}") from exc
        elapsed = time.perf_counter() - started
        self.results.append((name, elapsed))
        print(f"PASS {name} ({elapsed:.2f}s)")
        return value

    @staticmethod
    def expect(response: Any, status: int, *, code: str | None = None) -> dict[str, Any]:
        if response.status_code != status:
            try:
                detail = response.json()
            except Exception:
                detail = response.text[:500]
            raise AssertionError(f"expected HTTP {status}, got {response.status_code}: {detail}")
        if status == 204:
            return {}
        payload = response.json()
        if code is not None and payload.get("code") != code:
            raise AssertionError(f"expected error code {code}, got {payload.get('code')}")
        return payload

    def headers(self, role: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.tokens[role]}"}

    def register(self, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = self.expect(self.client.post("/api/v1/auth/register", json=payload), 201)
        user_id = str(body["userId"])
        self.user_ids.append(user_id)
        return body

    def login(
        self, role: str, payload: dict[str, Any], *, expected_role: str | None = None,
    ) -> dict[str, Any]:
        body = self.expect(self.client.post("/api/v1/auth/login", json=payload), 200)
        if body["user"]["role"] != (expected_role or role):
            raise AssertionError("login returned a non-canonical role")
        self.tokens[role] = body["accessToken"]
        self.refresh_tokens[role] = body["refreshToken"]
        return body

    def remember_storage_url(self, bucket: str, public_url: str | None) -> None:
        if not public_url:
            return
        filename = unquote(Path(urlparse(public_url).path).name)
        if filename:
            self.storage_objects.append((bucket, filename))

    def cleanup(self) -> None:
        if self.keep_data:
            print("KEEP test data retained by request")
            return
        supabase = get_supabase_service_client()
        for bucket, path in reversed(self.storage_objects):
            try:
                supabase.storage.from_(bucket).remove([path])
            except Exception:
                pass
        for user_id in reversed(self.user_ids):
            try:
                supabase.table("users").delete().eq("id", user_id).execute()
            except Exception:
                pass
            try:
                supabase.auth.admin.delete_user(user_id)
            except Exception:
                pass


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live BiteBuddy cross-app E2E.")
    parser.add_argument(
        "--food-image", type=Path, default=WORKSPACE_ROOT / "spageti.jpg",
    )
    parser.add_argument(
        "--medicine-image", type=Path,
        default=WORKSPACE_ROOT / "BiteBuddy/bite_buddy/assets/images/pills_placeholder.png",
    )
    parser.add_argument("--keep-data", action="store_true")
    return parser.parse_args()


def _require_configuration(args: argparse.Namespace) -> None:
    missing = [
        name for name, value in {
            "SUPABASE_URL": settings.supabase_url,
            "SUPABASE_ANON_KEY": settings.supabase_anon_key,
            "SUPABASE_SERVICE_ROLE_KEY": settings.supabase_service_role_key,
            "GEMINI_API_KEY": settings.gemini_api_key,
        }.items() if not value
    ]
    if missing:
        raise LiveE2EFailure(f"missing configuration: {', '.join(missing)}")
    for image in (args.food_image, args.medicine_image):
        if not image.is_file():
            raise LiveE2EFailure(f"image fixture does not exist: {image}")


def run(args: argparse.Namespace) -> int:
    _require_configuration(args)
    now_wib = datetime.now(ZoneInfo("Asia/Jakarta"))
    suffix = f"{now_wib:%m%d%H%M%S}{uuid4().hex[:5]}"
    password = f"Bb-E2E-{suffix}!"
    doctor_code = f"E2E-{suffix}".upper()
    outsider_code = f"ISO-{suffix}".upper()
    child_username = f"e2ec{suffix}".lower()
    parent_username = f"e2ep{suffix}".lower()
    outsider_parent_username = f"e2ex{suffix}".lower()

    with TestClient(app) as client:
        scenario = Scenario(client, keep_data=args.keep_data)
        try:
            scenario.step("auth: register Doctor", lambda: scenario.register("doctor", {
                "role": "doctor", "doctorCode": doctor_code, "password": password,
                "fullName": "Doctor Live E2E", "gender": "male",
                "birthdate": "1985-01-15", "address": "Jakarta",
            }))
            doctor = scenario.step("auth: Doctor login", lambda: scenario.login("doctor", {
                "role": "doctor", "doctorCode": doctor_code, "password": password,
            }))
            doctor_id = str(doctor["user"]["doctorId"])
            scenario.step("auth: Doctor /me restore", lambda: Scenario.expect(
                client.get("/api/v1/auth/me", headers=scenario.headers("doctor")), 200,
            ))

            invitation = scenario.step("Doctor: create patient invitation", lambda: Scenario.expect(
                client.post("/api/v1/doctors/me/patients", headers=scenario.headers("doctor"), json={
                    "fullName": "Child Live E2E", "gender": "female",
                    "birthdate": "2014-05-20", "address": "Jakarta",
                    "heightCm": 145, "weightKg": 42,
                    "medicalHistory": "Type 1 diabetes",
                    "medicationSchedule": ["Insulin after breakfast"],
                }), 201,
            ))
            invitation_id = str(invitation["id"])
            patient_code = str(invitation["code"])

            child_registration = scenario.step("auth: Child claims Doctor invitation", lambda: scenario.register("child", {
                "role": "child", "username": child_username, "password": password,
                "doctorCode": doctor_code, "patientCode": patient_code,
            }))
            child_id = str(child_registration["childId"])
            scenario.step("auth: Child login", lambda: scenario.login("child", {
                "role": "child", "username": child_username, "password": password,
            }))

            scenario.step("auth: register Parent", lambda: scenario.register("parent", {
                "role": "parent", "username": parent_username, "password": password,
            }))
            scenario.step("auth: Parent login", lambda: scenario.login("parent", {
                "role": "parent", "username": parent_username, "password": password,
            }))
            scenario.step("Parent: link Child", lambda: Scenario.expect(
                client.post("/api/v1/parents/me/children/link", headers=scenario.headers("parent"), json={
                    "childCode": patient_code,
                }), 201,
            ))

            scenario.step("auth: register isolation Doctor", lambda: scenario.register("doctor_iso", {
                "role": "doctor", "doctorCode": outsider_code, "password": password,
                "fullName": "Doctor Isolation E2E", "gender": "female",
                "birthdate": "1987-02-20", "address": "Bandung",
            }))
            scenario.step("auth: isolation Doctor login", lambda: scenario.login("doctor_iso", {
                "role": "doctor", "doctorCode": outsider_code, "password": password,
            }, expected_role="doctor"))
            scenario.step("auth: register isolation Parent", lambda: scenario.register("parent_iso", {
                "role": "parent", "username": outsider_parent_username, "password": password,
            }))
            scenario.step("auth: isolation Parent login", lambda: scenario.login("parent_iso", {
                "role": "parent", "username": outsider_parent_username, "password": password,
            }, expected_role="parent"))

            scenario.step("roles: Child rejected by Doctor API", lambda: Scenario.expect(
                client.get("/api/v1/doctors/me/patients", headers=scenario.headers("child")), 403, code="forbidden",
            ))
            scenario.step("roles: Parent rejected by Child API", lambda: Scenario.expect(
                client.get("/api/v1/children/me/profile", headers=scenario.headers("parent")), 403, code="forbidden",
            ))
            scenario.step("roles: other Doctor cannot read patient", lambda: Scenario.expect(
                client.get(f"/api/v1/doctors/me/patients/{child_id}", headers=scenario.headers("doctor_iso")),
                403, code="forbidden",
            ))
            scenario.step("roles: other Parent cannot read Child", lambda: Scenario.expect(
                client.get(f"/api/v1/parents/me/children/{child_id}", headers=scenario.headers("parent_iso")),
                403, code="forbidden",
            ))

            scenario.step("Doctor: claimed patient list", lambda: _assert_patient_list(
                Scenario.expect(client.get("/api/v1/doctors/me/patients", headers=scenario.headers("doctor")), 200),
                child_id,
            ))
            scenario.step("Doctor: read claimed patient", lambda: Scenario.expect(
                client.get(f"/api/v1/doctors/me/patients/{child_id}", headers=scenario.headers("doctor")), 200,
            ))
            scenario.step("Doctor: update patient", lambda: Scenario.expect(
                client.patch(f"/api/v1/doctors/me/patients/{child_id}", headers=scenario.headers("doctor"), json={
                    "heightCm": 146, "weightKg": 43,
                }), 200,
            ))
            recorded_at = now_wib.isoformat()
            scenario.step("Doctor: create glucose", lambda: Scenario.expect(
                client.post(f"/api/v1/doctors/me/patients/{child_id}/blood-glucose", headers=scenario.headers("doctor"), json={
                    "valueMgDl": 132, "recordedAt": recorded_at,
                }), 201,
            ))
            scenario.step("Doctor: read glucose", lambda: Scenario.expect(
                client.get(f"/api/v1/doctors/me/patients/{child_id}/blood-glucose", headers=scenario.headers("doctor")), 200,
            ))
            scenario.step("Doctor: read nutrition", lambda: Scenario.expect(
                client.get(f"/api/v1/doctors/me/patients/{child_id}/nutrition?days=7&timezone=Asia%2FJakarta", headers=scenario.headers("doctor")), 200,
            ))
            scenario.step("Doctor: read adherence", lambda: Scenario.expect(
                client.get(f"/api/v1/doctors/me/patients/{child_id}/medication-adherence?days=30&timezone=Asia%2FJakarta", headers=scenario.headers("doctor")), 200,
            ))
            appointment_at = (now_wib + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
            scenario.step("Doctor: create appointment", lambda: Scenario.expect(
                client.post(f"/api/v1/doctors/me/patients/{child_id}/appointments", headers=scenario.headers("doctor"), json={
                    "title": "E2E consultation", "startsAt": appointment_at.isoformat(),
                }), 201,
            ))
            scenario.step("Doctor: read appointments", lambda: Scenario.expect(
                client.get(f"/api/v1/doctors/me/patients/{child_id}/appointments", headers=scenario.headers("doctor")), 200,
            ))
            scenario.step("Doctor: create diagnosis", lambda: Scenario.expect(
                client.post(f"/api/v1/doctors/me/patients/{child_id}/diagnoses", headers=scenario.headers("doctor"), json={
                    "chiefComplaint": "Routine E2E check", "medicalDiagnosis": "Stable",
                    "therapy": "Continue treatment", "priceAmount": 0, "currency": "IDR",
                }), 201,
            ))

            patient_notification = scenario.step("Doctor to Child: send notification", lambda: Scenario.expect(
                client.post(f"/api/v1/doctors/me/patients/{child_id}/notifications", headers={
                    **scenario.headers("doctor"), "Idempotency-Key": f"patient-{suffix}",
                }, json={"recipient": "patient", "type": "reduce_sugar"}), 201,
            ))
            child_notifications = scenario.step("Doctor to Child: visible in mobile inbox", lambda: Scenario.expect(
                client.get("/api/v1/children/me/notifications", headers=scenario.headers("child")), 200,
            ))
            child_alert = _find_notification(child_notifications, patient_notification["title"])
            scenario.step("Child: mark Doctor notification read", lambda: Scenario.expect(
                client.patch(f"/api/v1/children/me/notifications/{child_alert['id']}/read", headers=scenario.headers("child")), 200,
            ))

            parent_notification = scenario.step("Doctor to Parent: send notification", lambda: Scenario.expect(
                client.post(f"/api/v1/doctors/me/patients/{child_id}/notifications", headers={
                    **scenario.headers("doctor"), "Idempotency-Key": f"parent-{suffix}",
                }, json={"recipient": "parent", "type": "appointment_reminder"}), 201,
            ))
            parent_notifications = scenario.step("Doctor to Parent: visible in mobile inbox", lambda: Scenario.expect(
                client.get(f"/api/v1/parents/me/children/{child_id}/notifications", headers=scenario.headers("parent")), 200,
            ))
            _find_notification(parent_notifications, parent_notification["title"])

            schedule = scenario.step("Parent: create schedule", lambda: Scenario.expect(
                client.post(f"/api/v1/parents/me/children/{child_id}/schedules", headers=scenario.headers("parent"), json={
                    "title": "E2E breakfast", "startTime": "07:00", "endTime": "08:00",
                }), 201,
            ))
            schedule_id = str(schedule["id"])
            scenario.step("Parent: update schedule", lambda: Scenario.expect(
                client.patch(f"/api/v1/parents/me/children/{child_id}/schedules/{schedule_id}", headers=scenario.headers("parent"), json={
                    "title": "E2E healthy breakfast", "startTime": "07:15", "endTime": "08:15",
                }), 200,
            ))
            scenario.step("Parent: read schedules", lambda: Scenario.expect(
                client.get(f"/api/v1/parents/me/children/{child_id}/schedules", headers=scenario.headers("parent")), 200,
            ))
            reminder = scenario.step("Parent to Child: create reminder", lambda: Scenario.expect(
                client.post(f"/api/v1/parents/me/children/{child_id}/reminders", headers=scenario.headers("parent"), json={
                    "reminderType": "eat",
                }), 201,
            ))
            child_notifications = scenario.step("Parent to Child: reminder visible", lambda: Scenario.expect(
                client.get("/api/v1/children/me/notifications", headers=scenario.headers("child")), 200,
            ))
            _assert_item(child_notifications, reminder["notification"]["id"])

            with ExitStack() as stack:
                food_file = stack.enter_context(args.food_image.open("rb"))
                food_analysis = scenario.step("Child: live food scan", lambda: Scenario.expect(
                    client.post("/api/v1/children/me/food-analyses", headers=scenario.headers("child"), files={
                        "file": (args.food_image.name, food_file, "image/jpeg"),
                    }), 201,
                ))
            scenario.remember_storage_url("food-photos", food_analysis.get("imageUrl"))
            food_confirmation = scenario.step("Child: atomic food confirmation", lambda: Scenario.expect(
                client.post(f"/api/v1/children/me/food-analyses/{food_analysis['analysisId']}/confirm", headers=scenario.headers("child"), json={
                    "portionGrams": food_analysis.get("portionGrams") or 100,
                }), 200,
            ))
            food_history_id = str(food_confirmation["history"]["id"])
            scenario.step("Child: food history persisted", lambda: _assert_item(
                Scenario.expect(client.get("/api/v1/children/me/history?type=food", headers=scenario.headers("child")), 200),
                food_history_id,
            ))
            scenario.step("Parent: food history detail visible", lambda: Scenario.expect(
                client.get(f"/api/v1/parents/me/children/{child_id}/history/{food_history_id}", headers=scenario.headers("parent")), 200,
            ))

            with ExitStack() as stack:
                medicine_file = stack.enter_context(args.medicine_image.open("rb"))
                medicine_analysis = scenario.step("Child: live medicine scan", lambda: Scenario.expect(
                    client.post("/api/v1/children/me/medicine-analyses", headers=scenario.headers("child"), files={
                        "file": (args.medicine_image.name, medicine_file, "image/png"),
                    }), 201,
                ))
            scenario.remember_storage_url("medicine-photos", medicine_analysis.get("imageUrl"))
            if not medicine_analysis.get("isMedicine"):
                raise LiveE2EFailure("medicine fixture was not recognized as medicine by the live provider")
            medicine_confirmation = scenario.step("Child: atomic medicine confirmation", lambda: Scenario.expect(
                client.post(f"/api/v1/children/me/medicine-analyses/{medicine_analysis['analysisId']}/confirm", headers=scenario.headers("child")), 200,
            ))
            medicine_history_id = str(medicine_confirmation["history"]["id"])
            scenario.step("Parent: medicine history visible", lambda: _assert_item(
                Scenario.expect(client.get(f"/api/v1/parents/me/children/{child_id}/history?type=medicine", headers=scenario.headers("parent")), 200),
                medicine_history_id,
            ))

            ai_summary = scenario.step("Doctor: live AI summary", lambda: Scenario.expect(
                client.get(f"/api/v1/doctors/me/patients/{child_id}/ai-summary", headers=scenario.headers("doctor")), 200,
            ))
            if not ai_summary.get("overview") or not ai_summary.get("insights"):
                raise LiveE2EFailure("Doctor AI summary was empty")

            scenario.step("Parent: delete schedule", lambda: Scenario.expect(
                client.delete(f"/api/v1/parents/me/children/{child_id}/schedules/{schedule_id}", headers=scenario.headers("parent")), 204,
            ))
            scenario.step("audit: Doctor monthly WIB log", lambda: _assert_actions(
                Scenario.expect(client.get(
                    f"/api/v1/activity-logs?month={now_wib:%Y-%m}&timezone=Asia%2FJakarta&limit=100",
                    headers=scenario.headers("doctor"),
                ), 200),
                {"auth.login", "doctor.patient.create", "notification.create", "ai_summary.generate"},
            ))
            scenario.step("audit: Parent monthly WIB log", lambda: _assert_actions(
                Scenario.expect(client.get(
                    f"/api/v1/activity-logs?month={now_wib:%Y-%m}&timezone=Asia%2FJakarta&limit=100",
                    headers=scenario.headers("parent"),
                ), 200),
                {"auth.login", "child.link", "schedule.create", "schedule.update", "schedule.delete"},
            ))

            refreshed = scenario.step("auth: refresh Child session", lambda: Scenario.expect(
                client.post("/api/v1/auth/refresh", json={"refreshToken": scenario.refresh_tokens["child"]}), 200,
            ))
            scenario.tokens["child"] = refreshed["accessToken"]
            for role in ("child", "parent", "parent_iso", "doctor_iso", "doctor"):
                scenario.step(f"auth: logout {role}", lambda role=role: Scenario.expect(
                    client.post("/api/v1/auth/logout", headers=scenario.headers(role), json={
                        "refreshToken": scenario.refresh_tokens[role],
                    }), 204,
                ))

            print(f"PASS live E2E complete: {len(scenario.results)} checks")
            print(f"RUN_ID {suffix}")
            print(f"DOCTOR_ID {doctor_id}")
            print(f"CHILD_ID {child_id}")
            print(f"INVITATION_ID {invitation_id}")
            return 0
        finally:
            scenario.cleanup()


def _assert_item(payload: dict[str, Any], item_id: str) -> dict[str, Any]:
    if not any(str(item.get("id")) == str(item_id) for item in payload.get("items", [])):
        raise AssertionError(f"item {item_id} was not present")
    return payload


def _assert_patient_list(payload: dict[str, Any], child_id: str) -> dict[str, Any]:
    return _assert_item(payload, child_id)


def _find_notification(payload: dict[str, Any], title: str) -> dict[str, Any]:
    for item in payload.get("items", []):
        if item.get("title") == title and item.get("senderType") == "doctor":
            return item
    raise AssertionError(f"Doctor notification {title!r} was not present")


def _assert_actions(payload: dict[str, Any], expected: set[str]) -> dict[str, Any]:
    actions = {str(item.get("actionType")) for item in payload.get("items", [])}
    missing = expected - actions
    if missing:
        raise AssertionError(f"monthly activity log is missing actions: {sorted(missing)}")
    return payload


if __name__ == "__main__":
    try:
        raise SystemExit(run(_arguments()))
    except LiveE2EFailure as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
