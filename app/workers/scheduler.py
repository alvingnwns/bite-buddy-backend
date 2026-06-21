from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.workers.compliance_worker import check_daily_compliance

# Inisialisasi AsyncIOScheduler
scheduler = AsyncIOScheduler()

def start_scheduler() -> None:
    """
    Memulai pekerja latar belakang (APScheduler).
    Dipanggil saat aplikasi FastAPI menyala.
    """
    # Untuk keperluan DEMO: Berjalan setiap 1 menit.
    # Pada produksi, gunakan cron trigger (contoh: day_of_week="*", hour="23", minute="59").
    scheduler.add_job(check_daily_compliance, "interval", minutes=1, id="compliance_job_demo")
    scheduler.start()

def stop_scheduler() -> None:
    """
    Menghentikan pekerja latar belakang.
    Dipanggil saat aplikasi FastAPI mati.
    """
    scheduler.shutdown()
