import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.supabase import get_supabase_service_client
from app.models.database import FoodLogCreate, MealType
from app.services.ai_service import AIService
from app.services.gamification_service import GamificationService
from app.services.reasoning_service import ReasoningService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/scan", tags=["scan"])

# Instantiate services
storage_service = StorageService()
ai_service = AIService()
reasoning_service = ReasoningService()
gamification_service = GamificationService()


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
        consumed_at=datetime.now(timezone.utc),
    )

    client = get_supabase_service_client()
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

    # 5. Gamification: Update status Virtual Pet berdasarkan makanan
    pet_status_update = gamification_service.evaluate_food_compliance(
        child_id=child_id, total_calories=total_calories
    )

    # 6. Return Response
    return {
        "status": "success",
        "message": "Makanan berhasil dideteksi dan dicatat",
        "data": {
            "foods_detected": nutrition_data["foods_detected"],
            "total_calories": total_calories,
            "total_carbs": nutrition_data["total_carbs"],
            "photo_url": public_url,
            "pet_status_update": pet_status_update,
            "database_record": result.data[0] if result.data else None,
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
    AI hanya bertugas mendeteksi JENIS obat. Dosis WAJIB diisi manual oleh pengguna.
    Menggunakan asyncio.gather untuk upload dan inferensi paralel.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File tidak ditemukan"
        )

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

    # Simpan ke Database (Tabel medication_logs)
    from app.models.database import MedicationLogCreate
    from datetime import time

    # Untuk prototipe, kita asumsikan scheduled_time adalah jam saat ini
    current_time = datetime.now(timezone.utc).time()

    log_data = MedicationLogCreate(
        child_id=child_id,
        administered_by=administered_by,
        medication_name=detected_medicine,
        dosage=dosage,
        dosage_unit=dosage_unit,
        route=route,
        scheduled_time=current_time,
        was_taken=True,
        notes=notes,
    )

    client = get_supabase_service_client()
    try:
        # Menyisipkan catatan obat, tapi di skema tabel kita tidak ada photo_url di medication_logs
        # Jika butuh menyimpan foto, kita bisa simpan public_url di 'notes' untuk sementara
        # atau merubah skema DB nanti.
        final_notes = f"[Photo URL: {public_url}] {notes if notes else ''}".strip()
        db_log_data = log_data.model_dump(mode="json")
        db_log_data["notes"] = final_notes

        result = client.table("medication_logs").insert(db_log_data).execute()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menyimpan data obat ke database: {str(e)}",
        )

    # Gamification: Update status Virtual Pet berdasarkan obat
    pet_status_update = gamification_service.evaluate_medicine_compliance(child_id=child_id)

    return {
        "status": "success",
        "message": "Obat berhasil dideteksi dan dicatat",
        "data": {
            "medication_detected": detected_medicine,
            "dosage_recorded": f"{dosage} {dosage_unit}",
            "photo_url": public_url,
            "pet_status_update": pet_status_update,
            "database_record": result.data[0] if result.data else None,
        },
    }

