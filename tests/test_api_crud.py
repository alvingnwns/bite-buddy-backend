from fastapi.testclient import TestClient

from app.api.deps import get_identity
from app.main import app


REQUIRED = {
    ("post", "/api/v1/auth/login"),
    ("post", "/api/v1/auth/register"),
    ("post", "/api/v1/auth/refresh"),
    ("post", "/api/v1/auth/logout"),
    ("get", "/api/v1/auth/me"),
    ("get", "/api/v1/children/me/profile"),
    ("patch", "/api/v1/children/me/profile"),
    ("get", "/api/v1/children/me/dashboard"),
    ("get", "/api/v1/children/me/schedules"),
    ("post", "/api/v1/children/me/food-analyses"),
    ("post", "/api/v1/children/me/food-analyses/{analysis_id}/confirm"),
    ("post", "/api/v1/children/me/medicine-analyses"),
    ("post", "/api/v1/children/me/medicine-analyses/{analysis_id}/confirm"),
    ("get", "/api/v1/children/me/history"),
    ("get", "/api/v1/children/me/history/{history_id}"),
    ("get", "/api/v1/children/me/notifications"),
    ("patch", "/api/v1/children/me/notifications/{notification_id}/read"),
    ("get", "/api/v1/parents/me/children"),
    ("post", "/api/v1/parents/me/children/link"),
    ("get", "/api/v1/parents/me/children/{child_id}"),
    ("get", "/api/v1/parents/me/children/{child_id}/dashboard"),
    ("get", "/api/v1/parents/me/children/{child_id}/schedules"),
    ("post", "/api/v1/parents/me/children/{child_id}/schedules"),
    ("patch", "/api/v1/parents/me/children/{child_id}/schedules/{schedule_id}"),
    ("delete", "/api/v1/parents/me/children/{child_id}/schedules/{schedule_id}"),
    ("get", "/api/v1/parents/me/children/{child_id}/history"),
    ("get", "/api/v1/parents/me/children/{child_id}/history/{history_id}"),
    ("get", "/api/v1/parents/me/children/{child_id}/notifications"),
    ("post", "/api/v1/parents/me/children/{child_id}/reminders"),
    ("get", "/api/v1/activity-logs"),
}


def test_required_non_doctor_contract_is_in_openapi():
    paths = app.openapi()["paths"]
    actual = {(method, path) for path, operations in paths.items() for method in operations}
    assert REQUIRED <= actual


def test_legacy_resource_routes_are_not_exposed():
    paths = app.openapi()["paths"]
    assert not any(path.startswith("/api/v1/schedules/") for path in paths)
    assert not any(path.startswith("/api/v1/users/") for path in paths)
    assert not any(path.startswith("/api/v1/scan/") for path in paths)


def test_child_cannot_access_parent_endpoint():
    app.dependency_overrides[get_identity] = lambda: {
        "id": "00000000-0000-0000-0000-000000000001",
        "role": "child",
        "is_active": True,
    }
    try:
        response = TestClient(app).get("/api/v1/parents/me/children")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_parent_cannot_access_child_endpoint():
    app.dependency_overrides[get_identity] = lambda: {
        "id": "00000000-0000-0000-0000-000000000002",
        "role": "parent",
        "is_active": True,
    }
    try:
        response = TestClient(app).get("/api/v1/children/me/dashboard")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_validation_errors_use_contract_envelope():
    response = TestClient(app).post("/api/v1/auth/login", json={})
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message", "details", "requestId"}
