import asyncio
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.models.database import MealType
from app.services.ai_service import AIService
from app.services.gamification_service import GamificationService
from app.services.log_service import LogService
from app.services.reasoning_service import ReasoningService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/scan", tags=["scan"])

# Instantiate services
storage_service = StorageService()
ai_service = AIService()
reasoning_service = ReasoningService()
gamification_service = GamificationService()
log_service = LogService()

def _validate_file(file: UploadFile) -> None:
    """Helper untuk memvalidasi file unggahan."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File tidak ditemukan"
        )

@router.post("/food")
async def scan_food(
    child_id: UUID = Form(...),
    logged_by: UUID = Form(...),
    meal_type: MealType = Form(...),
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
) -> dict:
    """
    Endpoint untuk mendeteksi makanan dari gambar.
    Menerapkan proses unggah gambar dan inferensi AI secara paralel (Concurrency).
    """
    _validate_file(file)
    file_bytes = await file.read()

    # Parallel Processing (I/O Bound)
    try:
        upload_task = storage_service.upload_image(
            file_bytes=file_bytes, filename=file.filename, bucket_name="food-photos"
        )
        ai_task = ai_service.detect_food(image_bytes=file_bytes)

        public_url, detected_foods = await asyncio.gather(upload_task, ai_task)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan saat memproses gambar: {str(e)}",
        )

    # Multimodal Reasoning
    nutrition_data = reasoning_service.estimate_nutrition(detected_foods)

    # Simpan ke Database
    db_record = log_service.create_food_log(
        child_id=child_id,
        logged_by=logged_by,
        meal_type=meal_type,
        nutrition_data=nutrition_data,
        public_url=public_url,
        notes=notes
    )

    # Gamification
    total_calories = int(nutrition_data["total_calories"])
    pet_status_update = gamification_service.evaluate_food_compliance(
        child_id=child_id, total_calories=total_calories
    )

    return {
        "status": "success",
        "message": "Makanan berhasil dideteksi dan dicatat",
        "data": {
            "foods_detected": nutrition_data["foods_detected"],
            "total_calories": total_calories,
            "total_carbs": nutrition_data["total_carbs"],
            "photo_url": public_url,
            "pet_status_update": pet_status_update,
            "database_record": db_record,
        },
    }


@router.post("/medicine")
async def scan_medicine(
    child_id: UUID = Form(...),
    administered_by: UUID = Form(...),
    dosage: float = Form(..., gt=0, description="Dosis obat wajib diisi manual demi keamanan"),
    dosage_unit: str = Form(..., description="Satuan dosis, misal: 'IU' untuk insulin"),
    file: UploadFile = File(...),
    route: str = Form("subcutaneous", description="Rute pemberian (oral, subcutaneous, dll)"),
    notes: Optional[str] = Form(None),
) -> dict:
    """
    Endpoint untuk memindai obat/insulin pen.
    AI hanya mendeteksi JENIS obat. Dosis WAJIB diisi manual oleh pengguna.
    Menggunakan asyncio.gather untuk upload dan inferensi paralel.
    """
    _validate_file(file)
    file_bytes = await file.read()

    # Parallel Processing
    try:
        upload_task = storage_service.upload_image(
            file_bytes=file_bytes, filename=file.filename, bucket_name="medicine-photos"
        )
        ai_task = ai_service.detect_medicine(image_bytes=file_bytes)

        public_url, detected_medicine = await asyncio.gather(upload_task, ai_task)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan saat memproses gambar obat: {str(e)}",
        )

    # Simpan ke Database
    db_record = log_service.create_medication_log(
        child_id=child_id,
        administered_by=administered_by,
        detected_medicine=detected_medicine,
        dosage=dosage,
        dosage_unit=dosage_unit,
        route=route,
        public_url=public_url,
        notes=notes
    )

    # Gamification
    pet_status_update = gamification_service.evaluate_medicine_compliance(child_id=child_id)

    return {
        "status": "success",
        "message": "Obat berhasil dideteksi dan dicatat",
        "data": {
            "medication_detected": detected_medicine,
            "dosage_recorded": f"{dosage} {dosage_unit}",
            "photo_url": public_url,
            "pet_status_update": pet_status_update,
            "database_record": db_record,
        },
    }
