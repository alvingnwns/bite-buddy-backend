import logging
from uuid import UUID
from app.core.supabase import get_supabase_service_client

logger = logging.getLogger(__name__)

def create_alert(child_id: UUID, alert_type: str, message: str) -> None:
    """
    Menyisipkan sebuah alert ke dalam tabel alerts di Supabase.
    Insert ini otomatis memicu Postgres Changes yang bisa di-subscribe oleh frontend
    secara real-time melalui WebSocket.
    """
    client = get_supabase_service_client()
    try:
        client.table("alerts").insert({
            "child_id": str(child_id),
            "type": alert_type,
            "message": message,
            "is_read": False
        }).execute()
        logger.info(f"Alert created for child {child_id}: {alert_type} - {message}")
    except Exception as e:
        # Kita hanya logging error agar kegagalan alert tidak memblokir flow utama (seperti gamification)
        logger.error(f"Gagal membuat alert untuk child {child_id}: {str(e)}")
