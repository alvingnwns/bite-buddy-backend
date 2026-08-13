import logging
from typing import Any, Dict

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.api.errors import api_error

from app.core.config import settings
from app.core.supabase import get_supabase_service_client

logger = logging.getLogger(__name__)

# HTTPBearer akan secara otomatis mengekstrak token dari header 'Authorization: Bearer <token>'
security = HTTPBearer(auto_error=False)

def decode_jwt(token: str) -> Dict[str, Any]:
    """
    Dekode dan validasi token JWT menggunakan Supabase JWT Secret.
    """
    if not settings.supabase_jwt_secret:
        try:
            response = get_supabase_service_client().auth.get_user(token)
            if not response.user:
                raise ValueError("Supabase did not return a user")
            return {"sub": str(response.user.id)}
        except Exception:
            raise api_error(401, "authentication_required", "Authentication is required.")
        
    try:
        # Supabase menggunakan algoritma HS256
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={
                "verify_aud": False, # Biasanya aud Supabase menyesuaikan dengan tipe project
                "verify_exp": True   # Pastikan token belum expired
            }
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token autentikasi telah kedaluwarsa (Expired).",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token JWT tidak valid: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token autentikasi tidak valid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> Dict[str, Any]:
    """
    FastAPI Dependency untuk melindungi endpoint.
    Jika token valid, ini akan mengembalikan data payload token.
    Jika tidak valid/tidak ada, FastAPI akan me-return HTTP 401 Unauthorized otomatis.
    """
    if credentials is None:
        raise api_error(401, "authentication_required", "Authentication is required.")

    token = credentials.credentials
    payload = decode_jwt(token)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak memiliki klaim 'sub' (User ID).",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Inject 'id' into payload so existing code using current_user["id"] works
    payload["id"] = user_id
        
    return payload
