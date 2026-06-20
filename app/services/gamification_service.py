from typing import Dict, Optional, Any
from uuid import UUID

from fastapi import HTTPException, status

from app.core.supabase import get_supabase_client
from app.models.database import compute_pet_status


class GamificationService:
    """
    Service untuk mengatur Rule Engine Gamifikasi.
    Mengubah aksi medis anak (makan, obat) menjadi EXP dan Status Pet.
    """

    def __init__(self) -> None:
        pass

    def evaluate_food_compliance(self, child_id: UUID, total_calories: float) -> Dict[str, int]:
        """
        Mengevaluasi nutrisi makanan dan menghitung reward/penalty untuk Virtual Pet.
        
        Rule Engine (Prototipe):
        - Kalori <= 500 (Diasumsikan makanan sehat/terkontrol): +10 EXP, +10 Happiness, +20 Hunger
        - Kalori > 500 (Junk food/Over kalori): +5 EXP, -10 Happiness, +20 Hunger
        
        (Pada produksi, ini akan merujuk ke ClinicalParameter milik child_id).
        """
        if total_calories <= 500:
            exp_delta = 10
            happiness_delta = 10
            hunger_delta = 20
        else:
            exp_delta = 5
            happiness_delta = -10
            hunger_delta = 20

        return self.update_pet_status(child_id, exp_delta, happiness_delta, hunger_delta)

    def evaluate_medicine_compliance(self, child_id: UUID) -> Dict[str, int]:
        """
        Mengevaluasi kepatuhan minum/suntik obat.
        
        Rule Engine:
        - Suntik Insulin / Minum Obat: +20 EXP, +15 Happiness
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
        client = get_supabase_client()
        
        # 1. Ambil data Virtual Pet saat ini
        try:
            response = client.table("virtual_pets").select("*").eq("child_id", str(child_id)).execute()
            if not response.data:
                # Jika anak belum punya pet, kembalikan delta default sebagai info log
                return {
                    "exp_gained": 0,
                    "level_up": False,
                    "new_level": 1,
                    "new_happiness": 100,
                    "new_hunger": 100,
                    "current_status": "neutral"
                }
            
            pet = response.data[0]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal mengambil data Virtual Pet: {str(e)}",
            )

        # 2. Kalkulasi nilai baru
        current_exp = pet["experience_points"]
        current_level = pet["level"]
        current_happiness = pet["happiness"]
        current_hunger = pet["hunger"]

        new_exp = current_exp + exp_delta
        
        # Cek Level Up (Setiap kelipatan 100 EXP = Level Naik)
        level_up = False
        if new_exp >= 100:
            levels_gained = new_exp // 100
            current_level += levels_gained
            new_exp = new_exp % 100  # Sisa EXP setelah naik level
            level_up = True

        # Terapkan batasan Min/Max (0-100) untuk Happiness dan Hunger
        new_happiness = max(0, min(100, current_happiness + happiness_delta))
        new_hunger = max(0, min(100, current_hunger + hunger_delta))

        # Re-compute status keseluruhan (happy, sad, sick, dsb)
        new_status = compute_pet_status(new_happiness, new_hunger).value

        # 3. Update ke Database
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
