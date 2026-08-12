"""GamificationService — Rule Engine untuk gamifikasi virtual pet.

Mengubah aksi medis anak (makan, minum obat) menjadi perubahan pada
stats Virtual Pet (EXP, Happiness, Hunger).

CATATAN SEMANTIK HUNGER (updated 2026-08-10):
  hunger TINGGI = makin KENYANG (++hunger = makin kenyang)
  hunger RENDAH = makin LAPAR

  Implikasi pada rule engine:
    - Setelah makan sehat → hunger += 30 (lebih kenyang) ✅
    - Setelah makan berlebih → hunger += 20 (kenyang tapi kebanyakan) ✅
    - Setelah makan junk food → hunger += 20 (kenyang tapi tidak sehat) ✅
    - Lewat jadwal makan (penalty) → hunger -= 30 (makin lapar) ✅ [DIUBAH dari +30]
"""

from typing import Any, Dict, cast
from uuid import UUID

from fastapi import HTTPException, status

from app.core.supabase import get_supabase_service_client
from app.models.database import AlertType, compute_pet_status
from app.services.alert_service import create_alert


class GamificationService:
    """Service untuk mengatur Rule Engine Gamifikasi.

    Mengubah aksi medis anak (makan, obat) menjadi EXP dan Status Pet.
    Semua delta nilai (EXP, Happiness, Hunger) berdasarkan tabel gamifikasi
    di implementation_plan.md.
    """

    def __init__(self) -> None:
        pass

    def evaluate_food_compliance(
        self,
        child_id: UUID,
        total_calories: float,
        is_healthy: bool = True,
    ) -> Dict[str, Any]:
        """Evaluasi nutrisi makanan dan hitung reward/penalty Virtual Pet.

        Mengambil target kalori per meal dari tabel clinical_parameters.
        target_per_meal = target_daily_calories / 3 (asumsi 3 makan besar)

        Rule Engine:
          - Junk food         : EXP 0, Happiness -20, Hunger +20
          - Sehat + kalori ≤ target×1.15: EXP +15, Happiness +15, Hunger +30
          - Sehat + kalori > target×1.15: EXP +5, Happiness -5, Hunger +20

        Args:
            child_id: UUID anak
            total_calories: Total kalori makanan yang terdeteksi
            is_healthy: False jika terdeteksi sebagai junk food
        """
        client = get_supabase_service_client()
        # Fallback jika tidak ada data klinis: 500 kcal per meal
        target_calories_per_meal = 500

        try:
            cp_response = (
                client.table("clinical_parameters")
                .select("target_daily_calories")
                .eq("child_id", str(child_id))
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if cp_response.data and cp_response.data[0].get("target_daily_calories"):
                target_daily = cp_response.data[0]["target_daily_calories"]
                target_calories_per_meal = target_daily / 3
        except Exception:
            # Non-fatal: gunakan fallback 500 kcal
            pass

        # Rule Engine
        if not is_healthy:
            # Junk food: pet sedih tapi masih kenyang
            exp_delta = 0
            happiness_delta = -20
            hunger_delta = 20   # kenyang, tapi dari makanan tidak sehat
            create_alert(
                child_id,
                AlertType.food_warning,
                "Waduh, makanan ini kurang sehat! Peliharaanmu jadi sedih dan sakit.",
            )
        elif total_calories <= (target_calories_per_meal * 1.15):
            # Makan sehat & kalori sesuai target (grace 15%)
            exp_delta = 15
            happiness_delta = 15
            hunger_delta = 30   # kenyang penuh
        else:
            # Makan sehat tapi kalori berlebih
            exp_delta = 5
            happiness_delta = -5
            hunger_delta = 20   # kenyang tapi kebanyakan

        return self.update_pet_status(child_id, exp_delta, happiness_delta, hunger_delta)

    def evaluate_medicine_compliance(self, child_id: UUID) -> Dict[str, Any]:
        """Evaluasi kepatuhan minum/suntik obat.

        Minum obat = reward terbesar karena sangat penting untuk T1DM.
        Obat tidak mempengaruhi hunger (tidak mengenyangkan).
        """
        exp_delta = 20
        happiness_delta = 15
        hunger_delta = 0    # obat tidak mengenyangkan

        return self.update_pet_status(child_id, exp_delta, happiness_delta, hunger_delta)

    def apply_missed_meal_penalty(self, child_id: UUID) -> Dict[str, Any]:
        """Terapkan penalty karena melewatkan jadwal makan.

        Dipanggil oleh compliance_worker saat end_time jadwal sudah lewat
        dan tidak ada food_log yang tercatat (sekali per jadwal per hari).

        Hunger turun karena pet makin lapar (tidak makan).
        """
        exp_delta = 0
        happiness_delta = -15
        hunger_delta = -30  # makin lapar karena tidak makan (hunger TURUN)

        create_alert(
            child_id,
            AlertType.compliance_violation,
            "Kamu melewatkan waktu makan! Jangan lupa makan ya, peliharaanmu jadi lapar 😢",
        )

        return self.update_pet_status(child_id, exp_delta, happiness_delta, hunger_delta)

    def apply_missed_medicine_penalty(self, child_id: UUID) -> Dict[str, Any]:
        """Terapkan penalty karena lupa minum/suntik obat.

        Dipanggil oleh compliance_worker (sekali per hari per jadwal obat).
        Hunger tidak berubah karena obat tidak mempengaruhi kenyang.
        """
        exp_delta = 0
        happiness_delta = -10
        hunger_delta = 0

        create_alert(
            child_id,
            AlertType.compliance_violation,
            "Jangan lupa minum obat! Kesehatanmu dan peliharaanmu bergantung padanya 💊",
        )

        return self.update_pet_status(child_id, exp_delta, happiness_delta, hunger_delta)

    def update_pet_status(
        self,
        child_id: UUID,
        exp_delta: int,
        happiness_delta: int,
        hunger_delta: int,
    ) -> Dict[str, Any]:
        """Update stats Virtual Pet di database dan hitung ulang status.

        Memastikan semua nilai berada dalam batas 0–100 (clamp).
        Menghitung level-up jika EXP mencapai 100 (carry-over sisa EXP).

        Catatan: Level system saat ini tetap menghitung EXP namun
        TIDAK mengubah level (defer ke future feature per revisi 2026-08-10).

        Args:
            child_id: UUID anak pemilik pet
            exp_delta: Perubahan EXP (bisa negatif, meski jarang)
            happiness_delta: Perubahan happiness (-100 s.d. +100)
            hunger_delta: Perubahan hunger (+ = makin kenyang, - = makin lapar)
        """
        client = get_supabase_service_client()

        try:
            response = (
                client.table("virtual_pets")
                .select("*")
                .eq("child_id", str(child_id))
                .execute()
            )
            if not response.data:
                # Pet belum dibuat — buat pet default terlebih dahulu
                default_pet = {
                    "child_id": str(child_id),
                    "pet_name": "Buddy",
                    "pet_type": "dog"
                }
                insert_resp = client.table("virtual_pets").insert(default_pet).execute()
                if not insert_resp.data:
                    raise HTTPException(status_code=500, detail="Gagal membuat peliharaan otomatis")
                pet = cast(Dict[str, Any], insert_resp.data[0])
            else:
                pet = cast(Dict[str, Any], response.data[0])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal mengambil/membuat data Virtual Pet: {str(e)}",
            )

        current_exp = pet["experience_points"]
        current_level = pet["level"]
        current_happiness = pet["happiness"]
        current_hunger = pet["hunger"]

        # Hitung EXP baru
        new_exp = current_exp + exp_delta

        # Level Up check (defer: EXP dihitung tapi level tidak naik otomatis)
        # Ini adalah placeholder — akan diaktifkan pada future feature Level System
        level_up = False
        if new_exp >= 100:
            levels_gained = new_exp // 100
            current_level += levels_gained
            new_exp = new_exp % 100
            level_up = True

            create_alert(
                child_id,
                AlertType.level_up,
                f"Hore! Peliharaanmu naik ke level {current_level}! 🎉",
            )

        # Clamp happiness dan hunger ke range 0–100
        new_happiness = max(0, min(100, current_happiness + happiness_delta))
        new_hunger = max(0, min(100, current_hunger + hunger_delta))

        # Hitung status baru berdasarkan nilai happiness dan hunger
        new_status = compute_pet_status(new_happiness, new_hunger).value

        update_data = {
            "experience_points": new_exp,
            "level": current_level,
            "happiness": new_happiness,
            "hunger": new_hunger,
            "is_active": True,
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
