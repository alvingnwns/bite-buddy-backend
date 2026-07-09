import pytest
from app.services.reasoning_service import ReasoningService

def test_estimate_nutrition_all_healthy():
    service = ReasoningService()
    result = service.estimate_nutrition(["apple", "salad"])
    
    assert result["is_healthy"] is True
    assert result["total_calories"] == 95 + 150
    assert result["total_carbs"] == 25 + 10

def test_estimate_nutrition_with_junk_food():
    service = ReasoningService()
    # pizza is a junk food
    result = service.estimate_nutrition(["apple", "pizza"])
    
    assert result["is_healthy"] is False
    assert result["total_calories"] == 95 + 285

def test_estimate_nutrition_unknown_food():
    service = ReasoningService()
    # unknown_food should default to healthy
    result = service.estimate_nutrition(["some_random_fruit"])
    
    assert result["is_healthy"] is True
