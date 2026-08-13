import logging
from datetime import datetime, timezone
from typing import Any, Dict, cast
from zoneinfo import ZoneInfo

from app.core.supabase import get_supabase_service_client
from app.services.gamification_service import GamificationService
from app.services.activity_service import record_activity

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

        now = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Jakarta"))
        today_date = now.date()
        current_time_str = now.time().isoformat()
        # ISO day_of_week: Monday is 0, Sunday is 6
        day_of_week = today_date.weekday() 

        for item in pets:
            pet = cast(Dict[str, Any], item)
            child_id = pet.get("child_id")
            if not child_id:
                continue
                
            # Evaluasi setiap jadwal yang sudah berakhir. schedule_occurrences
            # menjadi deduplikasi authoritative agar penalty tidak berulang.
            # Cari jadwal makan hari ini yang WAKTU BERAKHIRNYA (end_time) sudah terlewat
            schedules_response = client.table("custom_meal_schedules").select("*") \
                .eq("child_id", child_id) \
                .eq("day_of_week", day_of_week) \
                .eq("is_active", True) \
                .lte("end_time", current_time_str) \
                .execute()

            for schedule in schedules_response.data:
                occurrences = client.table("schedule_occurrences").select("id,status") \
                    .eq("schedule_id", schedule["id"]) \
                    .eq("occurrence_date", today_date.isoformat()) \
                    .execute().data or []
                if occurrences:
                    continue

                logger.info(f"[Compliance Worker] Anak {child_id} melewatkan jadwal {schedule['meal_name']}! Penalty diterapkan.")
                try:
                    occurrence = client.table("schedule_occurrences").insert({
                        "schedule_id": schedule["id"], "child_id": child_id,
                        "occurrence_date": today_date.isoformat(), "status": "skipped",
                    }).execute().data[0]
                    if schedule.get("schedule_type", "meal") == "medicine":
                        gamification.apply_missed_medicine_penalty(child_id)
                    else:
                        gamification.apply_missed_meal_penalty(child_id)
                    record_activity(
                        actor_id=child_id, actor_role="system", action="schedule.missed",
                        target_type="schedule_occurrence", target_id=str(occurrence["id"]),
                        child_id=child_id, description=f"Missed {schedule.get('schedule_type', 'meal')} schedule.",
                    )
                except Exception as e:
                    logger.error(f"Gagal memberi penalty jadwal untuk {child_id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"[Compliance Worker] Terjadi kesalahan saat mengecek data: {str(e)}")
        
    logger.info("[Compliance Worker] Pengecekan selesai.")

def clean_old_alerts() -> None:
    """
    Menghapus alerts yang berusia lebih dari 7 hari.
    """
    logger.info("[Compliance Worker] Memulai pembersihan alerts lama...")
    client = get_supabase_service_client()
    try:
        # Hitung tanggal 7 hari yang lalu
        import datetime
        seven_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
        seven_days_ago_iso = seven_days_ago.isoformat()
        
        # Hapus alerts
        res = client.table("alerts").delete().lt("created_at", seven_days_ago_iso).execute()
        deleted_count = len(res.data) if res.data else 0
        logger.info(f"[Compliance Worker] Berhasil menghapus {deleted_count} alert lama.")
    except Exception as e:
        logger.error(f"[Compliance Worker] Gagal membersihkan alerts lama: {str(e)}")
