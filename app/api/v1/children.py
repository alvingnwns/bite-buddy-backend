from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.api.deps import require_child
from app.api.errors import api_error
from app.core.supabase import get_supabase_service_client
from app.models.base import CamelModel
from app.services.activity_service import record_activity
from app.services.ai_service import AIService
from app.services.integration_service import canonical_pet, dashboard, notification, schedules, streak_days
from app.services.reasoning_service import ReasoningService
from app.services.storage_service import StorageService

router = APIRouter()
storage_service = StorageService()
ai_service = AIService()
reasoning_service = ReasoningService()
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


class ProfileUpdate(CamelModel):
    username: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    allergies: str | None = None


class ConfirmFoodRequest(CamelModel):
    portion_grams: float
    food_name: str | None = None
    sugar_amount_grams: float | None = None


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


def _detected_image_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def _image_bytes(file: UploadFile) -> tuple[bytes, str]:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise api_error(413, "upload_too_large", "Image size must not exceed 8 MB.")
    if not data:
        raise api_error(400, "empty_upload", "The uploaded image is empty.")
    detected_type = _detected_image_type(data)
    if detected_type not in ALLOWED_IMAGE_TYPES:
        raise api_error(415, "unsupported_media_type", "Only JPEG, PNG, and WebP images are supported.")
    return data, detected_type


@router.post("/me/food-analyses", status_code=201)
async def analyze_food(file: UploadFile = File(...), identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    data, mime_type = await _image_bytes(file)
    try:
        public_url, detection = await asyncio.gather(
            storage_service.upload_image(file_bytes=data, filename=file.filename or "food.jpg", bucket_name="food-photos"),
            ai_service.detect_food_ingredients(image_bytes=data, mime_type=mime_type),
        )
    except HTTPException:
        raise
    except Exception:
        raise api_error(502, "analysis_failed", "The food image could not be analyzed.")
    is_food, food_name, ingredients = detection
    if not is_food:
        raise api_error(400, "food_not_detected", "No food was detected in the image.")
    totals = reasoning_service.calculate_totals(ingredients)
    portion = sum(float(item.get("weight_g", 0) or 0) for item in ingredients) or 100
    payload = {"ingredients": ingredients, "foodName": food_name, "portionGrams": portion, "nutrition": totals}
    inserted = get_supabase_service_client().table("analysis_drafts").insert({
        "child_id": identity["id"], "analysis_type": "food", "payload": payload,
        "image_url": public_url, "status": "draft",
    }).execute().data[0]
    record_activity(
        actor_id=identity["id"], actor_role="child", action="food_analysis.create",
        target_type="analysis_draft", target_id=str(inserted["id"]), child_id=identity["id"],
        description="Analyzed a food image.",
    )
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
    if req.food_name is not None and not req.food_name.strip():
        raise api_error(422, "validation_error", "One or more fields are invalid.", {"fields": {"foodName": ["Must not be blank."]}})
    if req.sugar_amount_grams is not None and req.sugar_amount_grams < 0:
        raise api_error(422, "validation_error", "One or more fields are invalid.", {"fields": {"sugarAmountGrams": ["Must be zero or greater."]}})
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
    if req.food_name is not None:
        payload["foodName"] = req.food_name.strip()
    if req.sugar_amount_grams is not None:
        nutrition["sugar_g"] = round(req.sugar_amount_grams, 2)
    if req.food_name is not None or req.sugar_amount_grams is not None:
        payload["nutrition"] = nutrition
        client.table("analysis_drafts").update({"payload": payload}).eq("id", analysis_id).eq("child_id", identity["id"]).execute()
        record_activity(actor_id=identity["id"], actor_role="child", action="food_analysis.update", target_type="analysis_draft", target_id=analysis_id, child_id=identity["id"], description="Corrected food analysis before confirmation.")
    is_healthy = float(nutrition.get("sugar_g", 0)) < 15
    try:
        result = client.rpc("confirm_child_analysis", {
            "p_child_id": identity["id"], "p_analysis_id": analysis_id,
            "p_analysis_type": "food", "p_portion_grams": req.portion_grams,
            "p_nutrition": nutrition, "p_is_healthy": is_healthy,
        }).execute().data
    except Exception as exc:
        message = str(exc)
        if "analysis_forbidden" in message: raise api_error(403, "forbidden", "This operation is not permitted.")
        if "analysis_not_found" in message: raise api_error(404, "analysis_not_found", "Food analysis was not found.")
        raise api_error(500, "confirmation_failed", "Food confirmation could not be completed.")
    result["history"] = _food_history(result["history"])
    return result


@router.post("/me/medicine-analyses", status_code=201)
async def analyze_medicine(file: UploadFile = File(...), identity: dict[str, Any] = Depends(require_child)) -> dict[str, Any]:
    data, mime_type = await _image_bytes(file)
    try:
        public_url, detected = await asyncio.gather(
            storage_service.upload_image(file_bytes=data, filename=file.filename or "medicine.jpg", bucket_name="medicine-photos"),
            ai_service.detect_medicine(image_bytes=data, mime_type=mime_type),
        )
    except HTTPException:
        raise
    except Exception:
        raise api_error(502, "analysis_failed", "The medicine image could not be analyzed.")
    is_medicine = bool(detected.get("is_medicine", False)) if isinstance(detected, dict) else False
    inserted = get_supabase_service_client().table("analysis_drafts").insert({
        "child_id": identity["id"], "analysis_type": "medicine", "payload": {"detected": detected, "isMedicine": is_medicine},
        "image_url": public_url, "status": "awaiting_confirmation" if is_medicine else "failed",
    }).execute().data[0]
    record_activity(
        actor_id=identity["id"], actor_role="child", action="medicine_analysis.create",
        target_type="analysis_draft", target_id=str(inserted["id"]), child_id=identity["id"],
        description="Analyzed a medicine image.",
    )
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
    try:
        result = client.rpc("confirm_child_analysis", {
            "p_child_id": identity["id"], "p_analysis_id": analysis_id,
            "p_analysis_type": "medicine", "p_portion_grams": None,
            "p_nutrition": {}, "p_is_healthy": True,
        }).execute().data
    except Exception as exc:
        message = str(exc)
        if "analysis_forbidden" in message: raise api_error(403, "forbidden", "This operation is not permitted.")
        if "analysis_not_found" in message: raise api_error(404, "analysis_not_found", "Medicine analysis was not found.")
        if "invalid_medicine" in message: raise api_error(409, "invalid_medicine", "This analysis cannot be confirmed as medicine.")
        raise api_error(500, "confirmation_failed", "Medicine confirmation could not be completed.")
    result["history"] = _medicine_history(result["history"])
    return result


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
    query = query.or_(f"recipient_user_id.is.null,recipient_user_id.eq.{identity['id']}")
    if cursor: query = query.lt("created_at", cursor)
    rows = query.order("created_at", desc=True).limit(limit + 1).execute().data or []
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {"items": [notification(row) for row in rows], "nextCursor": rows[-1].get("created_at") if has_more and rows else None}


@router.patch("/me/notifications/{notification_id}/read", status_code=204)
def mark_notification_read(notification_id: str, identity: dict[str, Any] = Depends(require_child)) -> None:
    client = get_supabase_service_client()
    rows = (client.table("alerts").select("id").eq("id", notification_id).eq("child_id", identity["id"])
            .or_(f"recipient_user_id.is.null,recipient_user_id.eq.{identity['id']}").execute().data or [])
    if not rows: raise api_error(404, "notification_not_found", "Notification was not found.")
    client.table("alerts").delete().eq("id", notification_id).eq("child_id", identity["id"]).execute()
    record_activity(actor_id=identity["id"], actor_role="child", action="notification.delete_after_read", target_type="notification", target_id=notification_id, child_id=identity["id"], description="Deleted notification after it was read.")
