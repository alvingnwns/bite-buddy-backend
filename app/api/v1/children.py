from typing import Any, Dict, List, Optional
import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query

from app.core.auth import get_current_user
from app.core.supabase import get_supabase_service_client
from app.models.base import CamelModel
from app.models.database import Gender, MealType

from app.services.ai_service import AIService
from app.services.reasoning_service import ReasoningService
from app.services.gamification_service import GamificationService
from app.services.log_service import LogService
from app.services.storage_service import StorageService

router = APIRouter()

storage_service = StorageService()
ai_service = AIService()
reasoning_service = ReasoningService()
gamification_service = GamificationService()
log_service = LogService()

# In-memory drafts for MVP (No DB schema change required)
food_drafts = {}
med_drafts = {}

class ProfileUpdate(CamelModel):
    username: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    allergies: Optional[str] = None

class ConfirmFoodReq(CamelModel):
    portion_grams: float

@router.get("/me/profile")
def get_child_profile(current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    client = get_supabase_service_client()
    child_id = current_user["id"]
    
    # Get user profile
    user_resp = client.table("users").select("*").eq("id", child_id).single().execute()
    if not user_resp.data:
        raise HTTPException(status_code=404, detail="Child profile not found")
        
    user = user_resp.data
    
    # Get clinical parameters
    clinical_resp = client.table("clinical_parameters").select("*").eq("child_id", child_id).order("created_at", desc=True).limit(1).execute()
    clinical = clinical_resp.data[0] if clinical_resp.data else {}
    
    # Get doctor name if applicable
    doctor_name = None
    if user.get("doctor_id"):
        doc_resp = client.table("users").select("full_name").eq("id", user["doctor_id"]).execute()
        if doc_resp.data:
            doctor_name = doc_resp.data[0].get("full_name")
            
    # Asumsi patient_code disimpan atau dimapping dari suatu field (sementara return dummy jika tidak ada)
    patient_code = user.get("patient_code", "UNKNOWN")
    
    return {
        "childId": child_id,
        "patientCode": patient_code,
        "username": user.get("full_name"), # We mapped username to full_name in auth
        "doctorName": doctor_name,
        "fullName": user.get("full_name"),
        "birthdate": user.get("birth_date"),
        "gender": user.get("gender"),
        "heightCm": clinical.get("height_cm"),
        "weightKg": clinical.get("weight_kg"),
        "allergies": clinical.get("allergies", [])[0] if clinical.get("allergies") else None,
    }

@router.patch("/me/profile")
def update_child_profile(req: ProfileUpdate, current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    client = get_supabase_service_client()
    child_id = current_user["id"]
    
    # Update users table if username is provided
    if req.username is not None:
        client.table("users").update({"full_name": req.username}).eq("id", child_id).execute()
        
    # Update clinical parameters
    clinical_data = {}
    if req.height_cm is not None:
        clinical_data["height_cm"] = req.height_cm
    if req.weight_kg is not None:
        clinical_data["weight_kg"] = req.weight_kg
    if req.allergies is not None:
        clinical_data["allergies"] = [req.allergies]
        
    if clinical_data:
        # Check if clinical param exists
        existing = client.table("clinical_parameters").select("id").eq("child_id", child_id).order("created_at", desc=True).limit(1).execute()
        if existing.data:
            client.table("clinical_parameters").update(clinical_data).eq("id", existing.data[0]["id"]).execute()
        else:
            clinical_data["child_id"] = child_id
            clinical_data["recorded_by"] = child_id
            client.table("clinical_parameters").insert(clinical_data).execute()
            
    return get_child_profile(current_user)

@router.get("/me/dashboard")
def get_child_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    client = get_supabase_service_client()
    child_id = current_user["id"]
    
    pet_resp = client.table("virtual_pets").select("*").eq("child_id", child_id).single().execute()
    pet = pet_resp.data if pet_resp.data else {"level": 1, "happiness": 100, "hunger": 100, "experience_points": 0}
    
    # Calculate HP and XP as ratio 0-1
    # Assuming max HP is based on level, here we just do a simple mapping for MVP
    hp_ratio = (pet.get("happiness", 100) + pet.get("hunger", 100)) / 200.0
    xp_ratio = (pet.get("experience_points", 0) % 100) / 100.0 # Just a dummy calculation
    
    # Get streak (dummy for MVP)
    streak_days = 0
    
    return {
        "childId": child_id,
        "pet": {
            "level": pet.get("level", 1),
            "hp": hp_ratio,
            "xp": xp_ratio
        },
        "streakDays": streak_days,
        "asOf": datetime.now(timezone.utc).isoformat()
    }

@router.post("/me/food-analyses")
async def analyze_food(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    file_bytes = await file.read()
    try:
        upload_task = storage_service.upload_image(file_bytes=file_bytes, filename=file.filename, bucket_name="food-photos")
        ai_task = ai_service.detect_food_ingredients(image_bytes=file_bytes, mime_type=file.content_type or "image/jpeg")
        public_url, detected_ingredients = await asyncio.gather(upload_task, ai_task)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    analysis_id = str(uuid.uuid4())
    food_name = detected_ingredients[0].get("ingredient", "Unknown Food") if detected_ingredients else "Unknown Food"
    
    # Store draft in memory
    food_drafts[analysis_id] = {
        "child_id": current_user["id"],
        "ingredients": detected_ingredients,
        "public_url": public_url,
        "food_name": food_name
    }
    
    # Return draft shape as required by frontend
    return {
        "analysisId": analysis_id,
        "foodName": food_name,
        "sugarAmountGrams": 0,
        "sugarCategory": "unknown",
        "portionGrams": 100,
        "caloriesKcal": 0,
        "carbohydratesGrams": 0,
        "fiberGrams": 0,
        "proteinGrams": 0,
        "fatGrams": 0,
        "imageUrl": public_url,
        "status": "draft"
    }

@router.post("/me/food-analyses/{analysis_id}/confirm")
async def confirm_food(
    analysis_id: str,
    req: ConfirmFoodReq,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    if analysis_id not in food_drafts:
        raise HTTPException(status_code=404, detail="Draft not found or expired")
        
    draft = food_drafts[analysis_id]
    if str(draft["child_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Unauthorized to confirm this draft")
        
    # Scale ingredients by portion (MVP: just pass it down)
    nutrition_data = await reasoning_service.process_confirmed_meal(draft["ingredients"])
    
    db_record = log_service.create_food_log(
        child_id=current_user["id"],
        logged_by=current_user["id"],
        meal_type=MealType.snack, # MVP default
        nutrition_data=nutrition_data,
        public_url=draft["public_url"],
        notes=None
    )
    
    total_calories = int(nutrition_data["total_calories"])
    is_healthy = nutrition_data.get("is_healthy", True)
    gamification_service.evaluate_food_compliance(child_id=current_user["id"], total_calories=total_calories, is_healthy=is_healthy)
    
    del food_drafts[analysis_id]
    
    return {
        "history": {
            "id": str(db_record.id),
            "childId": str(db_record.child_id),
            "type": "food",
            "submittedAt": db_record.created_at.isoformat(),
            "imageUrl": draft["public_url"],
            "status": "done",
            "foodName": draft["food_name"],
            "analysisId": analysis_id,
            "healthClassification": "healthy" if is_healthy else "unhealthy"
        },
        "pet": {"level": 1, "hp": 1.0, "xp": 0.5},
        "affectedSchedule": {"id": "dummy-sch", "status": "done"},
        "streakDays": 1
    }

@router.post("/me/medicine-analyses")
async def analyze_medicine(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    file_bytes = await file.read()
    try:
        upload_task = storage_service.upload_image(file_bytes=file_bytes, filename=file.filename, bucket_name="medicine-photos")
        ai_task = ai_service.detect_medicine(image_bytes=file_bytes, mime_type=file.content_type or "image/jpeg")
        public_url, detected = await asyncio.gather(upload_task, ai_task)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    analysis_id = str(uuid.uuid4())
    is_medicine = detected.get("is_medicine", False) if isinstance(detected, dict) else True
    
    med_drafts[analysis_id] = {
        "child_id": current_user["id"],
        "detected": detected,
        "public_url": public_url,
        "is_medicine": is_medicine
    }
    
    return {
        "analysisId": analysis_id,
        "isMedicine": is_medicine,
        "imageUrl": public_url,
        "status": "awaiting_confirmation" if is_medicine else "failed"
    }

@router.post("/me/medicine-analyses/{analysis_id}/confirm")
async def confirm_medicine(
    analysis_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    if analysis_id not in med_drafts:
        raise HTTPException(status_code=404, detail="Draft not found or expired")
        
    draft = med_drafts[analysis_id]
    if str(draft["child_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    db_record = log_service.create_medication_log(
        child_id=current_user["id"],
        administered_by=current_user["id"],
        detected_medicine=str(draft["detected"]),
        dosage=1.0, # dummy default
        dosage_unit="unit",
        route="oral",
        public_url=draft["public_url"],
        notes=None
    )
    
    gamification_service.evaluate_medicine_compliance(child_id=current_user["id"])
    del med_drafts[analysis_id]
    
    return {
        "history": {
            "id": str(db_record.id),
            "childId": str(db_record.child_id),
            "type": "medicine",
            "submittedAt": db_record.created_at.isoformat(),
            "imageUrl": draft["public_url"],
            "status": "done",
            "isMedicine": draft["is_medicine"],
            "analysisId": analysis_id
        },
        "pet": {"level": 1, "hp": 1.0, "xp": 0.5},
        "affectedSchedule": {"id": "dummy-sch", "status": "done"},
        "streakDays": 1
    }

@router.get("/me/history")
def get_history(
    type: str = Query("food"),
    limit: int = Query(20),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    client = get_supabase_service_client()
    child_id = current_user["id"]
    
    items = []
    if type == "food":
        resp = client.table("food_logs").select("*").eq("child_id", child_id).order("created_at", desc=True).limit(limit).execute()
        for log in resp.data:
            items.append({
                "id": log["id"],
                "childId": log["child_id"],
                "type": "food",
                "submittedAt": log["created_at"],
                "imageUrl": log.get("photo_url"),
                "status": "done",
                "foodName": log.get("food_name"),
                "analysisId": "dummy-analysis-id",
                "healthClassification": "healthy" if log.get("is_healthy") else "unhealthy"
            })
    else:
        resp = client.table("medication_logs").select("*").eq("child_id", child_id).order("created_at", desc=True).limit(limit).execute()
        for log in resp.data:
            items.append({
                "id": log["id"],
                "childId": log["child_id"],
                "type": "medicine",
                "submittedAt": log["created_at"],
                "imageUrl": log.get("photo_url"),
                "status": "done",
                "isMedicine": True,
                "analysisId": "dummy-analysis-id"
            })
            
    return {"items": items, "nextCursor": None}

@router.get("/me/schedules")
def get_schedules(
    date: str = Query(None),
    timezone: str = Query("Asia/Jakarta"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    # Dummy MVP schedule
    return {
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "timezone": timezone,
        "items": []
    }

@router.get("/me/notifications")
def get_notifications(
    limit: int = Query(20),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    # Dummy MVP notifications
    return {"items": [], "nextCursor": None}

@router.patch("/me/notifications/{notification_id}/read")
def read_notification(
    notification_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    return {
        "id": notification_id,
        "childId": current_user["id"],
        "senderType": "system",
        "title": "Read Notification",
        "message": "",
        "isRead": True,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
