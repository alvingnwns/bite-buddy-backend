from typing import Dict, Any
from fastapi import HTTPException, status
import uuid

# Dummy UUID for the mocked user
MOCK_USER_ID = "00000000-0000-0000-0000-000000000000"

def get_current_user() -> Dict[str, Any]:
    """
    Mock dependency untuk mendapatkan user yang sedang login.
    Pada Fase 7, ini akan diganti dengan verifikasi JWT dari Supabase Auth.
    """
    return {
        "id": MOCK_USER_ID,
        "email": "dummy@example.com",
        "role": "parent" # or whatever mock you want
    }
