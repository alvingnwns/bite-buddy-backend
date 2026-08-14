from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import children
from app.core import auth
from app.services.ai_service import AIService, FOOD_DETECTION_PROVIDER_SCHEMA
from app.services.doctor_ai_service import DOCTOR_SUMMARY_PROVIDER_SCHEMA


class Query:
    def __init__(self, client, table):
        self.client = client
        self.table = table

    def select(self, *_args): return self
    def eq(self, *_args): return self
    def update(self, values):
        self.client.draft.update(values)
        return self

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


def test_doctor_ai_provider_schema_avoids_unsupported_legacy_sdk_keywords():
    schema_text = str(DOCTOR_SUMMARY_PROVIDER_SCHEMA)
    assert "maxLength" not in schema_text
    assert "maxItems" not in schema_text


def test_food_ai_provider_schema_avoids_google_genai_unsupported_constraints():
    schema_text = str(FOOD_DETECTION_PROVIDER_SCHEMA)
    assert "exclusiveMinimum" not in schema_text


def test_missing_jwt_secret_uses_supabase_token_verification(monkeypatch):
    verified = []

    class Auth:
        def get_claims(self, token):
            verified.append(token)
            return SimpleNamespace(claims={"sub": "verified-user", "role": "authenticated"})

    monkeypatch.setattr(auth.settings, "supabase_jwt_secret", "")
    monkeypatch.setattr(
        auth, "get_supabase_service_client", lambda: SimpleNamespace(auth=Auth()),
    )

    assert auth.decode_jwt("signed-token") == {
        "sub": "verified-user", "role": "authenticated",
    }
    assert verified == ["signed-token"]


def test_missing_jwt_secret_accepts_supabase_dict_claims(monkeypatch):
    class Auth:
        def get_claims(self, _token):
            return {"claims": {"sub": "verified-dict-user", "role": "authenticated"}}

    monkeypatch.setattr(auth.settings, "supabase_jwt_secret", "")
    monkeypatch.setattr(
        auth, "get_supabase_service_client", lambda: SimpleNamespace(auth=Auth()),
    )

    assert auth.decode_jwt("signed-token") == {
        "sub": "verified-dict-user", "role": "authenticated",
    }


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
    assert client.rpc_call["p_nutrition"] == {"kcal": 180.0, "sugar_g": 6.0}
    assert result["history"]["type"] == "food"
    assert result["streakDays"] == 1


@pytest.mark.asyncio
async def test_food_confirmation_persists_user_name_and_sugar_correction(monkeypatch):
    client = AtomicClient("food")
    activities = []
    monkeypatch.setattr(children, "get_supabase_service_client", lambda: client)
    monkeypatch.setattr(children, "record_activity", lambda **kwargs: activities.append(kwargs))

    await children.confirm_food(
        client.draft["id"],
        children.ConfirmFoodRequest(
            portionGrams=100, foodName="Ice cream", sugarAmountGrams=18,
        ),
        {"id": client.draft["child_id"], "role": "child"},
    )

    assert client.draft["payload"]["foodName"] == "Ice cream"
    assert client.rpc_call["p_nutrition"]["sugar_g"] == 18
    assert client.rpc_call["p_is_healthy"] is False
    assert activities[0]["action"] == "food_analysis.update"


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
