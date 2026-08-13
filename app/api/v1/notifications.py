from typing import Any, Dict
from fastapi import APIRouter, Depends
import uuid

from app.core.auth import get_current_user
from app.core.supabase import get_supabase_service_client

router = APIRouter()

@router.post("/child/{child_id}", response_model=Dict[str, Any])
def notify_child(child_id: str, payload: dict, current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    """MVP Notify child"""
    client = get_supabase_service_client()
    notif_id = str(uuid.uuid4())
    data = {
        "id": notif_id,
        "child_id": child_id,
        "type": "medication_reminder",
        "message": payload.get("message", payload.get("title", "Notification")),
        "is_read": False
    }
    client.table("alerts").insert(data).execute()
    
    return {
        "data": {
            "id": notif_id,
            "childId": child_id,
            "senderType": "parent",
            "title": payload.get("title", "Notification"),
            "message": payload.get("message", ""),
            "isRead": False
        }
    }
