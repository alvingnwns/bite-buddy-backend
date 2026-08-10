"""API endpoints untuk manajemen profil pengguna (user).

Endpoints:
  GET  /users/me           → Profil user yang sedang login
  GET  /users/{id}/children → Daftar anak dari parent
  PATCH /users/{id}        → Update profil user (nama, avatar, gender, dll)
"""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.core.supabase import get_supabase_service_client
from app.models.database import Gender, UserUpdate

router = APIRouter()


@router.get("/me", response_model=Dict[str, Any])
def get_my_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Ambil profil user yang sedang login.

    Menggunakan JWT dari header Authorization untuk identifikasi.
    (Pada fase ini, current_user masih mock — akan diganti di Fase 7)
    """
    client = get_supabase_service_client()
    try:
        response = (
            client.table("users")
            .select("*")
            .eq("id", current_user["id"])
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{user_id}/children", response_model=List[Dict[str, Any]])
def get_children(
    user_id: UUID,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Any:
    """Ambil daftar anak dari seorang parent (berdasarkan parent_id).

    Dipakai oleh dashboard orang tua untuk melihat semua anak yang terdaftar.
    Mendukung pagination via limit dan offset.
    """
    client = get_supabase_service_client()
    try:
        start = offset
        end = offset + limit - 1

        response = (
            client.table("users")
            .select("id, full_name, email, birth_date, gender, avatar_url, is_active, created_at")
            .eq("parent_id", str(user_id))
            .order("created_at", desc=True)
            .range(start, end)
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/{user_id}", response_model=Dict[str, Any])
def update_user_profile(
    user_id: UUID,
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Update profil pengguna.

    Field yang bisa diubah:
      - full_name  : nama lengkap (bukan 'name')
      - avatar_url : URL foto profil
      - is_active  : status aktif akun
      - birth_date : tanggal lahir (format: YYYY-MM-DD)
      - gender     : jenis kelamin ('male' atau 'female')

    Catatan: pada Fase 7, akan ditambahkan validasi bahwa
    current_user hanya bisa update profil dirinya sendiri atau anaknya.
    """
    update_data = user_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak ada data untuk diupdate"
        )

    # Konversi Gender enum ke string value agar bisa diserialisasi ke JSON
    if "gender" in update_data and isinstance(update_data["gender"], Gender):
        update_data["gender"] = update_data["gender"].value

    # Konversi date ke ISO string agar PostgreSQL bisa terima
    if "birth_date" in update_data and update_data["birth_date"] is not None:
        update_data["birth_date"] = str(update_data["birth_date"])

    client = get_supabase_service_client()
    try:
        response = (
            client.table("users")
            .update(update_data)
            .eq("id", str(user_id))
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
