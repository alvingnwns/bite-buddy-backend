from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from app.core.supabase import get_supabase_service_client

router = APIRouter()

@router.get("/food/{child_id}", response_model=List[Dict[str, Any]])
def get_food_logs(
    child_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> Any:
    """
    Mendapatkan riwayat makan anak.
    """
    client = get_supabase_service_client()
    try:
        start = offset
        end = offset + limit - 1
        
        response = client.table("food_logs") \
            .select("*") \
            .eq("child_id", str(child_id)) \
            .order("consumed_at", desc=True) \
            .range(start, end) \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/medication/{child_id}", response_model=List[Dict[str, Any]])
def get_medication_logs(
    child_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> Any:
    """
    Mendapatkan riwayat minum obat anak.
    """
    client = get_supabase_service_client()
    try:
        start = offset
        end = offset + limit - 1
        
        response = client.table("medication_logs") \
            .select("*") \
            .eq("child_id", str(child_id)) \
            .order("administered_at", desc=True) \
            .range(start, end) \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
