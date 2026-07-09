import os
import uuid
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.core.supabase import get_supabase_service_client

# UUID statis (tapi diacak sebagian) untuk membedakan hasil test E2E.
# Kita generate per session test agar user bisa mengeceknya.
E2E_USER_ID = str(uuid.uuid4())
E2E_CHILD_ID = str(uuid.uuid4())
E2E_PET_ID = str(uuid.uuid4())

@pytest.fixture(scope="session")
def test_client() -> Generator[TestClient, None, None]:
    """Menyediakan instance FastAPI TestClient."""
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="session", autouse=True)
def setup_e2e_data():
    """
    Setup data fiktif (dummy) di Supabase agar test E2E bisa dijalankan.
    Sesuai permintaan user, data ini TIDAK DIHAPUS (No Teardown) agar bisa dicek manual.
    """
    print(f"\n--- SETUP E2E DUMMY DATA ---")
    print(f"User ID: {E2E_USER_ID}")
    print(f"Child ID: {E2E_CHILD_ID}")
    print(f"Pet ID: {E2E_PET_ID}")
    
    client = get_supabase_service_client()
    
    # 1. Insert User
    try:
        client.table("users").insert({
            "id": E2E_USER_ID,
            "email": f"e2e_test_{E2E_USER_ID[:8]}@example.com",
            "password_hash": "dummyhash",
            "full_name": "E2E Test Parent",
            "role": "parent"
        }).execute()
        print("[OK] Inserted Dummy User")
    except Exception as e:
        print(f"[FAIL] Gagal insert User: {e}")

    # 1.1 Insert Child User
    try:
        client.table("users").insert({
            "id": E2E_CHILD_ID,
            "email": f"e2e_child_{E2E_CHILD_ID[:8]}@example.com",
            "password_hash": "dummyhash",
            "full_name": "E2E Test Child",
            "role": "child"
        }).execute()
        print("[OK] Inserted Dummy Child User")
    except Exception as e:
        print(f"[FAIL] Gagal insert Child User: {e}")

    # 2. Insert Clinical Parameters
    try:
        client.table("clinical_parameters").insert({
            "child_id": E2E_CHILD_ID,
            "recorded_by": E2E_USER_ID,
            "height_cm": 120,
            "weight_kg": 25,
            "target_daily_calories": 1500,
            "target_daily_carbs": 200,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        print("[OK] Inserted Dummy Clinical Parameters")
    except Exception as e:
        print(f"[FAIL] Gagal insert Clinical Parameters: {e}")

    # 3. Insert Virtual Pet
    try:
        client.table("virtual_pets").insert({
            "id": E2E_PET_ID,
            "child_id": E2E_CHILD_ID,
            "pet_type": "dragon",
            "pet_name": "E2E Pet",
            "level": 1,
            "experience_points": 50,
            "happiness": 100,
            "hunger": 100,
            "is_active": True
        }).execute()
        print("[OK] Inserted Dummy Virtual Pet")
    except Exception as e:
        print(f"[FAIL] Gagal insert Pet: {e}")
        
    yield {
        "user_id": E2E_USER_ID,
        "child_id": E2E_CHILD_ID,
        "pet_id": E2E_PET_ID
    }
    
    # TEARDOWN: Sengaja dikosongkan (PASS) sesuai permintaan user
    print(f"\n--- TEARDOWN DILOMPATI (Data tetap ada di DB) ---")
    pass
