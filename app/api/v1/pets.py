from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, HTTPException
from app.core.supabase import get_supabase_service_client
from pydantic import BaseModel

router = APIRouter()

class PetCreate(BaseModel):
    child_id: UUID
    name: str
    pet_type: str = "dog"

class PetUpdate(BaseModel):
    name: str | None = None
    pet_type: str | None = None

@router.post("/", response_model=Dict[str, Any])
def create_pet(pet: PetCreate) -> Any:
    """
    Membuat profil peliharaan baru untuk anak (hanya jika belum punya).
    """
    client = get_supabase_service_client()
    try:
        # Cek apakah sudah punya
        existing = client.table("virtual_pets").select("id").eq("child_id", str(pet.child_id)).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Anak ini sudah memiliki peliharaan")
            
        data = pet.model_dump()
        data["child_id"] = str(data["child_id"])
        # Default stats from DB schema will apply (exp=0, level=1, happiness=100, hunger=100)
        
        response = client.table("virtual_pets").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=400, detail="Gagal membuat peliharaan")
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{child_id}", response_model=Dict[str, Any])
def get_pet(child_id: UUID) -> Any:
    """
    Mendapatkan detail peliharaan anak saat ini.
    """
    client = get_supabase_service_client()
    try:
        response = client.table("virtual_pets").select("*").eq("child_id", str(child_id)).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Peliharaan tidak ditemukan")
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{pet_id}", response_model=Dict[str, Any])
def update_pet(pet_id: UUID, pet_update: PetUpdate) -> Any:
    """
    Memperbarui nama atau jenis peliharaan.
    """
    data = pet_update.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="Tidak ada data untuk diupdate")

    client = get_supabase_service_client()
    try:
        response = client.table("virtual_pets").update(data).eq("id", str(pet_id)).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Peliharaan tidak ditemukan")
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
