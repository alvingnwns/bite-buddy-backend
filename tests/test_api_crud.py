from unittest.mock import MagicMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MOCK_CHILD_ID = str(uuid.uuid4())
MOCK_USER_ID = "00000000-0000-0000-0000-000000000000"

# Mock all Supabase client calls
@pytest.fixture(autouse=True)
def mock_supabase():
    with patch("app.api.v1.users.get_supabase_service_client") as mock_users, \
         patch("app.api.v1.clinical.get_supabase_service_client") as mock_clinical, \
         patch("app.api.v1.schedules.get_supabase_service_client") as mock_schedules, \
         patch("app.api.v1.pets.get_supabase_service_client") as mock_pets, \
         patch("app.api.v1.logs.get_supabase_service_client") as mock_logs:
         
        mock_client = MagicMock()
        mock_users.return_value = mock_client
        mock_clinical.return_value = mock_client
        mock_schedules.return_value = mock_client
        mock_pets.return_value = mock_client
        mock_logs.return_value = mock_client
        
        yield mock_client

def test_get_users_me(mock_supabase):
    # Mock return data
    mock_supabase.table().select().eq().execute.return_value = MagicMock(
        data=[{"id": MOCK_USER_ID, "name": "Test Parent"}]
    )
    
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Parent"

def test_update_users_me(mock_supabase):
    mock_supabase.table().update().eq().execute.return_value = MagicMock(
        data=[{"id": MOCK_USER_ID, "name": "Updated Name"}]
    )
    
    response = client.patch(f"/api/v1/users/{MOCK_USER_ID}", json={"name": "Updated Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"

def test_get_clinical_latest(mock_supabase):
    mock_supabase.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[{"child_id": MOCK_CHILD_ID, "weight_kg": 20}]
    )
    
    response = client.get(f"/api/v1/clinical/{MOCK_CHILD_ID}/latest")
    assert response.status_code == 200
    assert response.json()["weight_kg"] == 20

def test_create_schedule(mock_supabase):
    mock_supabase.table().insert().execute.return_value = MagicMock(
        data=[{"id": "test-uuid", "child_id": MOCK_CHILD_ID, "meal_name": "Breakfast"}]
    )
    
    response = client.post("/api/v1/schedules/", json={
        "child_id": MOCK_CHILD_ID,
        "created_by": MOCK_USER_ID,
        "meal_type": "breakfast",
        "day_of_week": 1,
        "meal_name": "Breakfast"
    })
    
    assert response.status_code == 200
    assert response.json()["meal_name"] == "Breakfast"

def test_get_logs(mock_supabase):
    mock_supabase.table().select().eq().order().range().execute.return_value = MagicMock(
        data=[{"child_id": MOCK_CHILD_ID, "meal_type": "breakfast"}]
    )
    
    response = client.get(f"/api/v1/logs/food/{MOCK_CHILD_ID}?limit=5")
    assert response.status_code == 200
    assert len(response.json()) == 1
