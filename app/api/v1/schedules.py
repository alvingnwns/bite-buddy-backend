from typing import Any, Dict, List
import uuid

from fastapi import APIRouter, HTTPException, Query, Depends
from app.core.auth import get_current_user

router = APIRouter()

MOCK_SCHEDULES = {}

@router.post("/child/{child_id}", response_model=Dict[str, Any])
def add_schedule_for_child(child_id: str, payload: dict, current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    payload["id"] = str(uuid.uuid4())
    payload["childId"] = child_id
    if child_id not in MOCK_SCHEDULES:
        MOCK_SCHEDULES[child_id] = []
    MOCK_SCHEDULES[child_id].append(payload)
    return {"data": payload}

@router.get("/me", response_model=Dict[str, Any])
def get_my_schedules(current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    child_id = current_user["id"]
    return {"data": MOCK_SCHEDULES.get(child_id, [])}

@router.get("/child/{child_id}", response_model=Dict[str, Any])
def get_child_schedules(child_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    return {"data": MOCK_SCHEDULES.get(child_id, [])}

@router.patch("/{schedule_id}", response_model=Dict[str, Any])
def update_schedule(schedule_id: str, payload: dict, current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    for schedules in MOCK_SCHEDULES.values():
        for s in schedules:
            if s.get("id") == schedule_id:
                s.update(payload)
                return {"data": s}
    raise HTTPException(status_code=404, detail="Schedule not found")

@router.delete("/{schedule_id}", response_model=Dict[str, Any])
def delete_schedule(schedule_id: str, current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    for child_id, schedules in MOCK_SCHEDULES.items():
        for i, s in enumerate(schedules):
            if s.get("id") == schedule_id:
                del schedules[i]
                return {"status": "success"}
    raise HTTPException(status_code=404, detail="Schedule not found")
