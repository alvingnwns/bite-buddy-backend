from __future__ import annotations

import secrets
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
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


def _require_active_patient(doctor_id: str, patient_id: str) -> None:
    rows = (
        get_supabase_service_client().table("users")
        .select("id").eq("id", patient_id).eq("doctor_id", doctor_id)
        .eq("role", "child").eq("is_active", True).execute().data or []
    )
    if not rows:
        raise api_error(403, "forbidden", "This operation is not permitted.")


def _as_utc(value: str | datetime) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _utc_iso(value: str | datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _wib_period(days: int) -> tuple[date, date, datetime, datetime]:
    zone = ZoneInfo("Asia/Jakarta")
    end_date = datetime.now(zone).date()
    start_date = end_date - timedelta(days=days - 1)
    start_at = datetime.combine(start_date, time.min, zone).astimezone(timezone.utc)
    end_at = datetime.combine(end_date + timedelta(days=1), time.min, zone).astimezone(timezone.utc)
    return start_date, end_date, start_at, end_at


def _audit_read(request: Request, doctor_id: str, patient_id: str, action: str, target_type: str) -> None:
    record_activity(
        actor_id=doctor_id, actor_role="doctor", action=action,
        target_type=target_type, target_id=patient_id, child_id=patient_id,
        description=f"Viewed patient {target_type}.", request_id=request.state.request_id,
    )


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


@router.get("/me/patients/{patient_id}/blood-glucose")
def list_blood_glucose(
    patient_id: str, request: Request,
    limit: int = Query(5, ge=1, le=100),
    doctor: dict[str, Any] = Depends(require_doctor),
) -> dict[str, Any]:
    _require_active_patient(doctor["id"], patient_id)
    rows = (
        get_supabase_service_client().table("blood_glucose_records")
        .select("id,patient_id,value_mg_dl,recorded_at")
        .eq("patient_id", patient_id).order("recorded_at", desc=True)
        .limit(limit).execute().data or []
    )
    rows.reverse()
    _audit_read(request, doctor["id"], patient_id, "blood_glucose.list", "blood_glucose")
    return {
        "patientId": patient_id, "unit": "mg/dL",
        "items": [{
            "id": str(row["id"]), "patientId": patient_id,
            "valueMgDl": float(row["value_mg_dl"]),
            "recordedAt": _utc_iso(row["recorded_at"]),
        } for row in rows],
    }


@router.get("/me/patients/{patient_id}/nutrition")
def get_nutrition(
    patient_id: str, request: Request,
    days: int = Query(7, ge=7, le=7),
    requested_timezone: str = Query("Asia/Jakarta", alias="timezone"),
    doctor: dict[str, Any] = Depends(require_doctor),
) -> dict[str, Any]:
    if requested_timezone != "Asia/Jakarta":
        raise api_error(422, "validation_error", "One or more fields are invalid.", {"fields": {"timezone": ["Must be Asia/Jakarta."]}})
    _require_active_patient(doctor["id"], patient_id)
    start_date, end_date, start_at, end_at = _wib_period(days)
    rows = (
        get_supabase_service_client().table("food_logs")
        .select("id,consumed_at,nutrition").eq("child_id", patient_id)
        .gte("consumed_at", start_at.isoformat()).lt("consumed_at", end_at.isoformat())
        .order("consumed_at").execute().data or []
    )
    totals: dict[date, dict[str, float]] = {}
    for offset in range(days):
        totals[start_date + timedelta(days=offset)] = {key: 0.0 for key in ("sugar", "carbohydrates", "protein", "fiber", "fat")}
    source_keys = {"sugar": "sugar_g", "carbohydrates": "carbs_g", "protein": "protein_g", "fiber": "fiber_g", "fat": "fat_g"}
    for row in rows:
        day = _as_utc(row["consumed_at"]).astimezone(ZoneInfo("Asia/Jakarta")).date()
        if day not in totals:
            continue
        nutrition = row.get("nutrition") or {}
        for target, source in source_keys.items():
            totals[day][target] += float(nutrition.get(source, 0) or 0)
    items = []
    for day, values in totals.items():
        recorded_at = datetime.combine(day, time.min, ZoneInfo("Asia/Jakarta")).astimezone(timezone.utc)
        items.append({
            "id": f"nutrition-{patient_id}-{day.isoformat()}", "recordedAt": _utc_iso(recorded_at),
            "sugarGrams": round(values["sugar"], 2), "carbohydratesGrams": round(values["carbohydrates"], 2),
            "proteinGrams": round(values["protein"], 2), "fiberGrams": round(values["fiber"], 2),
            "fatGrams": round(values["fat"], 2),
        })
    _audit_read(request, doctor["id"], patient_id, "nutrition.view", "nutrition")
    return {
        "patientId": patient_id,
        "period": {"startDate": start_date.isoformat(), "endDate": end_date.isoformat(), "timezone": "Asia/Jakarta"},
        "unit": "g", "items": items,
    }


@router.get("/me/patients/{patient_id}/medication-adherence")
def get_medication_adherence(
    patient_id: str, request: Request,
    days: int = Query(30, ge=30, le=30),
    requested_timezone: str = Query("Asia/Jakarta", alias="timezone"),
    doctor: dict[str, Any] = Depends(require_doctor),
) -> dict[str, Any]:
    if requested_timezone != "Asia/Jakarta":
        raise api_error(422, "validation_error", "One or more fields are invalid.", {"fields": {"timezone": ["Must be Asia/Jakarta."]}})
    _require_active_patient(doctor["id"], patient_id)
    start_date, end_date, start_at, _ = _wib_period(days)
    rows = (
        get_supabase_service_client().table("schedule_occurrences")
        .select("id,occurrence_date,status,completed_at,schedule_id")
        .eq("child_id", patient_id).gte("occurrence_date", start_date.isoformat())
        .lte("occurrence_date", end_date.isoformat()).execute().data or []
    )
    schedule_ids = [str(row["schedule_id"]) for row in rows]
    medicine_schedules: dict[str, dict[str, Any]] = {}
    if schedule_ids:
        schedules = (
            get_supabase_service_client().table("custom_meal_schedules")
            .select("id,schedule_type,start_time,end_time").in_("id", schedule_ids)
            .eq("schedule_type", "medicine").execute().data or []
        )
        medicine_schedules = {str(row["id"]): row for row in schedules}
    counts = {"taken": 0, "takenLate": 0, "skipped": 0}
    now_wib = datetime.now(ZoneInfo("Asia/Jakarta"))
    for row in rows:
        schedule = medicine_schedules.get(str(row["schedule_id"]))
        if not schedule:
            continue
        occurrence_day = date.fromisoformat(str(row["occurrence_date"]))
        status = row.get("status")
        if status == "done": counts["taken"] += 1
        elif status == "late": counts["takenLate"] += 1
        elif status == "skipped": counts["skipped"] += 1
        elif status == "not_yet":
            due_value = schedule.get("end_time") or schedule.get("start_time")
            due_at = None
            if due_value:
                due_at = datetime.combine(occurrence_day, time.fromisoformat(str(due_value)), ZoneInfo("Asia/Jakarta"))
            if occurrence_day < now_wib.date() or (due_at is not None and due_at <= now_wib):
                counts["skipped"] += 1
    _audit_read(request, doctor["id"], patient_id, "medication_adherence.view", "medication_adherence")
    return {
        "patientId": patient_id,
        "period": {"startAt": _utc_iso(start_at), "endAt": _utc_iso(datetime.now(timezone.utc)), "timezone": "Asia/Jakarta"},
        "counts": counts,
    }


def _appointment(row: dict[str, Any], patient_id: str) -> dict[str, Any]:
    result = {
        "id": str(row["id"]), "patientId": patient_id, "title": row["title"],
        "startsAt": _utc_iso(row["starts_at"]), "status": row["status"],
    }
    if row.get("note") is not None: result["note"] = row["note"]
    if row.get("price_amount") is not None: result["priceAmount"] = float(row["price_amount"])
    if row.get("currency") is not None: result["currency"] = row["currency"]
    return result


@router.get("/me/patients/{patient_id}/appointments")
def list_appointments(
    patient_id: str, request: Request,
    upcoming_limit: int = Query(20, alias="upcomingLimit", ge=1, le=100),
    history_limit: int = Query(20, alias="historyLimit", ge=1, le=100),
    doctor: dict[str, Any] = Depends(require_doctor),
) -> dict[str, Any]:
    _require_active_patient(doctor["id"], patient_id)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    upcoming_rows = (
        get_supabase_service_client().table("doctor_appointments")
        .select("id,patient_id,title,starts_at,status,note,price_amount,currency")
        .eq("patient_id", patient_id).eq("doctor_id", doctor["id"])
        .eq("status", "scheduled").gte("starts_at", now_iso)
        .order("starts_at").limit(upcoming_limit).execute().data or []
    )
    elapsed_rows = (
        get_supabase_service_client().table("doctor_appointments")
        .select("id,patient_id,title,starts_at,status,note,price_amount,currency")
        .eq("patient_id", patient_id).eq("doctor_id", doctor["id"])
        .lt("starts_at", now_iso).order("starts_at", desc=True)
        .limit(history_limit).execute().data or []
    )
    completed_future_rows = (
        get_supabase_service_client().table("doctor_appointments")
        .select("id,patient_id,title,starts_at,status,note,price_amount,currency")
        .eq("patient_id", patient_id).eq("doctor_id", doctor["id"])
        .eq("status", "completed").gte("starts_at", now_iso)
        .order("starts_at", desc=True).limit(history_limit).execute().data or []
    )
    history_by_id = {str(row["id"]): row for row in [*elapsed_rows, *completed_future_rows]}
    history_rows = list(history_by_id.values())
    upcoming_rows.sort(key=lambda row: _as_utc(row["starts_at"]))
    history_rows.sort(key=lambda row: _as_utc(row["starts_at"]), reverse=True)
    _audit_read(request, doctor["id"], patient_id, "appointment.list", "appointment")
    return {
        "patientId": patient_id,
        "upcoming": [_appointment(row, patient_id) for row in upcoming_rows[:upcoming_limit]],
        "history": [_appointment(row, patient_id) for row in history_rows[:history_limit]],
    }
