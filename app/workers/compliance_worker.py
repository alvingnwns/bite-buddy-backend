import logging
from datetime import datetime, timezone

from app.core.supabase import get_supabase_service_client
from app.services.gamification_service import GamificationService

logger = logging.getLogger(__name__)

def check_daily_compliance() -> None:
    """
    Pekerja Latar Belakang (Background Worker).
    Berjalan secara berkala (misal: setiap jam atau setiap 1 menit untuk demo).
    Tugas:
    1. Mencari anak-anak yang melewatkan jadwal obat hari ini.
    2. Memberikan Penalty (mengurangi Happiness Pet) jika terlewat.
    """
    logger.info("[Compliance Worker] Memulai pengecekan kepatuhan medis...")
    
    client = get_supabase_service_client()
    gamification = GamificationService()
    
    try:
        # Ambil daftar semua pet (representasi dari anak-anak yang terdaftar)
        pets_response = client.table("virtual_pets").select("*").execute()
        pets = pets_response.data
        
        if not pets:
            logger.info("[Compliance Worker] Tidak ada data pet untuk dievaluasi.")
            return

        # Dapatkan hari ini dalam format tanggal (UTC)
        today = datetime.now(timezone.utc).date()
        today_start_iso = datetime(today.year, today.month, today.day, tzinfo=timezone.utc).isoformat()
        
        for pet in pets:
            child_id = pet.get("child_id")
            if not child_id:
                continue
                
            # Cek apakah anak ini punya log obat hari ini (dikonsumsi)
            logs_response = client.table("medication_logs").select("*") \
                .eq("child_id", child_id) \
                .gte("created_at", today_start_iso) \
                .execute()
                
            has_taken_medicine_today = len(logs_response.data) > 0
            
            # Jika anak belum mencatat minum obat sama sekali hari ini
            if not has_taken_medicine_today:
                logger.info(f"[Compliance Worker] Anak {child_id} melewatkan obat! Memberikan Penalty.")
                
                # Rule Engine Penalty Khusus Worker:
                # Kurangi 20 Happiness, Tambah 5 Hunger (karena tidak teratur)
                try:
                    gamification.update_pet_status(
                        child_id=child_id, 
                        exp_delta=0, 
                        happiness_delta=-20, 
                        hunger_delta=5
                    )
                except Exception as e:
                    logger.error(f"[Compliance Worker] Gagal memberi penalty untuk {child_id}: {str(e)}")
            else:
                logger.info(f"[Compliance Worker] Anak {child_id} sudah minum obat hari ini. Aman.")
                
    except Exception as e:
        logger.error(f"[Compliance Worker] Terjadi kesalahan saat mengecek data: {str(e)}")
        
    logger.info("[Compliance Worker] Pengecekan selesai.")
