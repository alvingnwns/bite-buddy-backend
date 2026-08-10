from typing import Dict, Any
from fastapi import HTTPException, status
import uuid

from app.core.auth import get_current_user

# Ekspor kembali MOCK_USER_ID untuk testing jika diperlukan, 
# walaupun sekarang get_current_user akan mengembalikan dari token.
MOCK_USER_ID = "00000000-0000-0000-0000-000000000000"
