from __future__ import annotations

from typing import Any

from app.core.supabase import get_supabase_service_client


def record_activity(
    *,
    actor_id: str,
    actor_role: str,
    action: str,
    target_type: str,
    target_id: str | None = None,
    child_id: str | None = None,
    description: str = "",
    outcome: str = "success",
) -> None:
    """Write a server-authoritative audit event; failures never mask a mutation."""
    try:
        get_supabase_service_client().table("activity_logs").insert(
            {
                "user_id": actor_id,
                "action": action,
                "entity_type": target_type,
                "entity_id": target_id,
                "metadata": {
                    "role": actor_role,
                    "child_id": child_id,
                    "description": description,
                    "outcome": outcome,
                },
            }
        ).execute()
    except Exception:
        # Logging is best-effort because older deployments may not have migration 008/009.
        return

