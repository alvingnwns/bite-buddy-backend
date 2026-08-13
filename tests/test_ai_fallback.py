import asyncio

from app.services.ai_service import AIService
from app.services.reasoning_service import ReasoningService


class FakeOpenRouter:
    configured = True

    async def complete_json(self, _prompt, **_kwargs):
        return {
            "is_food": True,
            "food_name": "Ice cream",
            "ingredients": [{
                "name": "ice cream", "weight_g": 90, "kcal_per_100g": 210,
                "protein_g_per_100g": 4, "fat_g_per_100g": 12.5,
                "carbs_g_per_100g": 20.6, "sugar_g_per_100g": 17.5,
                "fiber_g_per_100g": 0,
            }],
        }


def test_food_analysis_uses_qwen_when_gemini_fails(monkeypatch):
    service = AIService()
    service.api_key = "gemini-key"
    service.openrouter = FakeOpenRouter()

    async def failed_gemini(*_args):
        raise RuntimeError("503 Service Unavailable")

    monkeypatch.setattr(service, "_gemini_food", failed_gemini)
    is_food, food_name, ingredients = asyncio.run(
        service.detect_food_ingredients(b"image", "image/jpeg")
    )
    assert is_food is True
    assert food_name == "Ice cream"
    assert ingredients[0]["ingredient"] == "ice cream"
    nutrition = service.food_data_service.calculate_nutrition_for_meal(ingredients)
    assert ingredients[0]["dataSource"] == "TKPI 2020"
    assert ingredients[0]["sugarEstimated"] is True
    assert nutrition["sugar_g"] > 0


def test_nutrition_evaluation_uses_qwen_when_gemini_fails(monkeypatch):
    service = ReasoningService()
    service.api_key = "gemini-key"

    class NutritionFallback:
        configured = True

        async def complete_json(self, _prompt, **_kwargs):
            return {"is_healthy": True, "health_score": 82, "explanation": "Gula masih terkontrol."}

    service.openrouter = NutritionFallback()

    class BrokenModel:
        async def generate_content_async(self, *_args, **_kwargs):
            raise RuntimeError("quota exceeded")

    monkeypatch.setattr("app.services.reasoning_service.genai.GenerativeModel", lambda *_args: BrokenModel())
    result = asyncio.run(service.evaluate_meal_health([], {"sugar_g": 4, "fiber_g": 3}))
    assert result == {"is_healthy": True, "health_score": 82, "explanation": "Gula masih terkontrol."}
