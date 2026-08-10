import pytest
from app.services.reasoning_service import ReasoningService

@pytest.mark.asyncio
async def test_process_confirmed_meal_healthy():
    service = ReasoningService()
    ingredients = [
        {"ingredient": "apple", "description": "Apples, raw", "weight_g": 100, "fdcId": 171688} # Mock valid fdcId
    ]
    result = await service.process_confirmed_meal(ingredients)
    
    assert result["is_healthy"] in [True, False]
    assert "total_calories" in result
    assert "explanation" in result

@pytest.mark.asyncio
async def test_process_confirmed_meal_multiple():
    service = ReasoningService()
    ingredients = [
        {"ingredient": "apple", "description": "Apples, raw", "weight_g": 100, "fdcId": 171688},
        {"ingredient": "peanut butter", "description": "Peanut butter", "weight_g": 30, "fdcId": 174278}
    ]
    result = await service.process_confirmed_meal(ingredients)
    
    assert "total_calories" in result
    assert "foods_detected" in result
    assert len(result["foods_detected"]) == 2
