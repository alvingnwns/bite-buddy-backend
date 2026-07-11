from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.core.supabase import get_supabase_service_client
from pydantic import BaseModel

router = APIRouter()

class UserUpdate(BaseModel):
    name: str | None = None
    avatar_url: str | None = None

@router.get("/me", response_model=Dict[str, Any])
def get_my_profile(current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    """
    Mengambil profil user yang sedang login.
    """
    client = get_supabase_service_client()
    try:
        response = client.table("users").select("*").eq("id", current_user["id"]).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/children", response_model=List[Dict[str, Any]])
def get_children(
    user_id: UUID,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> Any:
    """
    Mengambil daftar anak dari seorang parent (user_id).
    """
    client = get_supabase_service_client()
    try:
        # Menambahkan limit dan offset untuk pagination
        # Supabase API python mendukung .range(start, end)
        # Jika offset=0, limit=10 -> range(0, 9)
        start = offset
        end = offset + limit - 1
        
        response = client.table("users") \
            .select("*") \
            .eq("parent_id", str(user_id)) \
            .order("created_at", desc=True) \
            .range(start, end) \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{user_id}", response_model=Dict[str, Any])
def update_user_profile(
    user_id: UUID,
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """
    Memperbarui profil pengguna (hanya name dan avatar_url).
    """
    # Pada Fase 7, kita harus memastikan current_user["id"] == str(user_id) 
    # atau user tersebut adalah parent dari user_id.
    update_data = user_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Tidak ada data untuk diupdate")

    client = get_supabase_service_client()
    try:
        response = client.table("users").update(update_data).eq("id", str(user_id)).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
