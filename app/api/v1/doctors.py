from __future__ import annotations

import secrets
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from pydantic import ConfigDict, Field, model_validator

from app.api.deps import require_doctor
from app.api.errors import api_error
from app.core.supabase import get_supabase_service_client
from app.models.base import CamelModel
from app.models.database import Gender
from app.services.activity_service import record_activity

router = APIRouter()


class PatientCreate(CamelModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=160)
    gender: Gender
    birthdate: date
    address: str = Field(min_length=1, max_length=500)
    height_cm: float = Field(ge=20, le=250)
    weight_kg: float = Field(ge=1, le=300)
    medical_history: str = Field(default="", max_length=5000)
    medication_schedule: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_birthdate(self) -> "PatientCreate":
        if self.birthdate > datetime.now(ZoneInfo("Asia/Jakarta")).date():
            raise ValueError("Birthdate cannot be in the future.")
        return self


class PatientUpdate(CamelModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    gender: Gender | None = None
    birthdate: date | None = None
    address: str | None = Field(default=None, min_length=1, max_length=500)
    height_cm: float | None = Field(default=None, ge=20, le=250)
    weight_kg: float | None = Field(default=None, ge=1, le=300)
    medical_history: str | None = Field(default=None, max_length=5000)
    medication_schedule: list[str] | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def require_change(self) -> "PatientUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one profile field is required.")
        if self.birthdate and self.birthdate > datetime.now(ZoneInfo("Asia/Jakarta")).date():
            raise ValueError("Birthdate cannot be in the future.")
        return self


def _clean_instructions(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def _avatar(gender: str, birthdate: str | None) -> str:
    today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
    try:
        adult_cutoff = today.replace(year=today.year - 18)
    except ValueError:
        adult_cutoff = today.replace(year=today.year - 18, day=28)
    adult = bool(birthdate and birthdate <= adult_cutoff.isoformat())
    if gender == "female":
        return "woman" if adult else "girl"
    return "man" if adult else "boy"


def _pet_health(pet: dict[str, Any] | None) -> dict[str, Any]:
    if not pet:
        return {"hp": 1.0, "level": 1}
    hp = (float(pet.get("happiness", 100)) + float(pet.get("hunger", 100))) / 200
    return {"hp": round(max(0.0, min(1.0, hp)), 2), "level": int(pet.get("level", 1))}


def _pending_summary(row: dict[str, Any]) -> dict[str, Any]:
    birthdate = str(row["birth_date"])
    return {
        "id": str(row["id"]), "code": row["patient_code"],
        "fullName": row["full_name"], "avatarKey": _avatar(row["gender"], birthdate),
        "petHealth": _pet_health(None), "invitationStatus": "pending",
    }


def _claimed_summary(row: dict[str, Any], pet: dict[str, Any] | None) -> dict[str, Any]:
    birthdate = str(row.get("birth_date") or "")
    return {
        "id": str(row["id"]), "code": row["patient_code"],
        "fullName": row["full_name"], "avatarKey": _avatar(row.get("gender", "male"), birthdate),
        "petHealth": _pet_health(pet), "invitationStatus": "claimed",
    }


def _condition(clinical: dict[str, Any] | None) -> str:
    if not clinical:
        return "Awaiting clinical assessment"
    conditions = clinical.get("medical_conditions") or []
    return str(conditions[0]) if conditions else "Awaiting clinical assessment"


def _pending_detail(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **_pending_summary(row),
        "condition": "Awaiting clinical assessment",
        "profile": {
            "fullName": row["full_name"], "gender": row["gender"],
            "birthdate": str(row["birth_date"]), "address": row["address"],
            "heightCm": float(row["height_cm"]), "weightKg": float(row["weight_kg"]),
            "medicalHistory": row.get("medical_history") or "",
            "medicationSchedule": row.get("medication_instructions") or [],
        },
    }


def _claimed_detail(
    user: dict[str, Any], clinical: dict[str, Any] | None,
    profile: dict[str, Any] | None, pet: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = _claimed_summary(user, pet)
    return {
        **summary, "condition": _condition(clinical),
        "profile": {
            "fullName": user["full_name"], "gender": user["gender"],
            "birthdate": str(user["birth_date"]), "address": user.get("address") or "",
            "heightCm": float(clinical["height_cm"]) if clinical else None,
            "weightKg": float(clinical["weight_kg"]) if clinical else None,
            "medicalHistory": (profile or {}).get("medical_history") or "",
            "medicationSchedule": (profile or {}).get("medication_instructions") or [],
        },
    }


def _patient_detail(doctor_id: str, patient_id: str) -> tuple[str, dict[str, Any]]:
    client = get_supabase_service_client()
    now = datetime.now(ZoneInfo("UTC")).isoformat()
    pending = client.table("patient_invitations").select("*").eq("id", patient_id).eq("doctor_id", doctor_id).eq("status", "pending").gt("expires_at", now).execute().data or []
    if pending:
        return "pending", _pending_detail(pending[0])
    claimed = client.table("users").select("id,full_name,gender,birth_date,address,patient_code").eq("id", patient_id).eq("doctor_id", doctor_id).eq("role", "child").eq("is_active", True).execute().data or []
    if not claimed:
        raise api_error(403, "forbidden", "This operation is not permitted.")
    clinical_rows = client.table("clinical_parameters").select("height_cm,weight_kg,medical_conditions").eq("child_id", patient_id).order("recorded_at", desc=True).limit(1).execute().data or []
    profiles = client.table("doctor_patient_profiles").select("medical_history,medication_instructions").eq("patient_id", patient_id).eq("doctor_id", doctor_id).execute().data or []
    pets = client.table("virtual_pets").select("happiness,hunger,level").eq("child_id", patient_id).eq("is_active", True).execute().data or []
    return "claimed", _claimed_detail(claimed[0], clinical_rows[0] if clinical_rows else None, profiles[0] if profiles else None, pets[0] if pets else None)


def _new_patient_code() -> str:
    client = get_supabase_service_client()
    for _ in range(20):
        code = "P" + "".join(secrets.choice("0123456789") for _ in range(6))
        existing = client.table("patient_invitations").select("id").ilike("patient_code", code).execute().data or []
        if not existing:
            return code
    raise api_error(503, "patient_code_unavailable", "A patient code could not be generated.")


@router.get("/me/patients")
def list_patients(request: Request, doctor: dict[str, Any] = Depends(require_doctor)) -> dict[str, Any]:
    doctor_id = doctor["id"]
    client = get_supabase_service_client()
    now = datetime.now(ZoneInfo("UTC")).isoformat()
    invitations = client.table("patient_invitations").select("*").eq("doctor_id", doctor_id).eq("status", "pending").gt("expires_at", now).order("created_at", desc=True).execute().data or []
    users = client.table("users").select("id,full_name,gender,birth_date,patient_code").eq("doctor_id", doctor_id).eq("role", "child").eq("is_active", True).order("full_name").execute().data or []
    pets_by_child: dict[str, dict[str, Any]] = {}
    if users:
        pets = client.table("virtual_pets").select("child_id,happiness,hunger,level").in_("child_id", [row["id"] for row in users]).eq("is_active", True).execute().data or []
        pets_by_child = {str(row["child_id"]): row for row in pets}
    items = [_pending_summary(row) for row in invitations]
    items.extend(_claimed_summary(row, pets_by_child.get(str(row["id"]))) for row in users)
    record_activity(actor_id=doctor_id, actor_role="doctor", action="doctor.patient.list", target_type="patient", description="Viewed assigned patients.", request_id=request.state.request_id)
    return {"items": items}


@router.post("/me/patients", status_code=201)
def create_patient(req: PatientCreate, request: Request, doctor: dict[str, Any] = Depends(require_doctor)) -> dict[str, Any]:
    code = _new_patient_code()
    row = get_supabase_service_client().table("patient_invitations").insert({
        "doctor_id": doctor["id"], "patient_code": code,
        "full_name": req.full_name.strip(), "gender": req.gender.value,
        "birth_date": req.birthdate.isoformat(), "address": req.address.strip(),
        "height_cm": req.height_cm, "weight_kg": req.weight_kg,
        "medical_history": req.medical_history.strip(),
        "medication_instructions": _clean_instructions(req.medication_schedule),
    }).execute().data
    if not row:
        raise api_error(500, "patient_create_failed", "The patient invitation could not be created.")
    detail = _pending_detail(row[0])
    record_activity(actor_id=doctor["id"], actor_role="doctor", action="doctor.patient.create", target_type="patient_invitation", target_id=str(row[0]["id"]), description="Created patient invitation.", request_id=request.state.request_id, metadata={"patient_code": code})
    return detail


@router.get("/me/patients/{patient_id}")
def get_patient(patient_id: str, request: Request, doctor: dict[str, Any] = Depends(require_doctor)) -> dict[str, Any]:
    _, detail = _patient_detail(doctor["id"], patient_id)
    record_activity(actor_id=doctor["id"], actor_role="doctor", action="doctor.patient.view", target_type="patient", target_id=patient_id, description="Viewed patient profile.", request_id=request.state.request_id)
    return detail


@router.patch("/me/patients/{patient_id}")
def update_patient(req: PatientUpdate, patient_id: str, request: Request, doctor: dict[str, Any] = Depends(require_doctor)) -> dict[str, Any]:
    state, _ = _patient_detail(doctor["id"], patient_id)
    values = req.model_dump(exclude_unset=True)
    client = get_supabase_service_client()
    if state == "pending":
        mapping = {"full_name": "full_name", "gender": "gender", "birthdate": "birth_date", "address": "address", "height_cm": "height_cm", "weight_kg": "weight_kg", "medical_history": "medical_history", "medication_schedule": "medication_instructions"}
        update = {}
        for key, value in values.items():
            if key == "gender": value = value.value
            if key == "birthdate": value = value.isoformat()
            if key == "medication_schedule": value = _clean_instructions(value)
            if isinstance(value, str): value = value.strip()
            update[mapping[key]] = value
        rows = client.table("patient_invitations").update(update).eq("id", patient_id).eq("doctor_id", doctor["id"]).eq("status", "pending").execute().data or []
        if not rows:
            raise api_error(409, "patient_state_changed", "The patient invitation state changed.")
    else:
        user_update = {}
        for key in ("full_name", "gender", "birthdate", "address"):
            if key in values:
                db_key = "birth_date" if key == "birthdate" else key
                value = values[key]
                if key == "gender": value = value.value
                if key == "birthdate": value = value.isoformat()
                if isinstance(value, str): value = value.strip()
                user_update[db_key] = value
        if user_update:
            client.table("users").update(user_update).eq("id", patient_id).eq("doctor_id", doctor["id"]).execute()
        clinical_update = {key: values[key] for key in ("height_cm", "weight_kg") if key in values}
        if clinical_update:
            latest = client.table("clinical_parameters").select("id").eq("child_id", patient_id).order("recorded_at", desc=True).limit(1).execute().data or []
            if latest:
                client.table("clinical_parameters").update(clinical_update).eq("id", latest[0]["id"]).execute()
            elif "height_cm" in clinical_update and "weight_kg" in clinical_update:
                client.table("clinical_parameters").insert({"child_id": patient_id, "recorded_by": doctor["id"], **clinical_update}).execute()
            else:
                raise api_error(409, "clinical_profile_incomplete", "Height and weight are both required for this patient.")
        profile_update = {}
        if "medical_history" in values: profile_update["medical_history"] = values["medical_history"].strip()
        if "medication_schedule" in values: profile_update["medication_instructions"] = _clean_instructions(values["medication_schedule"])
        if profile_update:
            client.table("doctor_patient_profiles").upsert({"patient_id": patient_id, "doctor_id": doctor["id"], **profile_update}, on_conflict="patient_id").execute()
    _, detail = _patient_detail(doctor["id"], patient_id)
    record_activity(actor_id=doctor["id"], actor_role="doctor", action="doctor.patient.update", target_type="patient", target_id=patient_id, description="Updated patient profile.", request_id=request.state.request_id, metadata={"changed_fields": sorted(req.model_fields_set)})
    return detail
