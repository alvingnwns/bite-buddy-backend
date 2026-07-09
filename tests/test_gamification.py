import uuid
from unittest.mock import MagicMock, patch

import pytest
from app.services.gamification_service import GamificationService

@patch("app.services.gamification_service.get_supabase_service_client")
def test_evaluate_food_compliance_junk_food(mock_supabase):
    # Setup mock supabase
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client
    
    # Mock pet data
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[{"target_daily_calories": 1500}]
    )
    mock_client.table().select().eq().execute.return_value = MagicMock(
        data=[{"id": "pet-123", "experience_points": 50, "level": 1, "happiness": 80, "hunger": 50, "child_id": "child-1"}]
    )
    
    service = GamificationService()
    # Panggil fungsi dengan is_healthy=False
    result = service.evaluate_food_compliance(uuid.uuid4(), total_calories=300, is_healthy=False)
    
    # Karena junk food, EXP +0, Happiness berkurang 20, Hunger nambah 20
    assert result["exp_gained"] == 0
    assert result["new_happiness"] == 60  # 80 - 20
    assert result["new_hunger"] == 70     # 50 + 20

@patch("app.services.gamification_service.get_supabase_service_client")
def test_evaluate_food_compliance_healthy_good_calories(mock_supabase):
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client
    
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[{"target_daily_calories": 1500}]
    )
    mock_client.table().select().eq().execute.return_value = MagicMock(
        data=[{"id": "pet-123", "experience_points": 50, "level": 1, "happiness": 80, "hunger": 50, "child_id": "child-1"}]
    )
    
    service = GamificationService()
    # Panggil fungsi dengan is_healthy=True, kalori <= 500 (1500 / 3) * 1.15
    result = service.evaluate_food_compliance(uuid.uuid4(), total_calories=400, is_healthy=True)
    
    assert result["exp_gained"] == 15
    assert result["new_happiness"] == 95  # 80 + 15
    assert result["new_hunger"] == 80     # 50 + 30
