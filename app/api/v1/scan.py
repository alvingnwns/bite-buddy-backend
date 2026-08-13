import asyncio
from typing import Optional, List, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status, Body
from pydantic import Field
from app.models.base import CamelModel

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

# Model untuk endpoint confirm
class ConfirmedIngredient(CamelModel):
    ingredient: str = Field(description="Nama bahan makanan asli dari AI")
    description: str = Field(description="Deskripsi dari FoodData Central")
    weight_g: float = Field(description="Berat dalam gram", gt=0)
    fdcId: Optional[int] = Field(None, description="FoodData Central ID")

class ConfirmFoodRequest(CamelModel):
    child_id: UUID
    logged_by: UUID
    meal_type: MealType
    public_url: str = Field(description="URL gambar yang telah diupload")
    notes: Optional[str] = None
    ingredients: List[ConfirmedIngredient] = Field(description="Daftar bahan makanan yang telah dikonfirmasi oleh user")

@router.post("/food/analyze")
async def analyze_food(
    file: UploadFile = File(...),
) -> dict:
    """
    Step 1: Endpoint untuk mendeteksi bahan makanan dari gambar.
    Menerapkan proses unggah gambar dan inferensi AI secara paralel.
    Tidak menyimpan ke database, state disimpan di frontend.
    """
    _validate_file(file)
    file_bytes = await file.read()

    # Parallel Processing (I/O Bound)
    try:
        upload_task = storage_service.upload_image(
            file_bytes=file_bytes, filename=file.filename, bucket_name="food-photos"
        )
        # Deteksi bahan makanan menggunakan Gemini
        ai_task = ai_service.detect_food_ingredients(image_bytes=file_bytes, mime_type=file.content_type or "image/jpeg")

        public_url, detection = await asyncio.gather(upload_task, ai_task)
        is_food, food_name, detected_ingredients = detection
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan saat memproses gambar: {str(e)}",
        )

    return {
        "status": "success",
        "message": "Analisis gambar selesai. Silakan konfirmasi bahan dan berat makanan.",
        "data": {
            "photo_url": public_url,
            "is_food": is_food,
            "food_name": food_name,
            "ingredients": detected_ingredients
        }
    }

@router.post("/food/confirm")
async def confirm_food(
    request: ConfirmFoodRequest = Body(...)
) -> dict:
    """
    Step 2: Endpoint untuk memproses bahan makanan yang sudah dikonfirmasi (berat/gram).
    Melakukan kalkulasi kalori/makro, evaluasi kesehatan via Gemini, lalu menyimpan log.
    """
    if not request.ingredients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Daftar bahan makanan tidak boleh kosong."
        )

    # Convert Pydantic models to dicts for the service
    ingredients_list = [item.model_dump() for item in request.ingredients]

    # Multimodal Reasoning (Menghitung Total + AI Evaluasi Kesehatan)
    nutrition_data = await reasoning_service.process_confirmed_meal(ingredients_list)

    # Simpan ke Database
    db_record = log_service.create_food_log(
        child_id=request.child_id,
        logged_by=request.logged_by,
        meal_type=request.meal_type,
        nutrition_data=nutrition_data,
        public_url=request.public_url,
        notes=request.notes
    )

    # Gamification
    total_calories = int(nutrition_data["total_calories"])
    is_healthy = nutrition_data.get("is_healthy", True)
    pet_status_update = gamification_service.evaluate_food_compliance(
        child_id=request.child_id, total_calories=total_calories, is_healthy=is_healthy
    )

    return {
        "status": "success",
        "message": "Makanan berhasil dikonfirmasi dan dicatat",
        "data": {
            "nutrition_evaluation": nutrition_data,
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
        ai_task = ai_service.detect_medicine(image_bytes=file_bytes, mime_type=file.content_type or "image/jpeg")

        public_url, detected_medicine = await asyncio.gather(upload_task, ai_task)
    except HTTPException as he:
        raise he
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
