from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from app.core.supabase import get_supabase_service_client
from pydantic import BaseModel

router = APIRouter()

class ClinicalParameterCreate(BaseModel):
    child_id: UUID
    weight_kg: float | None = None
    height_cm: float | None = None
    bmi: float | None = None
    target_daily_calories: int | None = None
    target_daily_water_ml: int | None = None

@router.post("/", response_model=Dict[str, Any])
def create_clinical_parameter(params: ClinicalParameterCreate) -> Any:
    """
    Menyimpan rekam parameter klinis baru (misal hasil kunjungan dokter).
    """
    client = get_supabase_service_client()
    try:
        # Pydantic otomatis memvalidasi, tapi kita perlu konversi UUID ke string
        data = params.model_dump(exclude_unset=True)
        data["child_id"] = str(data["child_id"])
        
        response = client.table("clinical_parameters").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=400, detail="Gagal menyimpan parameter klinis")
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{child_id}", response_model=List[Dict[str, Any]])
def get_clinical_history(
    child_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0)
) -> Any:
    """
    Mendapatkan riwayat parameter klinis untuk seorang anak (dengan pagination).
    """
    client = get_supabase_service_client()
    try:
        start = offset
        end = offset + limit - 1
        
        response = client.table("clinical_parameters") \
            .select("*") \
            .eq("child_id", str(child_id)) \
            .order("created_at", desc=True) \
            .range(start, end) \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{child_id}/latest", response_model=Dict[str, Any])
def get_latest_clinical_parameters(child_id: UUID) -> Any:
    """
    Mendapatkan parameter klinis yang paling baru.
    """
    client = get_supabase_service_client()
    try:
        response = client.table("clinical_parameters") \
            .select("*") \
            .eq("child_id", str(child_id)) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail="Data klinis tidak ditemukan")
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
