from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.deps import require_child
from app.api.errors import api_error
from app.core.supabase import get_supabase_service_client
from app.models.base import CamelModel
from app.services.activity_service import record_activity
from app.services.ai_service import AIService
from app.services.gamification_service import GamificationService
from app.services.integration_service import canonical_pet, complete_matching_schedule, dashboard, notification, schedules, streak_days
from app.services.reasoning_service import ReasoningService
from app.services.storage_service import StorageService

router = APIRouter()
storage_service = StorageService()
ai_service = AIService()
reasoning_service = ReasoningService()
gamification_service = GamificationService()
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


class ProfileUpdate(CamelModel):
    username: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    allergies: str | None = None


class ConfirmFoodRequest(CamelModel):
    portion_grams: float


def _profile(child_id: str) -> dict[str, Any]:
    client = get_supabase_service_client()
    response = client.table("users").select("*").eq("id", child_id).single().execute()
    if not response.data:
        raise api_error(404, "profile_not_found", "Child profile was not found.")
    user = response.data
    clinical_rows = client.table("clinical_parameters").select("*").eq("child_id", child_id).order("created_at", desc=True).limit(1).execute().data or []
    clinical = clinical_rows[0] if clinical_rows else {}
    doctor_name = None
    if user.get("doctor_id"):
        doctors = client.table("users").select("full_name").eq("id", user["doctor_id"]).execute().data or []
        doctor_name = doctors[0].get("full_name") if doctors else None
    allergies = clinical.get("allergies") or []
    return {
        "childId": child_id, "patientCode": user.get("patient_code"),
        "username": user.get("username") or str(user.get("email", "")).split("@")[0],
        "doctorName": doctor_name, "fullName": user.get("full_name"),
        "birthdate": user.get("birth_date"), "gender": user.get("gender"),
        "heightCm": clinical.get("height_cm"), "weightKg": clinical.get("weight_kg"),
        "allergies": allergies[0] if isinstance(allergies, list) and allergies else "",
    }


@router.get("/me/profile")
def get_child_profile(identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    return _profile(identity["id"])


@router.patch("/me/profile")
def update_child_profile(req: ProfileUpdate, identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    client = get_supabase_service_client()
    child_id = identity["id"]
    if req.username is not None:
        username = req.username.strip()
        duplicate = client.table("users").select("id").ilike("username", username).neq("id", child_id).execute()
        if duplicate.data:
            raise api_error(409, "username_conflict", "Username is already in use.", {"fields": {"username": ["Already in use."]}})
        client.table("users").update({"username": username, "email": f"{username}@bitebuddy.com"}).eq("id", child_id).execute()
    clinical_data: dict[str, Any] = {}
    if req.height_cm is not None: clinical_data["height_cm"] = req.height_cm
    if req.weight_kg is not None: clinical_data["weight_kg"] = req.weight_kg
    if req.allergies is not None: clinical_data["allergies"] = [req.allergies] if req.allergies else []
    if clinical_data:
        existing = client.table("clinical_parameters").select("id").eq("child_id", child_id).order("created_at", desc=True).limit(1).execute()
        if existing.data:
            client.table("clinical_parameters").update(clinical_data).eq("id", existing.data[0]["id"]).execute()
        else:
            clinical_data.update({"child_id": child_id, "recorded_by": child_id, "height_cm": req.height_cm or 1, "weight_kg": req.weight_kg or 1})
            client.table("clinical_parameters").insert(clinical_data).execute()
    record_activity(actor_id=child_id, actor_role="child", action="profile.update", target_type="user", target_id=child_id, child_id=child_id, description="Updated profile.")
    return _profile(child_id)


@router.get("/me/dashboard")
def get_child_dashboard(identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    return dashboard(identity["id"])


@router.get("/me/schedules")
def get_child_schedules(identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    return schedules(identity["id"])


async def _image_bytes(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise api_error(415, "unsupported_media_type", "Only JPEG, PNG, and WebP images are supported.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise api_error(413, "upload_too_large", "Image size must not exceed 8 MB.")
    if not data:
        raise api_error(400, "empty_upload", "The uploaded image is empty.")
    return data


@router.post("/me/food-analyses", status_code=201)
async def analyze_food(file: UploadFile = File(...), identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    data = await _image_bytes(file)
    try:
        public_url, detection = await asyncio.gather(
            storage_service.upload_image(file_bytes=data, filename=file.filename or "food.jpg", bucket_name="food-photos"),
            ai_service.detect_food_ingredients(image_bytes=data, mime_type=file.content_type or "image/jpeg"),
        )
    except Exception:
        raise api_error(502, "analysis_failed", "The food image could not be analyzed.")
    is_food, ingredients = detection
    if not is_food:
        raise api_error(400, "food_not_detected", "No food was detected in the image.")
    totals = reasoning_service.calculate_totals(ingredients)
    portion = sum(float(item.get("weight_g", 0) or 0) for item in ingredients) or 100
    food_name = ", ".join(str(item.get("description") or item.get("ingredient") or "Food") for item in ingredients)
    payload = {"ingredients": ingredients, "foodName": food_name, "portionGrams": portion, "nutrition": totals}
    inserted = get_supabase_service_client().table("analysis_drafts").insert({
        "child_id": identity["id"], "analysis_type": "food", "payload": payload,
        "image_url": public_url, "status": "draft",
    }).execute().data[0]
    return _food_draft(inserted)


def _food_draft(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") or {}
    nutrition = payload.get("nutrition") or {}
    sugar = float(nutrition.get("sugar_g", 0) or 0)
    return {
        "analysisId": str(row["id"]), "isFood": True, "foodName": payload.get("foodName", "Food"),
        "sugarAmountGrams": sugar, "sugarCategory": "low" if sugar < 5 else "medium" if sugar < 15 else "high",
        "portionGrams": payload.get("portionGrams", 100), "caloriesKcal": nutrition.get("kcal", 0),
        "carbohydratesGrams": nutrition.get("carbs_g", 0), "fiberGrams": nutrition.get("fiber_g", 0),
        "proteinGrams": nutrition.get("protein_g", 0), "fatGrams": nutrition.get("fat_g", 0),
        "imageUrl": row["image_url"], "status": row["status"],
    }


def _food_history(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]), "childId": str(row["child_id"]), "type": "food",
        "submittedAt": row.get("consumed_at") or row.get("created_at"), "imageUrl": row.get("photo_url"),
        "status": "done", "foodName": row.get("food_name"),
        "analysisId": str(row["analysis_id"]) if row.get("analysis_id") else None,
        "healthClassification": "healthy" if row.get("is_healthy") else "unhealthy",
    }


def _medicine_history(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]), "childId": str(row["child_id"]), "type": "medicine",
        "submittedAt": row.get("administered_at") or row.get("created_at"), "imageUrl": row.get("photo_url"),
        "status": row.get("status", "done"), "isMedicine": bool(row.get("is_medicine", True)),
        "analysisId": str(row["analysis_id"]) if row.get("analysis_id") else None,
    }


def _confirmation(history: dict[str, Any], child_id: str, affected: dict[str, Any] | None) -> dict[str, Any]:
    return {"history": history, "pet": canonical_pet(child_id), "affectedSchedule": affected, "streakDays": streak_days(child_id)}


@router.post("/me/food-analyses/{analysis_id}/confirm")
async def confirm_food(analysis_id: str, req: ConfirmFoodRequest, identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    if req.portion_grams <= 0:
        raise api_error(422, "validation_error", "One or more fields are invalid.", {"fields": {"portionGrams": ["Must be greater than zero."]}})
    client = get_supabase_service_client()
    rows = client.table("analysis_drafts").select("*").eq("id", analysis_id).eq("analysis_type", "food").execute().data or []
    if not rows: raise api_error(404, "analysis_not_found", "Food analysis was not found.")
    draft = rows[0]
    if str(draft["child_id"]) != identity["id"]: raise api_error(403, "forbidden", "This operation is not permitted.")
    if draft["status"] == "confirmed":
        logs = client.table("food_logs").select("*").eq("analysis_id", analysis_id).execute().data or []
        if logs: return _confirmation(_food_history(logs[0]), identity["id"], None)
        raise api_error(409, "already_confirmed", "Food analysis was already confirmed.")
    payload = draft.get("payload") or {}
    base_portion = float(payload.get("portionGrams", 100) or 100)
    base = payload.get("nutrition") or {}
    scale = req.portion_grams / base_portion
    nutrition = {key: round(float(value or 0) * scale, 2) for key, value in base.items()}
    is_healthy = float(nutrition.get("sugar_g", 0)) < 15
    affected = complete_matching_schedule(identity["id"], "meal")
    inserted = client.table("food_logs").insert({
        "child_id": identity["id"], "logged_by": identity["id"], "meal_type": "snack",
        "meal_schedule_id": affected["id"] if affected else None, "food_name": payload.get("foodName", "Food"),
        "portion_size": f"{req.portion_grams:g} g", "portion_grams": req.portion_grams,
        "calories": round(float(nutrition.get("kcal", 0))), "photo_url": draft["image_url"],
        "nutrition": nutrition, "is_healthy": is_healthy, "analysis_id": analysis_id,
    }).execute().data[0]
    gamification_service.evaluate_food_compliance(UUID(identity["id"]), float(nutrition.get("kcal", 0)), is_healthy)
    client.table("analysis_drafts").update({"status": "confirmed", "confirmed_history_id": inserted["id"], "confirmed_at": datetime.now(timezone.utc).isoformat()}).eq("id", analysis_id).execute()
    record_activity(actor_id=identity["id"], actor_role="child", action="food.confirm", target_type="food_log", target_id=str(inserted["id"]), child_id=identity["id"], description="Confirmed food analysis.")
    return _confirmation(_food_history(inserted), identity["id"], affected)


@router.post("/me/medicine-analyses", status_code=201)
async def analyze_medicine(file: UploadFile = File(...), identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    data = await _image_bytes(file)
    try:
        public_url, detected = await asyncio.gather(
            storage_service.upload_image(file_bytes=data, filename=file.filename or "medicine.jpg", bucket_name="medicine-photos"),
            ai_service.detect_medicine(image_bytes=data, mime_type=file.content_type or "image/jpeg"),
        )
    except Exception:
        raise api_error(502, "analysis_failed", "The medicine image could not be analyzed.")
    is_medicine = bool(detected.get("is_medicine", False)) if isinstance(detected, dict) else False
    inserted = get_supabase_service_client().table("analysis_drafts").insert({
        "child_id": identity["id"], "analysis_type": "medicine", "payload": {"detected": detected, "isMedicine": is_medicine},
        "image_url": public_url, "status": "awaiting_confirmation" if is_medicine else "failed",
    }).execute().data[0]
    if not is_medicine:
        get_supabase_service_client().table("medication_logs").insert({
            "child_id": identity["id"], "administered_by": identity["id"], "medication_name": "Not medicine",
            "dosage": 0, "dosage_unit": "unit", "route": "oral", "scheduled_time": datetime.now(timezone.utc).time().isoformat(),
            "was_taken": False, "analysis_id": inserted["id"], "photo_url": public_url, "is_medicine": False, "status": "failed",
        }).execute()
    return {"analysisId": str(inserted["id"]), "isMedicine": is_medicine, "imageUrl": public_url, "status": inserted["status"]}


@router.post("/me/medicine-analyses/{analysis_id}/confirm")
def confirm_medicine(analysis_id: str, identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    client = get_supabase_service_client()
    rows = client.table("analysis_drafts").select("*").eq("id", analysis_id).eq("analysis_type", "medicine").execute().data or []
    if not rows: raise api_error(404, "analysis_not_found", "Medicine analysis was not found.")
    draft = rows[0]
    if str(draft["child_id"]) != identity["id"]: raise api_error(403, "forbidden", "This operation is not permitted.")
    if not (draft.get("payload") or {}).get("isMedicine"):
        raise api_error(409, "invalid_medicine", "This analysis cannot be confirmed as medicine.")
    existing = client.table("medication_logs").select("*").eq("analysis_id", analysis_id).execute().data or []
    if existing: return _confirmation(_medicine_history(existing[0]), identity["id"], None)
    detected = (draft.get("payload") or {}).get("detected") or {}
    name = detected.get("detected", "Medicine") if isinstance(detected, dict) else "Medicine"
    affected = complete_matching_schedule(identity["id"], "medicine")
    inserted = client.table("medication_logs").insert({
        "child_id": identity["id"], "administered_by": identity["id"], "medication_name": str(name),
        "dosage": 1, "dosage_unit": "unit", "route": "oral", "scheduled_time": datetime.now(timezone.utc).time().isoformat(),
        "was_taken": True, "analysis_id": analysis_id, "photo_url": draft["image_url"], "is_medicine": True, "status": "done",
    }).execute().data[0]
    gamification_service.evaluate_medicine_compliance(UUID(identity["id"]))
    client.table("analysis_drafts").update({"status": "confirmed", "confirmed_history_id": inserted["id"], "confirmed_at": datetime.now(timezone.utc).isoformat()}).eq("id", analysis_id).execute()
    record_activity(actor_id=identity["id"], actor_role="child", action="medicine.confirm", target_type="medication_log", target_id=str(inserted["id"]), child_id=identity["id"], description="Confirmed medicine analysis.")
    return _confirmation(_medicine_history(inserted), identity["id"], affected)


def history_list(child_id: str, history_type: str, limit: int, cursor: str | None) -> dict[str, Any]:
    if history_type not in {"food", "medicine"}: raise api_error(422, "validation_error", "History type must be food or medicine.")
    table = "food_logs" if history_type == "food" else "medication_logs"
    order_field = "consumed_at" if history_type == "food" else "administered_at"
    query = get_supabase_service_client().table(table).select("*").eq("child_id", child_id)
    if cursor: query = query.lt(order_field, cursor)
    rows = query.order(order_field, desc=True).limit(limit + 1).execute().data or []
    has_more = len(rows) > limit
    rows = rows[:limit]
    mapper = _food_history if history_type == "food" else _medicine_history
    return {"items": [mapper(row) for row in rows], "nextCursor": rows[-1].get(order_field) if has_more and rows else None}


@router.get("/me/history")
def get_history(history_type: str = Query("food", alias="type"), limit: int = Query(20, ge=1, le=100), cursor: str | None = None, identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    return history_list(identity["id"], history_type, limit, cursor)


def history_detail(child_id: str, history_id: str) -> dict[str, Any]:
    client = get_supabase_service_client()
    food = client.table("food_logs").select("*").eq("id", history_id).eq("child_id", child_id).execute().data or []
    if food:
        row = food[0]
        nutrition = row.get("nutrition") or {}
        return {"history": _food_history(row), "analysis": {
            "analysisId": str(row.get("analysis_id") or ""), "foodName": row.get("food_name"),
            "portionGrams": row.get("portion_grams"), "caloriesKcal": row.get("calories"),
            "sugarAmountGrams": nutrition.get("sugar_g", 0), "carbohydratesGrams": nutrition.get("carbs_g", 0),
            "fiberGrams": nutrition.get("fiber_g", 0), "proteinGrams": nutrition.get("protein_g", 0),
            "fatGrams": nutrition.get("fat_g", 0), "imageUrl": row.get("photo_url"),
        }}
    meds = client.table("medication_logs").select("*").eq("id", history_id).eq("child_id", child_id).execute().data or []
    if meds: return {"history": _medicine_history(meds[0]), "analysis": None}
    raise api_error(404, "history_not_found", "History item was not found.")


@router.get("/me/history/{history_id}")
def get_history_detail(history_id: str, identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    return history_detail(identity["id"], history_id)


@router.get("/me/notifications")
def get_notifications(limit: int = Query(20, ge=1, le=100), cursor: str | None = None, identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    query = get_supabase_service_client().table("alerts").select("*").eq("child_id", identity["id"])
    if cursor: query = query.lt("created_at", cursor)
    rows = query.order("created_at", desc=True).limit(limit + 1).execute().data or []
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {"items": [notification(row) for row in rows], "nextCursor": rows[-1].get("created_at") if has_more and rows else None}


@router.patch("/me/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    rows = get_supabase_service_client().table("alerts").update({"is_read": True}).eq("id", notification_id).eq("child_id", identity["id"]).execute().data or []
    if not rows: raise api_error(404, "notification_not_found", "Notification was not found.")
    record_activity(actor_id=identity["id"], actor_role="child", action="notification.read", target_type="notification", target_id=notification_id, child_id=identity["id"], description="Marked notification as read.")
    return notification(rows[0])
