from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from app.core.supabase import get_supabase_service_client
from app.models.database import CustomMealScheduleCreate, CustomMealScheduleUpdate

router = APIRouter()

@router.post("/", response_model=Dict[str, Any])
def create_schedule(schedule: CustomMealScheduleCreate) -> Any:
    """
    Membuat jadwal makan baru untuk anak.
    """
    client = get_supabase_service_client()
    try:
        data = schedule.model_dump(exclude_unset=True)
        data["child_id"] = str(data["child_id"])
        
        # Pydantic date/time objects to string for JSON serialization
        if "start_time" in data and data["start_time"]:
            data["start_time"] = data["start_time"].isoformat()
        if "end_time" in data and data["end_time"]:
            data["end_time"] = data["end_time"].isoformat()
        if "start_date" in data and data["start_date"]:
            data["start_date"] = data["start_date"].isoformat()
        if "end_date" in data and data["end_date"]:
            data["end_date"] = data["end_date"].isoformat()
        if "meal_type" in data:
            data["meal_type"] = data["meal_type"].value

        response = client.table("custom_meal_schedules").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=400, detail="Gagal menyimpan jadwal")
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{child_id}", response_model=List[Dict[str, Any]])
def get_schedules(
    child_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> Any:
    """
    Mendapatkan daftar jadwal makan anak (ber-pagination).
    """
    client = get_supabase_service_client()
    try:
        start = offset
        end = offset + limit - 1
        
        response = client.table("custom_meal_schedules") \
            .select("*") \
            .eq("child_id", str(child_id)) \
            .order("start_time", desc=False) \
            .range(start, end) \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{schedule_id}", response_model=Dict[str, Any])
def update_schedule(schedule_id: UUID, schedule_update: CustomMealScheduleUpdate) -> Any:
    """
    Memperbarui jadwal makan yang ada.
    """
    data = schedule_update.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="Tidak ada data untuk diupdate")
        
    if "start_time" in data and data["start_time"]:
        data["start_time"] = data["start_time"].isoformat()
    if "end_time" in data and data["end_time"]:
        data["end_time"] = data["end_time"].isoformat()
    if "end_date" in data and data["end_date"]:
        data["end_date"] = data["end_date"].isoformat()
    if "meal_type" in data and data["meal_type"]:
        data["meal_type"] = data["meal_type"].value

    client = get_supabase_service_client()
    try:
        response = client.table("custom_meal_schedules").update(data).eq("id", str(schedule_id)).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: UUID) -> Any:
    """
    Menghapus jadwal makan.
    """
    client = get_supabase_service_client()
    try:
        response = client.table("custom_meal_schedules").delete().eq("id", str(schedule_id)).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")
        return {"message": "Jadwal berhasil dihapus"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
