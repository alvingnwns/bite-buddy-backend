from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.core.config import settings
from app.workers import scheduler as scheduler_module


@pytest.mark.asyncio
async def test_scheduler_uses_production_wib_cron(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "scheduler_enabled", True)

    scheduler_module.start_scheduler()
    try:
        scheduler = scheduler_module.scheduler
        assert scheduler is not None
        assert str(scheduler.timezone) == "Asia/Jakarta"

        compliance = scheduler.get_job("daily_compliance_wib")
        cleanup = scheduler.get_job("daily_alert_cleanup_wib")
        assert compliance is not None
        assert cleanup is not None

        wib = ZoneInfo("Asia/Jakarta")
        reference = datetime(2026, 8, 14, 12, 0, tzinfo=wib)
        assert compliance.trigger.get_next_fire_time(None, reference) == datetime(
            2026, 8, 14, 23, 59, tzinfo=wib
        )
        assert cleanup.trigger.get_next_fire_time(None, reference) == datetime(
            2026, 8, 15, 0, 30, tzinfo=wib
        )
    finally:
        scheduler_module.stop_scheduler()


@pytest.mark.asyncio
async def test_scheduler_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "scheduler_enabled", False)

    scheduler_module.start_scheduler()

    assert scheduler_module.scheduler is None
