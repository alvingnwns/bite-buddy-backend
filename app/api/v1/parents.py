from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import get_current_user
from app.core.supabase import get_supabase_service_client
from app.models.base import CamelModel
from app.models.database import MealType

# We can re-use some logic from children endpoints
from app.api.v1.children import get_child_dashboard

router = APIRouter()

class LinkChildReq(CamelModel):
    child_code: str

class ReminderReq(CamelModel):
    title: str
    message: str
    type: str

@router.get("/me/children")
def get_children(current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    client = get_supabase_service_client()
    parent_id = current_user["id"]
    
    # Query anak yang parent_id-nya = parent_id
    resp = client.table("users").select("id, full_name, avatar_url, birth_date, gender").eq("parent_id", parent_id).execute()
    
    children_list = []
    for row in resp.data:
        children_list.append({
            "id": row["id"],
            "name": row["full_name"],
            "avatarUrl": row.get("avatar_url"),
            "healthStatus": "healthy", # dummy MVP
            "petLevel": 1 # dummy MVP
        })
        
    return {"children": children_list}

@router.post("/me/children/link")
def link_child(req: LinkChildReq, current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    client = get_supabase_service_client()
    parent_id = current_user["id"]
    
    # Cari anak berdasarkan username (full_name)
    child_resp = client.table("users").select("id, role").eq("full_name", req.child_code).execute()
    
    if not child_resp.data or child_resp.data[0]["role"] != "child":
        raise HTTPException(status_code=404, detail="Child not found with that code")
        
    child_id = child_resp.data[0]["id"]
    
    # Update parent_id anak tersebut
    client.table("users").update({"parent_id": parent_id}).eq("id", child_id).execute()
    
    return {"status": "success", "childId": child_id}

@router.get("/me/children/{child_id}")
def get_child_summary(child_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    client = get_supabase_service_client()
    parent_id = current_user["id"]
    
    # Validasi kepemilikan
    child_resp = client.table("users").select("id, parent_id, full_name, birth_date, gender").eq("id", child_id).single().execute()
    if not child_resp.data or str(child_resp.data.get("parent_id")) != str(parent_id):
        raise HTTPException(status_code=403, detail="Not authorized to access this child")
        
    child = child_resp.data
    
    return {
        "id": child["id"],
        "name": child["full_name"],
        "birthdate": child.get("birth_date"),
        "gender": child.get("gender"),
        "healthStatus": "healthy",
        "petLevel": 1,
        "recentAlerts": 0
    }

@router.get("/me/children/{child_id}/dashboard")
def get_child_dash(child_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    client = get_supabase_service_client()
    parent_id = current_user["id"]
    
    # Validasi
    child_resp = client.table("users").select("parent_id").eq("id", child_id).single().execute()
    if not child_resp.data or str(child_resp.data.get("parent_id")) != str(parent_id):
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    # Memanggil ulang logic dashboard anak dengan memalsukan current_user sbg anak
    mock_child_user = {"id": child_id, "role": "child"}
    return get_child_dashboard(mock_child_user)

@router.get("/me/children/{child_id}/schedules")
def get_child_schedules(
    child_id: str,
    date: str = Query(None),
    timezone: str = Query("Asia/Jakarta"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    return {
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "timezone": timezone,
        "items": []
    }

@router.post("/me/children/{child_id}/schedules")
def create_child_schedule(
    child_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    # Dummy MVP creation
    return {"status": "success", "scheduleId": "dummy-sch-id"}

@router.get("/me/children/{child_id}/history")
def get_child_history(
    child_id: str,
    type: str = Query("food"),
    limit: int = Query(20),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    client = get_supabase_service_client()
    
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
                "isMedicine": True
            })
            
    return {"items": items, "nextCursor": None}

@router.get("/me/children/{child_id}/notifications")
def get_child_notifications(
    child_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    return {"items": [], "nextCursor": None}

@router.post("/me/children/{child_id}/reminders")
def send_reminder(
    child_id: str,
    req: ReminderReq,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    # Create notification dummy
    return {
        "id": "dummy-reminder-id",
        "childId": child_id,
        "title": req.title,
        "message": req.message,
        "status": "sent"
    }
