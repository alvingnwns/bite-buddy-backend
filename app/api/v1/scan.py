import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.supabase import get_supabase_client
from app.models.database import FoodLogCreate, MealType
from app.services.ai_service import AIService
from app.services.reasoning_service import ReasoningService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/scan", tags=["scan"])

# Instantiate services
storage_service = StorageService()
ai_service = AIService()
reasoning_service = ReasoningService()


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
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File tidak ditemukan"
        )

    # 1. Baca byte dari file gambar
    file_bytes = await file.read()

    # 2. Parallel Processing (Mempercepat response time)
    # Task A: Upload ke Supabase Storage
    # Task B: Analisis gambar dengan AI (Hugging Face)
    try:
        # Menjalankan kedua I/O bound task secara bersamaan
        upload_task = storage_service.upload_image(
            file_bytes=file_bytes, filename=file.filename, bucket_name="food-photos"
        )
        ai_task = ai_service.detect_food(image_bytes=file_bytes)

        # Tunggu sampai kedua task selesai
        public_url, detected_foods = await asyncio.gather(upload_task, ai_task)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan saat memproses gambar: {str(e)}",
        )

    # 3. Multimodal Reasoning (Estimasi Nutrisi)
    nutrition_data = reasoning_service.estimate_nutrition(detected_foods)

    # 4. Simpan ke Database (Tabel food_logs)
    food_name_str = ", ".join(nutrition_data["foods_detected"])
    total_calories = int(nutrition_data["total_calories"])

    log_data = FoodLogCreate(
        child_id=child_id,
        logged_by=logged_by,
        meal_type=meal_type,
        food_name=food_name_str,
        calories=total_calories,
        photo_url=public_url,
        notes=notes,
        consumed_at=datetime.utcnow(),
    )

    client = get_supabase_client()
    try:
        # Lakukan proses sinkronous ke database. 
        # Untuk optimisasi ekstrem, bisa dibuat async dengan supabase-js wrapper,
        # namun supabase-py saat ini berjalan secara synchronous.
        result = client.table("food_logs").insert(log_data.model_dump(mode="json")).execute()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menyimpan data makanan ke database: {str(e)}",
        )

    # 5. Return Response
    return {
        "status": "success",
        "message": "Makanan berhasil dideteksi dan dicatat",
        "data": {
            "foods_detected": nutrition_data["foods_detected"],
            "total_calories": total_calories,
            "total_carbs": nutrition_data["total_carbs"],
            "photo_url": public_url,
            "database_record": result.data[0] if result.data else None,
        },
    }

