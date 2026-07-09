import logging
from datetime import datetime, timezone
from typing import Any, Dict, cast

from app.core.supabase import get_supabase_service_client
from app.services.gamification_service import GamificationService

logger = logging.getLogger(__name__)

def check_daily_compliance() -> None:
    """
    Pekerja Latar Belakang (Background Worker).
    Tugas:
    1. Mengevaluasi jadwal makan (Custom Meal Schedules). Jika waktu (end_time) sudah terlewat 
       tanpa adanya catatan makan (food_logs) untuk meal_type tersebut, terapkan penalty.
    2. Mengevaluasi catatan obat harian.
    """
    logger.info("[Compliance Worker] Memulai pengecekan kepatuhan medis dan makanan...")
    
    client = get_supabase_service_client()
    gamification = GamificationService()
    
    try:
        pets_response = client.table("virtual_pets").select("*").execute()
        pets = pets_response.data
        if not pets:
            return

        now = datetime.now(timezone.utc)
        today_date = now.date()
        today_start_iso = datetime(today_date.year, today_date.month, today_date.day, tzinfo=timezone.utc).isoformat()
        current_time_str = now.time().isoformat()
        # ISO day_of_week: Monday is 0, Sunday is 6
        day_of_week = today_date.weekday() 

        for item in pets:
            pet = cast(Dict[str, Any], item)
            child_id = pet.get("child_id")
            if not child_id:
                continue
                
            # --- 1. Evaluasi Kepatuhan Obat (Medication) ---
            # (Untuk prototype, kita masih mengecek apakah ada log obat hari ini. Pada produksi,
            # sebaiknya obat juga menggunakan tabel jadwal khusus).
            logs_response = client.table("medication_logs").select("*") \
                .eq("child_id", child_id) \
                .gte("created_at", today_start_iso) \
                .execute()
                
            if len(logs_response.data) == 0:
                logger.info(f"[Compliance Worker] Anak {child_id} belum minum obat hari ini! Penalty obat diterapkan.")
                try:
                    gamification.update_pet_status(child_id=child_id, exp_delta=0, happiness_delta=-10, hunger_delta=0)
                except Exception as e:
                    logger.error(f"Gagal memberi penalty obat untuk {child_id}: {str(e)}")

            # --- 2. Evaluasi Kepatuhan Makan Berdasarkan Jadwal ---
            # Cari jadwal makan hari ini yang WAKTU BERAKHIRNYA (end_time) sudah terlewat
            schedules_response = client.table("custom_meal_schedules").select("*") \
                .eq("child_id", child_id) \
                .eq("day_of_week", day_of_week) \
                .eq("is_active", True) \
                .lte("end_time", current_time_str) \
                .execute()

            for schedule in schedules_response.data:
                # Cek apakah ada food_log untuk meal_type ini hari ini
                food_logs_resp = client.table("food_logs").select("*") \
                    .eq("child_id", child_id) \
                    .eq("meal_type", schedule["meal_type"]) \
                    .gte("consumed_at", today_start_iso) \
                    .execute()
                
                if len(food_logs_resp.data) == 0:
                    logger.info(f"[Compliance Worker] Anak {child_id} melewatkan jadwal {schedule['meal_name']}! Penalty diterapkan.")
                    try:
                        gamification.update_pet_status(child_id=child_id, exp_delta=0, happiness_delta=-15, hunger_delta=30)
                    except Exception as e:
                        logger.error(f"Gagal memberi penalty makan untuk {child_id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"[Compliance Worker] Terjadi kesalahan saat mengecek data: {str(e)}")
        
    logger.info("[Compliance Worker] Pengecekan selesai.")
