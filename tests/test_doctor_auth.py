from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.deps import get_identity, require_doctor
from app.api.v1 import auth as auth_api
from app.main import app


DOCTOR_ID = "00000000-0000-0000-0000-000000000010"


class FakeUsersQuery:
    def __init__(self, client: "FakeClient"):
        self.client = client
        self.filters: dict[str, object] = {}
        self.inserted: dict[str, object] | None = None

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters[field] = value
        return self

    def ilike(self, field, value):
        self.filters[field] = str(value).lower()
        return self

    def single(self):
        return self

    def insert(self, value):
        self.inserted = value
        return self

    def execute(self):
        if self.inserted is not None:
            self.client.users.append(dict(self.inserted))
            return SimpleNamespace(data=[dict(self.inserted)])
        matches = self.client.users
        for field, expected in self.filters.items():
            matches = [
                user for user in matches
                if str(user.get(field, "")).lower() == str(expected).lower()
            ]
        if "id" in self.filters:
            return SimpleNamespace(data=matches[0] if matches else None)
        return SimpleNamespace(data=[dict(user) for user in matches])


class FakeAdmin:
    def create_user(self, _payload):
        return SimpleNamespace(user=SimpleNamespace(id=DOCTOR_ID))

    def delete_user(self, _user_id):
        return None


class FakeAuth:
    def __init__(self, client: "FakeClient"):
        self.client = client
        self.admin = FakeAdmin()

    def sign_in_with_password(self, credentials):
        user = next(user for user in self.client.users if user["email"] == credentials["email"])
        return SimpleNamespace(
            user=SimpleNamespace(id=user["id"]),
            session=SimpleNamespace(access_token="access", refresh_token="refresh"),
        )


class FakeClient:
    def __init__(self, users=None):
        self.users = list(users or [])
        self.auth = FakeAuth(self)

    def table(self, name):
        assert name == "users"
        return FakeUsersQuery(self)


def doctor_user():
    return {
        "id": DOCTOR_ID,
        "username": "d0987",
        "email": "d0987@bitebuddy.com",
        "full_name": "Dr. Bite Buddy",
        "role": "doctor",
        "doctor_code": "D0987",
        "is_active": True,
    }


def test_doctor_login_returns_canonical_identity(monkeypatch):
    client = FakeClient([doctor_user()])
    monkeypatch.setattr(auth_api, "get_supabase_service_client", lambda: client)
    monkeypatch.setattr(auth_api, "record_activity", lambda **_kwargs: None)

    response = TestClient(app).post("/api/v1/auth/login", json={
        "doctorCode": "d0987",
        "password": "doctor123",
        "role": "doctor",
    })

    assert response.status_code == 200
    assert response.json() == {
        "accessToken": "access",
        "refreshToken": "refresh",
        "user": {
            "id": DOCTOR_ID,
            "username": "d0987",
            "role": "doctor",
            "parentId": None,
            "childId": None,
            "doctorId": DOCTOR_ID,
            "doctorCode": "D0987",
            "fullName": "Dr. Bite Buddy",
        },
    }


def test_login_role_must_match_persisted_role(monkeypatch):
    client = FakeClient([doctor_user()])
    monkeypatch.setattr(auth_api, "get_supabase_service_client", lambda: client)

    response = TestClient(app).post("/api/v1/auth/login", json={
        "username": "d0987",
        "password": "doctor123",
        "role": "parent",
    })

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_doctor_registration_persists_profile(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(auth_api, "get_supabase_service_client", lambda: client)
    monkeypatch.setattr(auth_api, "record_activity", lambda **_kwargs: None)

    response = TestClient(app).post("/api/v1/auth/register", json={
        "role": "doctor",
        "fullName": "Dr. Bite Buddy",
        "gender": "female",
        "birthdate": "1990-08-13",
        "address": "Jakarta",
        "doctorCode": "d0987",
        "password": "doctor123",
    })

    assert response.status_code == 201
    assert response.json()["doctorId"] == DOCTOR_ID
    assert response.json()["doctorCode"] == "D0987"
    assert client.users[0]["doctor_code"] == "D0987"
    assert client.users[0]["birth_date"] == "1990-08-13"
    assert client.users[0]["address"] == "Jakarta"


def test_doctor_registration_requires_profile_fields():
    response = TestClient(app).post("/api/v1/auth/register", json={
        "role": "doctor",
        "doctorCode": "D0987",
        "password": "doctor123",
    })

    assert response.status_code == 422
    assert set(response.json()["details"]["fields"]) == {"fullName", "gender", "birthdate", "address"}


def test_auth_me_returns_doctor_identity():
    app.dependency_overrides[get_identity] = doctor_user
    try:
        response = TestClient(app).get("/api/v1/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["user"]["doctorId"] == DOCTOR_ID
    assert response.json()["user"]["doctorCode"] == "D0987"


def test_require_doctor_rejects_non_doctor():
    try:
        require_doctor({"id": DOCTOR_ID, "role": "parent"})
    except Exception as error:
        assert error.status_code == 403
    else:
        raise AssertionError("Parent identity must not pass require_doctor.")
