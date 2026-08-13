from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.core.supabase import get_supabase_service_client

WIB = ZoneInfo("Asia/Jakarta")


def wib_today() -> date:
    return datetime.now(timezone.utc).astimezone(WIB).date()


def canonical_pet(child_id: str) -> dict[str, Any]:
    response = get_supabase_service_client().table("virtual_pets").select("*").eq("child_id", child_id).execute()
    if not response.data:
        inserted = get_supabase_service_client().table("virtual_pets").insert(
            {"child_id": child_id, "pet_name": "Buddy", "pet_type": "dog"}
        ).execute()
        pet = inserted.data[0]
    else:
        pet = response.data[0]
    level = int(pet.get("level", 1))
    threshold = (100 * level) + 150
    return {
        "level": level,
        "hp": round((float(pet.get("happiness", 100)) + float(pet.get("hunger", 100))) / 200, 2),
        "xp": round(float(pet.get("experience_points", 0)) / threshold, 2),
    }


def streak_days(child_id: str) -> int:
    rows = (
        get_supabase_service_client().table("food_logs")
        .select("consumed_at").eq("child_id", child_id)
        .order("consumed_at", desc=True).limit(90).execute().data or []
    )
    completed = {
        datetime.fromisoformat(str(row["consumed_at"]).replace("Z", "+00:00")).astimezone(WIB).date()
        for row in rows if row.get("consumed_at")
    }
    cursor = wib_today()
    streak = 0
    from datetime import timedelta
    while cursor in completed:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def dashboard(child_id: str) -> dict[str, Any]:
    return {
        "childId": child_id,
        "pet": canonical_pet(child_id),
        "streakDays": streak_days(child_id),
        "asOf": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _time_text(value: Any) -> str:
    if isinstance(value, time):
        return value.strftime("%H:%M")
    return str(value or "")[:5]


def _schedule_occurs_on(row: dict[str, Any], day: date) -> bool:
    recurrence = row.get("recurrence_type")
    if row.get("schedule_type") != "medicine" or not recurrence:
        return int(row.get("day_of_week", -1)) == day.weekday()
    anchor_text = row.get("recurrence_anchor_date") or row.get("start_date")
    try:
        anchor = date.fromisoformat(str(anchor_text))
    except (TypeError, ValueError):
        return int(row.get("day_of_week", -1)) == day.weekday()
    if day < anchor:
        return False
    elapsed = (day - anchor).days
    if recurrence == "everyday":
        return True
    if recurrence == "every_x_days":
        return elapsed % max(1, int(row.get("recurrence_interval_days") or 1)) == 0
    if recurrence == "once_a_week":
        return elapsed % 7 == 0
    if recurrence == "once_a_month":
        return day.day == anchor.day
    return False


def schedules(child_id: str, target_date: date | None = None) -> dict[str, Any]:
    day = target_date or wib_today()
    rows = (
        get_supabase_service_client().table("custom_meal_schedules")
        .select("*").eq("child_id", child_id).eq("is_active", True)
        .execute().data or []
    )
    rows = [row for row in rows if _schedule_occurs_on(row, day)]
    occurrences = (
        get_supabase_service_client().table("schedule_occurrences")
        .select("schedule_id,status").eq("child_id", child_id)
        .eq("occurrence_date", day.isoformat()).execute().data or []
    )
    status_by_id = {str(row["schedule_id"]): row["status"] for row in occurrences}
    now = datetime.now(timezone.utc).astimezone(WIB)
    items = []
    for row in rows:
        status = status_by_id.get(str(row["id"]), "not_yet")
        if status == "not_yet" and day == now.date() and _time_text(row.get("end_time")) < now.strftime("%H:%M"):
            status = "late"
        items.append({
            "id": str(row["id"]),
            "title": row.get("meal_name", ""),
            "startTime": _time_text(row.get("start_time")),
            "endTime": _time_text(row.get("end_time")),
            "type": row.get("schedule_type", "meal"),
            "status": status,
        })
    items.sort(key=lambda item: item["startTime"])
    return {"date": day.isoformat(), "timezone": "Asia/Jakarta", "items": items}


def complete_matching_schedule(child_id: str, schedule_type: str) -> dict[str, Any] | None:
    result = schedules(child_id)
    now_text = datetime.now(timezone.utc).astimezone(WIB).strftime("%H:%M")
    candidates = [
        item for item in result["items"]
        if item["type"] == schedule_type and item["status"] != "done"
        and item["startTime"] <= now_text <= item["endTime"]
    ]
    if not candidates:
        return None
    item = candidates[0]
    client = get_supabase_service_client()
    existing = client.table("schedule_occurrences").select("id").eq("schedule_id", item["id"]).eq("occurrence_date", result["date"]).execute()
    payload = {"schedule_id": item["id"], "child_id": child_id, "occurrence_date": result["date"], "status": "done", "completed_at": datetime.now(timezone.utc).isoformat()}
    if existing.data:
        client.table("schedule_occurrences").update(payload).eq("id", existing.data[0]["id"]).execute()
    else:
        client.table("schedule_occurrences").insert(payload).execute()
    return {"id": item["id"], "status": "done"}


def notification(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]), "childId": str(row["child_id"]),
        "senderType": row.get("sender_type", "pet"), "title": row.get("title", "BiteBuddy"),
        "message": row.get("message", ""), "isRead": bool(row.get("is_read", False)),
        "createdAt": row.get("created_at"),
    }
