from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.core.supabase import get_supabase_service_client


def record_activity(
    *,
    actor_id: str | None,
    actor_role: str,
    action: str,
    target_type: str,
    target_id: str | None = None,
    child_id: str | None = None,
    description: str = "",
    outcome: str = "success",
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write a server-authoritative audit event; failures never mask a mutation."""
    try:
        occurred_at = datetime.now(timezone.utc)
        safe_metadata = dict(metadata or {})
        safe_metadata.update(
            {
                "role": actor_role,
                "child_id": child_id,
                "description": description,
                "outcome": outcome,
                "request_id": request_id,
            }
        )
        get_supabase_service_client().table("activity_logs").insert(
            {
                "user_id": actor_id,
                "action": action,
                "entity_type": target_type,
                "entity_id": target_id,
                "metadata": safe_metadata,
                "created_at": occurred_at.isoformat(),
                "wib_month": occurred_at.astimezone(ZoneInfo("Asia/Jakarta")).strftime("%Y-%m"),
            }
        ).execute()
    except Exception:
        # Logging is best-effort because older deployments may not have migration 008/009.
        return
