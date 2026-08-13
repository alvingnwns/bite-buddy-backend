from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_identity
from app.api.errors import api_error
from app.core.supabase import get_supabase_service_client
from app.models.base import CamelModel
from app.models.database import UserRole
from app.services.activity_service import record_activity

router = APIRouter()


class LoginRequest(CamelModel):
    username: str
    password: str
    role: UserRole


class RegisterRequest(CamelModel):
    username: str
    password: str
    role: UserRole
    doctor_code: str | None = None
    patient_code: str | None = None


class RefreshRequest(CamelModel):
    refresh_token: str


class LogoutRequest(CamelModel):
    refresh_token: str | None = None


def _identity(user: dict[str, Any]) -> dict[str, Any]:
    role = str(user["role"])
    username = user.get("username") or str(user.get("email", "")).split("@")[0]
    return {
        "id": str(user["id"]),
        "username": username,
        "role": role,
        "parentId": str(user["id"]) if role == "parent" else None,
        "childId": str(user["id"]) if role == "child" else None,
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
def login(req: LoginRequest) -> dict[str, Any]:
    client = get_supabase_service_client()
    username = req.username.strip()
    try:
        auth_response = client.auth.sign_in_with_password(
            {"email": f"{username}@bitebuddy.com", "password": req.password}
        )
    except Exception:
        raise api_error(401, "invalid_credentials", "Invalid username or password.")
    if not auth_response.user:
        raise api_error(401, "invalid_credentials", "Invalid username or password.")
    response = (
        client.table("users")
        .select("id,username,email,role,is_active")
        .eq("id", auth_response.user.id)
        .single()
        .execute()
    )
    user = response.data
    if not user or not user.get("is_active", True):
        raise api_error(401, "invalid_credentials", "Invalid username or password.")
    record_activity(
        actor_id=str(user["id"]), actor_role=user["role"], action="auth.login",
        target_type="session", description="Signed in."
    )
    return _session_payload(auth_response.session, user)


@router.post("/register", status_code=201)
def register(req: RegisterRequest) -> dict[str, Any]:
    client = get_supabase_service_client()
    username = req.username.strip()
    if len(username) < 3 or len(req.password) < 8:
        raise api_error(422, "validation_error", "One or more fields are invalid.", {
            "fields": {
                **({"username": ["Must contain at least 3 characters."]} if len(username) < 3 else {}),
                **({"password": ["Must contain at least 8 characters."]} if len(req.password) < 8 else {}),
            }
        })
    doctor_id: str | None = None
    if req.role == UserRole.child:
        if not req.doctor_code or not req.patient_code:
            raise api_error(422, "validation_error", "One or more fields are invalid.", {
                "fields": {
                    **({"doctorCode": ["Required for a Child account."]} if not req.doctor_code else {}),
                    **({"patientCode": ["Required for a Child account."]} if not req.patient_code else {}),
                }
            })
        doctor = client.table("users").select("id").eq("doctor_code", req.doctor_code).eq("role", "doctor").eq("is_active", True).execute()
        if not doctor.data:
            raise api_error(400, "invalid_doctor_code", "Doctor code is invalid.", {"fields": {"doctorCode": ["Invalid or inactive code."]}})
        doctor_id = str(doctor.data[0]["id"])
        existing_code = client.table("users").select("id").eq("patient_code", req.patient_code).execute()
        if existing_code.data:
            raise api_error(409, "patient_code_conflict", "Patient code is already registered.")

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
            "full_name": username,
            "role": req.role.value,
            "doctor_id": doctor_id,
            "patient_code": req.patient_code if req.role == UserRole.child else None,
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
        raise api_error(409, "registration_failed", "The account could not be registered.")

    record_activity(
        actor_id=created_user_id, actor_role=req.role.value, action="auth.register",
        target_type="user", target_id=created_user_id, child_id=created_user_id if req.role == UserRole.child else None,
        description="Registered account."
    )
    return {
        "userId": created_user_id,
        "parentId": created_user_id if req.role == UserRole.parent else None,
        "childId": created_user_id if req.role == UserRole.child else None,
        "role": req.role.value,
        "requiresLogin": True,
    }


@router.post("/refresh")
def refresh(req: RefreshRequest) -> dict[str, Any]:
    client = get_supabase_service_client()
    try:
        auth_response = client.auth.refresh_session(req.refresh_token)
        response = client.table("users").select("id,username,email,role,is_active").eq("id", auth_response.user.id).single().execute()
    except Exception:
        raise api_error(401, "refresh_failed", "The session could not be refreshed.")
    if not response.data:
        raise api_error(401, "refresh_failed", "The session could not be refreshed.")
    return _session_payload(auth_response.session, response.data)


@router.post("/logout", status_code=204)
def logout(req: LogoutRequest, identity: dict[str, Any] = Depends(get_identity)) -> None:
    client = get_supabase_service_client()
    if req.refresh_token:
        try:
            client.auth.refresh_session(req.refresh_token)
            client.auth.sign_out()
        except Exception:
            pass
    record_activity(
        actor_id=identity["id"], actor_role=identity["role"], action="auth.logout",
        target_type="session", description="Signed out."
    )


@router.get("/me")
def get_me(identity: dict[str, Any] = Depends(get_identity)) -> dict[str, Any]:
    return {"user": _identity(identity)}
