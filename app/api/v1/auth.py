from __future__ import annotations

import re
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ConfigDict

from app.api.deps import get_identity
from app.api.errors import api_error
from app.core.auth import security
from app.core.supabase import get_supabase_service_client
from app.models.base import CamelModel
from app.models.database import Gender, UserRole
from app.services.activity_service import record_activity

router = APIRouter()


class LoginRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = None
    doctor_code: str | None = None
    password: str
    role: UserRole


class RegisterRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = None
    password: str
    role: UserRole
    doctor_code: str | None = None
    patient_code: str | None = None
    full_name: str | None = None
    gender: Gender | None = None
    birthdate: date | None = None
    address: str | None = None


class RefreshRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class LogoutRequest(CamelModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str | None = None


_DOCTOR_CODE_PATTERN = re.compile(r"^[A-Z0-9-]{4,32}$")


def _doctor_code(value: str | None) -> str:
    return (value or "").strip().upper()


def _auth_select() -> str:
    return "id,username,email,full_name,role,doctor_code,is_active"


def _identity(user: dict[str, Any]) -> dict[str, Any]:
    role = str(user["role"])
    username = user.get("username") or str(user.get("email", "")).split("@")[0]
    return {
        "id": str(user["id"]),
        "username": username,
        "role": role,
        "parentId": str(user["id"]) if role == "parent" else None,
        "childId": str(user["id"]) if role == "child" else None,
        "doctorId": str(user["id"]) if role == "doctor" else None,
        "doctorCode": user.get("doctor_code") if role == "doctor" else None,
        "fullName": user.get("full_name") or username,
    }


def _session_payload(session: Any, user: dict[str, Any]) -> dict[str, Any]:
    if not session:
        raise api_error(401, "authentication_required", "Authentication failed.")
    return {
        "accessToken": session.access_token,
        "refreshToken": session.refresh_token,
        "user": _identity(user),
    }


@router.post("/login")
def login(req: LoginRequest, request: Request) -> dict[str, Any]:
    client = get_supabase_service_client()
    expected_user: dict[str, Any] | None = None
    if req.role == UserRole.doctor:
        code = _doctor_code(req.doctor_code)
        if not code:
            record_activity(
                actor_id=None, actor_role="doctor", action="auth.login",
                target_type="session", description="Sign-in failed.", outcome="failure",
                request_id=request.state.request_id,
            )
            raise api_error(422, "validation_error", "One or more fields are invalid.", {
                "fields": {"doctorCode": ["Required for a Doctor account."]}
            })
        rows = (
            client.table("users").select(_auth_select())
            .ilike("doctor_code", code).eq("role", "doctor").eq("is_active", True)
            .execute().data or []
        )
        if len(rows) != 1:
            record_activity(
                actor_id=None, actor_role="doctor", action="auth.login",
                target_type="session", description="Sign-in failed.", outcome="failure",
                request_id=request.state.request_id,
            )
            raise api_error(401, "invalid_credentials", "Invalid Doctor code or password.")
        expected_user = rows[0]
        email = str(expected_user["email"])
    else:
        username = (req.username or "").strip()
        if not username:
            raise api_error(422, "validation_error", "One or more fields are invalid.", {
                "fields": {"username": ["Required."]}
            })
        email = f"{username}@bitebuddy.com"
    try:
        auth_response = client.auth.sign_in_with_password(
            {"email": email, "password": req.password}
        )
    except Exception:
        if expected_user:
            record_activity(
                actor_id=str(expected_user["id"]), actor_role="doctor",
                action="auth.login", target_type="session",
                description="Sign-in failed.", outcome="failure",
                request_id=request.state.request_id,
            )
        message = "Invalid Doctor code or password." if req.role == UserRole.doctor else "Invalid username or password."
        raise api_error(401, "invalid_credentials", message)
    if not auth_response.user:
        raise api_error(401, "invalid_credentials", "Invalid username or password.")
    response = (
        client.table("users")
        .select(_auth_select())
        .eq("id", auth_response.user.id)
        .single()
        .execute()
    )
    user = response.data
    if (
        not user
        or not user.get("is_active", True)
        or user.get("role") != req.role.value
        or (expected_user and str(expected_user["id"]) != str(user["id"]))
    ):
        raise api_error(401, "invalid_credentials", "Invalid username or password.")
    record_activity(
        actor_id=str(user["id"]), actor_role=user["role"], action="auth.login",
        target_type="session", description="Signed in.", request_id=request.state.request_id
    )
    return _session_payload(auth_response.session, user)


@router.post("/register", status_code=201)
def register(req: RegisterRequest, request: Request) -> dict[str, Any]:
    doctor_code = _doctor_code(req.doctor_code)
    username = (req.username or "").strip()
    if req.role == UserRole.doctor:
        username = doctor_code.lower()
    fields: dict[str, list[str]] = {}
    if req.role != UserRole.doctor and len(username) < 3:
        fields["username"] = ["Must contain at least 3 characters."]
    if len(req.password) < 8:
        fields["password"] = ["Must contain at least 8 characters."]
    if req.role == UserRole.doctor:
        if not _DOCTOR_CODE_PATTERN.fullmatch(doctor_code):
            fields["doctorCode"] = ["Use 4-32 letters, numbers, or hyphens."]
        if not (req.full_name or "").strip():
            fields["fullName"] = ["Required for a Doctor account."]
        if req.gender is None:
            fields["gender"] = ["Required for a Doctor account."]
        if req.birthdate is None:
            fields["birthdate"] = ["Required for a Doctor account."]
        if not (req.address or "").strip():
            fields["address"] = ["Required for a Doctor account."]
    if fields:
        record_activity(
            actor_id=None, actor_role=req.role.value, action="auth.register",
            target_type="user", description="Registration failed validation.",
            outcome="failure", request_id=request.state.request_id,
            metadata={"invalid_fields": sorted(fields)},
        )
        raise api_error(422, "validation_error", "One or more fields are invalid.", {"fields": fields})

    client = get_supabase_service_client()
    doctor_id: str | None = None
    if req.role == UserRole.child:
        if not req.doctor_code or not req.patient_code:
            raise api_error(422, "validation_error", "One or more fields are invalid.", {
                "fields": {
                    **({"doctorCode": ["Required for a Child account."]} if not req.doctor_code else {}),
                    **({"patientCode": ["Required for a Child account."]} if not req.patient_code else {}),
                }
            })
        doctor = client.table("users").select("id").ilike("doctor_code", doctor_code).eq("role", "doctor").eq("is_active", True).execute()
        if not doctor.data:
            raise api_error(400, "invalid_doctor_code", "Doctor code is invalid.", {"fields": {"doctorCode": ["Invalid or inactive code."]}})
        doctor_id = str(doctor.data[0]["id"])
        existing_code = client.table("users").select("id").eq("patient_code", req.patient_code).execute()
        if existing_code.data:
            raise api_error(409, "patient_code_conflict", "Patient code is already registered.")
    elif req.role == UserRole.doctor:
        duplicate = client.table("users").select("id").ilike("doctor_code", doctor_code).execute()
        if duplicate.data:
            raise api_error(409, "doctor_code_conflict", "Doctor code is already registered.", {
                "fields": {"doctorCode": ["Already in use."]}
            })

    created_user_id: str | None = None
    try:
        auth_response = client.auth.admin.create_user({
            "email": f"{username}@bitebuddy.com",
            "password": req.password,
            "email_confirm": True,
            "user_metadata": {"username": username, "role": req.role.value},
        })
        created_user_id = str(auth_response.user.id)
        user_data = {
            "id": created_user_id,
            "email": f"{username}@bitebuddy.com",
            "username": username,
            "full_name": (req.full_name or username).strip(),
            "role": req.role.value,
            "doctor_id": doctor_id,
            "doctor_code": doctor_code if req.role == UserRole.doctor else None,
            "patient_code": req.patient_code if req.role == UserRole.child else None,
            "birth_date": req.birthdate.isoformat() if req.birthdate else None,
            "gender": req.gender.value if req.gender else None,
            "address": (req.address or "").strip() or None,
            "is_active": True,
            "password_hash": "supabase_managed",
        }
        inserted = client.table("users").insert(user_data).execute()
        if not inserted.data:
            raise RuntimeError("Profile insert failed")
        if req.role == UserRole.child:
            client.table("virtual_pets").insert({
                "child_id": created_user_id, "pet_name": "Buddy", "pet_type": "dog"
            }).execute()
    except Exception:
        if created_user_id:
            try:
                client.auth.admin.delete_user(created_user_id)
            except Exception:
                pass
        record_activity(
            actor_id=None, actor_role=req.role.value, action="auth.register",
            target_type="user", description="Registration failed.", outcome="failure",
            request_id=request.state.request_id,
        )
        raise api_error(409, "registration_failed", "The account could not be registered.")

    record_activity(
        actor_id=created_user_id, actor_role=req.role.value, action="auth.register",
        target_type="user", target_id=created_user_id, child_id=created_user_id if req.role == UserRole.child else None,
        description="Registered account.", request_id=request.state.request_id
    )
    return {
        "userId": created_user_id,
        "parentId": created_user_id if req.role == UserRole.parent else None,
        "childId": created_user_id if req.role == UserRole.child else None,
        "doctorId": created_user_id if req.role == UserRole.doctor else None,
        "doctorCode": doctor_code if req.role == UserRole.doctor else None,
        "role": req.role.value,
        "requiresLogin": True,
    }


@router.post("/refresh")
def refresh(req: RefreshRequest, request: Request) -> dict[str, Any]:
    client = get_supabase_service_client()
    try:
        auth_response = client.auth.refresh_session(req.refresh_token)
        response = client.table("users").select(_auth_select()).eq("id", auth_response.user.id).single().execute()
    except Exception:
        raise api_error(401, "refresh_failed", "The session could not be refreshed.")
    user = response.data
    if not user or not user.get("is_active", True):
        raise api_error(401, "refresh_failed", "The session could not be refreshed.")
    record_activity(
        actor_id=str(user["id"]), actor_role=user["role"], action="auth.refresh",
        target_type="session", description="Session refreshed.",
        request_id=request.state.request_id,
    )
    return _session_payload(auth_response.session, user)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    identity: dict[str, Any] = Depends(get_identity),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    req: LogoutRequest | None = None,
) -> None:
    client = get_supabase_service_client()
    try:
        client.auth.admin.sign_out(credentials.credentials, scope="local")
    except Exception:
        raise api_error(503, "logout_failed", "The session could not be ended.")
    record_activity(
        actor_id=identity["id"], actor_role=identity["role"], action="auth.logout",
        target_type="session", description="Signed out.", request_id=request.state.request_id,
        metadata={"refresh_token_submitted": bool(req and req.refresh_token)},
    )


@router.get("/me")
def get_me(request: Request, identity: dict[str, Any] = Depends(get_identity)) -> dict[str, Any]:
    record_activity(
        actor_id=identity["id"], actor_role=identity["role"], action="auth.me",
        target_type="user", target_id=identity["id"], description="Restored identity.",
        request_id=request.state.request_id,
    )
    return {"user": _identity(identity)}
