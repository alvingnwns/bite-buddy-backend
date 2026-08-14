import asyncio
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.workers.compliance_worker import check_daily_compliance, clean_old_alerts

scheduler: AsyncIOScheduler | None = None
WIB = ZoneInfo("Asia/Jakarta")

def start_scheduler() -> None:
    """
    Memulai pekerja latar belakang (APScheduler).
    Dipanggil saat aplikasi FastAPI menyala.
    """
    global scheduler
    if not settings.scheduler_enabled:
        return
    if scheduler is not None and scheduler.running:
        return
    # Bind a fresh scheduler to the current app lifespan event loop. TestClient
    # and reloads create new loops, so a module-import scheduler becomes stale.
    scheduler = AsyncIOScheduler(
        event_loop=asyncio.get_running_loop(),
        timezone=WIB,
    )
    scheduler.add_job(
        check_daily_compliance,
        "cron",
        hour=23,
        minute=59,
        id="daily_compliance_wib",
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )
    scheduler.add_job(
        clean_old_alerts,
        "cron",
        hour=0,
        minute=30,
        id="daily_alert_cleanup_wib",
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )
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
