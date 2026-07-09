from typing import Any, Dict, Optional, cast
from uuid import UUID

from fastapi import HTTPException, status

from app.core.supabase import get_supabase_service_client
from app.models.database import compute_pet_status


class GamificationService:
    """
    Service untuk mengatur Rule Engine Gamifikasi.
    Mengubah aksi medis anak (makan, obat) menjadi EXP dan Status Pet.
    """

    def __init__(self) -> None:
        pass

    def evaluate_food_compliance(self, child_id: UUID, total_calories: float) -> Dict[str, Any]:
        """
        Mengevaluasi nutrisi makanan dan menghitung reward/penalty untuk Virtual Pet.
        Mengambil target harian dari tabel clinical_parameters.
        """
        client = get_supabase_service_client()
        target_calories_per_meal = 500  # Fallback
        
        try:
            # Mengambil parameter klinis terbaru untuk anak ini
            cp_response = client.table("clinical_parameters") \
                .select("target_daily_calories") \
                .eq("child_id", str(child_id)) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
                
            if cp_response.data and cp_response.data[0].get("target_daily_calories"):
                # Asumsi 3 kali makan besar sehari
                target_daily = cp_response.data[0]["target_daily_calories"]
                target_calories_per_meal = target_daily / 3
        except Exception:
            pass # Abaikan error, gunakan nilai fallback 500 kalori

        # Rule Engine
        # Kita beri toleransi 15% dari target per meal
        if total_calories <= (target_calories_per_meal * 1.15):
            exp_delta = 10
            happiness_delta = 10
            hunger_delta = 20
        else:
            exp_delta = 5
            happiness_delta = -10
            hunger_delta = 20

        return self.update_pet_status(child_id, exp_delta, happiness_delta, hunger_delta)

    def evaluate_medicine_compliance(self, child_id: UUID) -> Dict[str, Any]:
        """
        Mengevaluasi kepatuhan minum/suntik obat.
        """
        exp_delta = 20
        happiness_delta = 15
        hunger_delta = 0  # Obat tidak mengenyangkan

        return self.update_pet_status(child_id, exp_delta, happiness_delta, hunger_delta)

    def update_pet_status(
        self, child_id: UUID, exp_delta: int, happiness_delta: int, hunger_delta: int
    ) -> Dict[str, Any]:
        """
        Memperbarui status Virtual Pet di database, menerapkan batasan 0-100, 
        serta menghitung Level Up (100 EXP = 1 Level).
        """
        client = get_supabase_service_client()
        
        try:
            response = client.table("virtual_pets").select("*").eq("child_id", str(child_id)).execute()
            if not response.data:
                return {
                    "exp_gained": 0,
                    "level_up": False,
                    "new_level": 1,
                    "new_happiness": 100,
                    "new_hunger": 100,
                    "current_status": "neutral"
                }
            
            pet = cast(Dict[str, Any], response.data[0])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal mengambil data Virtual Pet: {str(e)}",
            )

        current_exp = pet["experience_points"]
        current_level = pet["level"]
        current_happiness = pet["happiness"]
        current_hunger = pet["hunger"]

        new_exp = current_exp + exp_delta
        
        level_up = False
        if new_exp >= 100:
            levels_gained = new_exp // 100
            current_level += levels_gained
            new_exp = new_exp % 100
            level_up = True

        new_happiness = max(0, min(100, current_happiness + happiness_delta))
        new_hunger = max(0, min(100, current_hunger + hunger_delta))

        new_status = compute_pet_status(new_happiness, new_hunger).value

        update_data = {
            "experience_points": new_exp,
            "level": current_level,
            "happiness": new_happiness,
            "hunger": new_hunger,
            "is_active": True
        }

        try:
            client.table("virtual_pets").update(update_data).eq("id", pet["id"]).execute()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal memperbarui status Virtual Pet: {str(e)}",
            )

        return {
            "exp_gained": exp_delta,
            "level_up": level_up,
            "new_level": current_level,
            "new_happiness": new_happiness,
            "new_hunger": new_hunger,
            "current_status": new_status,
        }
