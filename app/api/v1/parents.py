from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import assert_parent_child, require_parent
from app.api.errors import api_error
from app.api.v1.children import history_detail, history_list
from app.core.supabase import get_supabase_service_client
from app.models.base import CamelModel
from app.services.activity_service import record_activity
from app.services.integration_service import canonical_pet, dashboard, notification, schedules, wib_today

router = APIRouter()


class LinkChildRequest(CamelModel):
    child_code: str


class ScheduleCreate(CamelModel):
    title: str
    start_time: str
    end_time: str


class ScheduleUpdate(CamelModel):
    title: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class ReminderRequest(CamelModel):
    reminder_type: Literal["eat", "take_pills"]


def _validate_time_window(start: str, end: str) -> None:
    import re
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", start) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", end) or start >= end:
        raise api_error(422, "validation_error", "One or more fields are invalid.", {"fields": {"startTime": ["Use HH:mm and ensure start is before end."], "endTime": ["Use HH:mm and ensure end is after start."]}})


def _child(row: dict[str, Any]) -> dict[str, Any]:
    return {"id": str(row["id"]), "name": row.get("full_name") or row.get("username") or "Child", "pet": canonical_pet(str(row["id"]))}


@router.get("/me/children")
def get_children(identity: dict[str, Any] = Depends(require_parent)) -> dict[str, Any]:
    rows = get_supabase_service_client().table("users").select("id,username,full_name").eq("parent_id", identity["id"]).eq("role", "child").execute().data or []
    return {"items": [_child(row) for row in rows]}


@router.post("/me/children/link", status_code=201)
def link_child(req: LinkChildRequest, identity: dict[str, Any] = Depends(require_parent)) -> dict[str, Any]:
    client = get_supabase_service_client()
    rows = client.table("users").select("id,username,full_name,parent_id,role").eq("patient_code", req.child_code.strip()).eq("role", "child").execute().data or []
    if not rows: raise api_error(404, "child_code_not_found", "Child code is invalid.")
    row = rows[0]
    if row.get("parent_id") and str(row["parent_id"]) != identity["id"]:
        raise api_error(409, "child_already_linked", "Child is already linked to another parent.")
    if str(row.get("parent_id")) == identity["id"]:
        raise api_error(409, "child_already_linked", "Child is already linked to this parent.")
    updated = client.table("users").update({"parent_id": identity["id"]}).eq("id", row["id"]).is_("parent_id", "null").execute().data or []
    if not updated: raise api_error(409, "child_already_linked", "Child could not be linked.")
    record_activity(actor_id=identity["id"], actor_role="parent", action="child.link", target_type="user", target_id=str(row["id"]), child_id=str(row["id"]), description="Linked child.")
    return _child(updated[0])


@router.get("/me/children/{child_id}")
def get_child(child_id: str, identity: dict[str, Any] = Depends(require_parent)) -> dict[str, Any]:
    child = assert_parent_child(identity["id"], child_id)
    return {"id": child_id, "name": child.get("full_name") or child.get("username"), "birthdate": child.get("birth_date"), "gender": child.get("gender"), "pet": canonical_pet(child_id)}


@router.get("/me/children/{child_id}/dashboard")
def get_child_dashboard(child_id: str, identity: dict[str, Any] = Depends(require_parent)) -> dict[str, Any]:
    assert_parent_child(identity["id"], child_id)
    return dashboard(child_id)


@router.get("/me/children/{child_id}/schedules")
def get_child_schedules(child_id: str, identity: dict[str, Any] = Depends(require_parent)) -> dict[str, Any]:
    assert_parent_child(identity["id"], child_id)
    return schedules(child_id)


def _schedule_row(row: dict[str, Any]) -> dict[str, Any]:
    def short(value: Any) -> str: return str(value or "")[:5]
    return {"id": str(row["id"]), "title": row["meal_name"], "startTime": short(row["start_time"]), "endTime": short(row["end_time"]), "type": row.get("schedule_type", "meal"), "status": "not_yet"}


@router.post("/me/children/{child_id}/schedules", status_code=201)
def create_schedule(child_id: str, req: ScheduleCreate, identity: dict[str, Any] = Depends(require_parent)) -> dict[str, Any]:
    assert_parent_child(identity["id"], child_id)
    _validate_time_window(req.start_time, req.end_time)
    row = get_supabase_service_client().table("custom_meal_schedules").insert({
        "child_id": child_id, "created_by": identity["id"], "meal_type": "snack",
        "day_of_week": wib_today().weekday(), "meal_name": req.title.strip(),
        "start_time": req.start_time, "end_time": req.end_time, "schedule_type": "meal", "is_active": True,
    }).execute().data[0]
    record_activity(actor_id=identity["id"], actor_role="parent", action="schedule.create", target_type="schedule", target_id=str(row["id"]), child_id=child_id, description=f"Created {req.title.strip()} schedule.")
    return _schedule_row(row)


def _owned_schedule(parent_id: str, child_id: str, schedule_id: str) -> dict[str, Any]:
    assert_parent_child(parent_id, child_id)
    rows = get_supabase_service_client().table("custom_meal_schedules").select("*").eq("id", schedule_id).eq("child_id", child_id).execute().data or []
    if not rows: raise api_error(404, "schedule_not_found", "Schedule was not found.")
    if rows[0].get("schedule_type", "meal") != "meal": raise api_error(403, "medicine_schedule_read_only", "Medicine schedules are read-only for parents.")
    return rows[0]


@router.patch("/me/children/{child_id}/schedules/{schedule_id}")
def update_schedule(child_id: str, schedule_id: str, req: ScheduleUpdate, identity: dict[str, Any] = Depends(require_parent)) -> dict[str, Any]:
    current = _owned_schedule(identity["id"], child_id, schedule_id)
    start = req.start_time or str(current["start_time"])[:5]
    end = req.end_time or str(current["end_time"])[:5]
    _validate_time_window(start, end)
    changes = {"meal_name": req.title.strip() if req.title is not None else current["meal_name"], "start_time": start, "end_time": end}
    row = get_supabase_service_client().table("custom_meal_schedules").update(changes).eq("id", schedule_id).eq("child_id", child_id).execute().data[0]
    record_activity(actor_id=identity["id"], actor_role="parent", action="schedule.update", target_type="schedule", target_id=schedule_id, child_id=child_id, description="Updated meal schedule.")
    return _schedule_row(row)


@router.delete("/me/children/{child_id}/schedules/{schedule_id}", status_code=204)
def delete_schedule(child_id: str, schedule_id: str, identity: dict[str, Any] = Depends(require_parent)) -> Response:
    _owned_schedule(identity["id"], child_id, schedule_id)
    get_supabase_service_client().table("custom_meal_schedules").delete().eq("id", schedule_id).eq("child_id", child_id).execute()
    record_activity(actor_id=identity["id"], actor_role="parent", action="schedule.delete", target_type="schedule", target_id=schedule_id, child_id=child_id, description="Deleted meal schedule.")
    return Response(status_code=204)


@router.get("/me/children/{child_id}/history")
def get_child_history(child_id: str, history_type: str = Query("food", alias="type"), limit: int = Query(20, ge=1, le=100), cursor: str | None = None, identity: dict[str, Any] = Depends(require_parent)) -> dict[str, Any]:
    assert_parent_child(identity["id"], child_id)
    return history_list(child_id, history_type, limit, cursor)


@router.get("/me/children/{child_id}/history/{history_id}")
def get_child_history_detail(child_id: str, history_id: str, identity: dict[str, Any] = Depends(require_parent)) -> dict[str, Any]:
    assert_parent_child(identity["id"], child_id)
    return history_detail(child_id, history_id)


@router.get("/me/children/{child_id}/notifications")
def get_child_notifications(child_id: str, limit: int = Query(20, ge=1, le=100), cursor: str | None = None, identity: dict[str, Any] = Depends(require_parent)) -> dict[str, Any]:
    assert_parent_child(identity["id"], child_id)
    query = get_supabase_service_client().table("alerts").select("*").eq("child_id", child_id)
    query = query.or_(f"recipient_user_id.is.null,recipient_user_id.eq.{identity['id']}")
    if cursor: query = query.lt("created_at", cursor)
    rows = query.order("created_at", desc=True).limit(limit + 1).execute().data or []
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {"items": [notification(row) for row in rows], "nextCursor": rows[-1].get("created_at") if has_more and rows else None}


@router.post("/me/children/{child_id}/reminders", status_code=201)
def send_reminder(child_id: str, req: ReminderRequest, identity: dict[str, Any] = Depends(require_parent)) -> dict[str, Any]:
    assert_parent_child(identity["id"], child_id)
    title, message = ("Parent", "Reminder: Eat") if req.reminder_type == "eat" else ("Parent", "Reminder: Take Pills")
    row = get_supabase_service_client().table("alerts").insert({"child_id": child_id, "type": "parent_reminder", "sender_type": "parent", "title": title, "message": message, "is_read": False}).execute().data[0]
    record_activity(actor_id=identity["id"], actor_role="parent", action="reminder.create", target_type="notification", target_id=str(row["id"]), child_id=child_id, description=f"Sent {req.reminder_type} reminder.")
    return {"notification": notification(row)}
