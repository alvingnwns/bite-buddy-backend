import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.workers.compliance_worker import check_daily_compliance, clean_old_alerts

scheduler: AsyncIOScheduler | None = None

def start_scheduler() -> None:
    """
    Memulai pekerja latar belakang (APScheduler).
    Dipanggil saat aplikasi FastAPI menyala.
    """
    # Untuk keperluan DEMO: Berjalan setiap 1 menit.
    # Pada produksi, gunakan cron trigger (contoh: day_of_week="*", hour="23", minute="59").
    global scheduler
    if scheduler is not None and scheduler.running:
        return
    # Bind a fresh scheduler to the current app lifespan event loop. TestClient
    # and reloads create new loops, so a module-import scheduler becomes stale.
    scheduler = AsyncIOScheduler(event_loop=asyncio.get_running_loop())
    scheduler.add_job(check_daily_compliance, "interval", minutes=1, id="compliance_job_demo")
    scheduler.add_job(clean_old_alerts, "interval", hours=1, id="clean_old_alerts_demo")
    scheduler.start()

def stop_scheduler() -> None:
    """
    Menghentikan pekerja latar belakang.
    Dipanggil saat aplikasi FastAPI mati.
    """
    global scheduler
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler = None
