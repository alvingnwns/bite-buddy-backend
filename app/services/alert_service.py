"""AlertService — Membuat alert real-time untuk frontend.

Setiap INSERT ke tabel alerts otomatis memicu Postgres Changes broadcast
yang bisa di-subscribe oleh frontend via Supabase Realtime WebSocket.

Cara penggunaan:
  from app.services.alert_service import create_alert
  from app.models.database import AlertType

  create_alert(child_id, AlertType.food_warning, "Makanan ini kurang sehat!")
"""

import logging
from uuid import UUID

from app.core.supabase import get_supabase_service_client
from app.models.database import AlertType

logger = logging.getLogger(__name__)


def create_alert(child_id: UUID, alert_type: AlertType, message: str) -> None:
    """Insert satu alert ke tabel alerts di Supabase.

    Fungsi ini dengan sengaja tidak raise exception agar kegagalan alert
    tidak memblokir flow utama (misalnya: gamification tetap jalan
    meskipun alert gagal dikirim).

    Error akan di-log sebagai WARNING agar bisa dimonitor.

    Args:
        child_id: UUID anak yang menerima alert
        alert_type: Tipe alert (AlertType enum — type-safe, tidak bisa typo)
        message: Pesan yang akan ditampilkan ke pengguna
    """
    client = get_supabase_service_client()
    try:
        client.table("alerts").insert({
            "child_id": str(child_id),
            "type": alert_type.value,   # .value karena DB menyimpan string, bukan enum object
            "message": message,
            "is_read": False,
        }).execute()
        logger.info(f"Alert [{alert_type.value}] created for child {child_id}: {message}")
    except Exception as e:
        # Non-fatal: log saja, jangan raise
        logger.error(f"Gagal membuat alert untuk child {child_id}: {str(e)}")
