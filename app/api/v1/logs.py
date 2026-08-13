from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_identity
from app.api.errors import api_error
from app.core.supabase import get_supabase_service_client

router = APIRouter()


@router.get("/activity-logs")
def get_activity_logs(
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    timezone_name: str = Query("Asia/Jakarta", alias="timezone"),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
    identity: dict[str, Any] = Depends(get_identity),
) -> dict[str, Any]:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        raise api_error(422, "validation_error", "Timezone is invalid.", {"fields": {"timezone": ["Unknown IANA timezone."]}})
    year, month_number = map(int, month.split("-"))
    start_local = datetime(year, month_number, 1, tzinfo=zone)
    if month_number == 12:
        end_local = datetime(year + 1, 1, 1, tzinfo=zone)
    else:
        end_local = datetime(year, month_number + 1, 1, tzinfo=zone)
    start_utc = start_local.astimezone(timezone.utc).isoformat()
    end_utc = end_local.astimezone(timezone.utc).isoformat()
    query = (
        get_supabase_service_client().table("activity_logs").select("*")
        .eq("user_id", identity["id"]).gte("created_at", start_utc).lt("created_at", end_utc)
    )
    if cursor: query = query.lt("created_at", cursor)
    rows = query.order("created_at", desc=True).limit(limit + 1).execute().data or []
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = []
    for row in rows:
        metadata = row.get("metadata") or {}
        items.append({
            "id": str(row["id"]), "actorId": str(row["user_id"]),
            "actorRole": metadata.get("role", identity["role"]), "actionType": row["action"],
            "targetType": row["entity_type"], "targetId": str(row["entity_id"]) if row.get("entity_id") else None,
            "childId": str(metadata["child_id"]) if metadata.get("child_id") else None,
            "description": metadata.get("description", ""), "outcome": metadata.get("outcome", "success"),
            "occurredAt": row["created_at"],
        })
    return {"month": month, "timezone": timezone_name, "items": items, "nextCursor": rows[-1].get("created_at") if has_more and rows else None}
