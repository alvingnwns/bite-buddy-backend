"""API endpoints untuk manajemen parameter klinis anak.

Dokter menggunakan endpoint ini untuk:
- Menyimpan hasil pengukuran fisik (BB, TB) dan parameter medis
- Melihat riwayat parameter klinis
- Preview kalkulasi kalori sebelum menyimpan
- Override target kalori yang dihitung otomatis

Semua kalkulasi kalori/karbo/max sugar dilakukan oleh ClinicalService,
bukan di endpoint ini langsung (separation of concerns).
"""

from datetime import date
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.supabase import get_supabase_service_client
from app.models.database import (
    ClinicalParameter,
    ClinicalParameterCreate,
    ClinicalParameterUpdate,
    DiabetesType,
    Gender,
)
from app.services.clinical_service import ClinicalService

router = APIRouter()

# Satu instance service, dipakai oleh semua endpoint di file ini
_clinical_service = ClinicalService()


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_clinical_parameter(params: ClinicalParameterCreate) -> Any:
    """Simpan parameter klinis baru hasil pemeriksaan dokter.

    Sistem akan otomatis menghitung target_daily_calories dan target_daily_carbs
    menggunakan formula WHO Pediatric jika:
      1. Data anak (birth_date, gender) tersedia di tabel users, DAN
      2. Dokter tidak mengisi target_daily_calories secara manual

    Jika dokter mengisi target_daily_calories, nilai manual tersebut dipakai.

    max_sugar_intake_g juga otomatis direkomendasikan dari diabetes_type
    jika tidak diisi manual.
    """
    try:
        # Ambil data profil anak untuk auto-calculation
        child_profile = _clinical_service.get_child_profile(params.child_id)

        birth_date = None
        gender = None

        if child_profile:
            # Parse birth_date string ke objek date jika ada
            if child_profile.get("birth_date"):
                birth_date = date.fromisoformat(child_profile["birth_date"])
            # Parse gender string ke enum Gender jika ada
            if child_profile.get("gender"):
                try:
                    gender = Gender(child_profile["gender"])
                except ValueError:
                    pass  # Abaikan jika nilai gender tidak dikenal

        result = _clinical_service.create_clinical_record(
            params=params,
            birth_date=birth_date,
            gender=gender,
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menyimpan parameter klinis: {str(e)}"
        )


@router.get("/preview", response_model=Dict[str, Any])
def preview_calorie_calculation(
    weight_kg: float,
    height_cm: float,
    birth_date: date,
    gender: Gender,
    diabetes_type: DiabetesType = DiabetesType.type1,
) -> Any:
    """Preview kalkulasi target kalori/karbo/max sugar TANPA menyimpan ke DB.

    Berguna untuk dokter melihat estimasi sebelum mengisi form parameter klinis.

    Contoh request:
      GET /clinical/preview?weight_kg=35&height_cm=140&birth_date=2015-03-15
           &gender=male&diabetes_type=type1

    Returns:
      target_daily_calories, target_daily_carbs, recommended_max_sugar_g,
      age_years_at_calculation, bmr_kcal
    """
    try:
        return _clinical_service.preview_calculation(
            weight_kg=weight_kg,
            height_cm=height_cm,
            birth_date=birth_date,
            gender=gender,
            diabetes_type=diabetes_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{child_id}", response_model=List[Dict[str, Any]])
def get_clinical_history(
    child_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> Any:
    """Ambil riwayat parameter klinis untuk seorang anak (dengan pagination).

    Diurutkan dari yang paling baru (created_at descending).
    """
    client = get_supabase_service_client()
    try:
        start = offset
        end = offset + limit - 1

        response = (
            client.table("clinical_parameters")
            .select("*")
            .eq("child_id", str(child_id))
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


@router.get("/{child_id}/latest", response_model=Dict[str, Any])
def get_latest_clinical_parameters(child_id: UUID) -> Any:
    """Ambil parameter klinis yang paling baru untuk seorang anak.

    Dipakai oleh GamificationService untuk mengetahui target_daily_calories
    saat mengevaluasi makanan.
    """
    client = get_supabase_service_client()
    try:
        response = (
            client.table("clinical_parameters")
            .select("*")
            .eq("child_id", str(child_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data klinis tidak ditemukan untuk anak ini"
            )
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/{clinical_id}", response_model=Dict[str, Any])
def update_clinical_parameters(
    clinical_id: UUID,
    update_data: ClinicalParameterUpdate,
) -> Any:
    """Update parameter klinis yang sudah ada (dokter override nilai otomatis).

    Dokter dapat menggunakan endpoint ini untuk:
    - Override target_daily_calories yang dihitung otomatis
    - Update max_sugar_intake_g sesuai kondisi klinis spesifik pasien
    - Update data pengukuran terbaru (BB, TB)
    """
    client = get_supabase_service_client()
    try:
        data = update_data.model_dump(exclude_unset=True)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tidak ada data untuk diupdate"
            )

        # Konversi enum ke value string
        if "diabetes_type" in data and hasattr(data["diabetes_type"], "value"):
            data["diabetes_type"] = data["diabetes_type"].value

        response = (
            client.table("clinical_parameters")
            .update(data)
            .eq("id", str(clinical_id))
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data klinis tidak ditemukan"
            )
        return response.data[0]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
