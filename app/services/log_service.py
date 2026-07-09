import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.core.supabase import get_supabase_service_client
from app.models.database import FoodLogCreate, MealType, MedicationLogCreate

logger = logging.getLogger(__name__)

class LogService:
    """Service untuk menangani penyimpanan catatan makanan dan obat ke database."""

    def __init__(self) -> None:
        pass

    def create_food_log(
        self,
        child_id: UUID,
        logged_by: UUID,
        meal_type: MealType,
        nutrition_data: Dict[str, Any],
        public_url: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        food_name_str = ", ".join(nutrition_data["foods_detected"])
        total_calories = int(nutrition_data["total_calories"])
        is_healthy = nutrition_data.get("is_healthy", True)

        log_data = FoodLogCreate(
            child_id=child_id,
            logged_by=logged_by,
            meal_type=meal_type,
            food_name=food_name_str,
            calories=total_calories,
            photo_url=public_url,
            is_healthy=is_healthy,
            notes=notes,
            consumed_at=datetime.now(timezone.utc),
        )

        client = get_supabase_service_client()
        try:
            result = client.table("food_logs").insert(log_data.model_dump(mode="json")).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Gagal menyimpan data makanan: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menyimpan data makanan ke database: {str(e)}",
            )

    def create_medication_log(
        self,
        child_id: UUID,
        administered_by: UUID,
        detected_medicine: str,
        dosage: float,
        dosage_unit: str,
        route: str,
        public_url: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
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
            final_notes = f"[Photo URL: {public_url}] {notes if notes else ''}".strip()
            db_log_data = log_data.model_dump(mode="json")
            db_log_data["notes"] = final_notes

            result = client.table("medication_logs").insert(db_log_data).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Gagal menyimpan data obat: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menyimpan data obat ke database: {str(e)}",
            )
