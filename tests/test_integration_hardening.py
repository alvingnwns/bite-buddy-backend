from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import children
from app.services.ai_service import AIService


class Query:
    def __init__(self, client, table):
        self.client = client
        self.table = table

    def select(self, *_args): return self
    def eq(self, *_args): return self

    def execute(self):
        if self.table == "analysis_drafts":
            return SimpleNamespace(data=[self.client.draft])
        raise AssertionError(f"Unexpected table query: {self.table}")


class AtomicClient:
    def __init__(self, analysis_type):
        self.analysis_type = analysis_type
        self.rpc_call = None
        self.draft = {
            "id": "00000000-0000-0000-0000-000000000020",
            "child_id": "00000000-0000-0000-0000-000000000010",
            "analysis_type": analysis_type,
            "status": "draft" if analysis_type == "food" else "awaiting_confirmation",
            "image_url": "https://example.test/image.jpg",
            "payload": {
                "foodName": "Salad", "portionGrams": 100,
                "nutrition": {"kcal": 120, "sugar_g": 4},
            } if analysis_type == "food" else {
                "isMedicine": True, "detected": {"detected": "insulin pen"},
            },
        }

    def table(self, name): return Query(self, name)

    def rpc(self, name, params):
        assert name == "confirm_child_analysis"
        self.rpc_call = params
        history = {
            "id": "00000000-0000-0000-0000-000000000030",
            "child_id": params["p_child_id"],
            "analysis_id": params["p_analysis_id"],
            "photo_url": self.draft["image_url"],
            "created_at": "2026-08-13T12:00:00+00:00",
        }
        if self.analysis_type == "food":
            history.update({"food_name": "Salad", "is_healthy": True})
        else:
            history.update({"is_medicine": True, "status": "done"})
        result = {
            "history": history,
            "pet": {"level": 1, "hp": 1, "xp": 0.15},
            "affectedSchedule": None,
            "streakDays": 1,
        }
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=result))


@pytest.mark.asyncio
async def test_ai_without_provider_fails_closed():
    service = AIService()
    service.api_key = ""

    with pytest.raises(HTTPException) as food_error:
        await service.detect_food_ingredients(b"image")
    with pytest.raises(HTTPException) as medicine_error:
        await service.detect_medicine(b"image")

    assert food_error.value.status_code == 503
    assert medicine_error.value.status_code == 503


@pytest.mark.asyncio
async def test_food_confirmation_uses_single_atomic_rpc(monkeypatch):
    client = AtomicClient("food")
    monkeypatch.setattr(children, "get_supabase_service_client", lambda: client)

    result = await children.confirm_food(
        client.draft["id"], children.ConfirmFoodRequest(portionGrams=150),
        {"id": client.draft["child_id"], "role": "child"},
    )

    assert client.rpc_call["p_analysis_type"] == "food"
    assert client.rpc_call["p_portion_grams"] == 150
    assert result["history"]["type"] == "food"
    assert result["streakDays"] == 1


def test_medicine_confirmation_uses_single_atomic_rpc(monkeypatch):
    client = AtomicClient("medicine")
    monkeypatch.setattr(children, "get_supabase_service_client", lambda: client)

    result = children.confirm_medicine(
        client.draft["id"],
        {"id": client.draft["child_id"], "role": "child"},
    )

    assert client.rpc_call["p_analysis_type"] == "medicine"
    assert result["history"]["type"] == "medicine"


def test_migration_bridges_doctor_notification_and_keeps_audit_atomic():
    sql = open("migrations/016_cross_app_notifications_atomic_confirmations.sql", encoding="utf-8").read()

    assert "INSERT INTO public.alerts" in sql
    assert "doctor_notification_id" in sql
    assert "CREATE OR REPLACE FUNCTION public.confirm_child_analysis" in sql
    assert "INSERT INTO public.activity_logs" in sql
