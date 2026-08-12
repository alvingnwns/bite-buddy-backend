from typing import Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Field

from app.core.auth import get_current_user
from app.core.supabase import get_supabase_service_client
from app.models.base import CamelModel
from app.models.database import UserRole

router = APIRouter()

class LoginRequest(CamelModel):
    username: str
    password: str
    role: UserRole

class RegisterRequest(CamelModel):
    username: str
    password: str
    role: UserRole
    doctor_code: str | None = None
    patient_code: str | None = None

@router.post("/login")
def login(req: LoginRequest) -> Any:
    """Login using Supabase GoTrue with mapped email."""
    client = get_supabase_service_client()
    dummy_email = f"{req.username}@bitebuddy.local"
    try:
        auth_response = client.auth.sign_in_with_password({
            "email": dummy_email,
            "password": req.password
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get user profile
        user_resp = client.table("users").select("*").eq("id", auth_response.user.id).single().execute()
        user_data = user_resp.data if user_resp.data else {}
        
        # Determine parentId / childId based on role
        role = user_data.get("role", req.role.value)
        parent_id = auth_response.user.id if role == "parent" else user_data.get("parent_id")
        child_id = auth_response.user.id if role == "child" else None

        return {
            "accessToken": auth_response.session.access_token,
            "user": {
                "id": auth_response.user.id,
                "username": req.username,
                "role": role,
                "parentId": parent_id,
                "childId": child_id
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/register", status_code=201)
def register(req: RegisterRequest) -> Any:
    client = get_supabase_service_client()
    dummy_email = f"{req.username}@bitebuddy.local"
    
    try:
        # 1. Sign up on Supabase Auth
        auth_response = client.auth.sign_up({
            "email": dummy_email,
            "password": req.password,
            "options": {
                "data": {
                    "username": req.username,
                    "role": req.role.value
                }
            }
        })
        
        user_id = auth_response.user.id
        
        # 2. Add to public.users
        client.table("users").insert({
            "id": user_id,
            "email": dummy_email,
            "full_name": req.username,
            "role": req.role.value,
            "is_active": True,
            "password_hash": "supabase_managed"
        }).execute()
        
        parent_id = user_id if req.role == UserRole.parent else None
        child_id = user_id if req.role == UserRole.child else None
        
        return {
            "userId": user_id,
            "parentId": parent_id,
            "childId": child_id,
            "role": req.role.value,
            "requiresLogin": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/me")
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    client = get_supabase_service_client()
    try:
        resp = client.table("users").select("*").eq("id", current_user["id"]).single().execute()
        user_data = resp.data
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        role = user_data.get("role")
        
        # Asumsi: Jika username tidak ada, kita derive dari email dummy
        email = user_data.get("email", "")
        username = email.replace("@bitebuddy.local", "") if "@bitebuddy.local" in email else email
        
        parent_id = current_user["id"] if role == "parent" else user_data.get("parent_id")
        child_id = current_user["id"] if role == "child" else None
        
        return {
            "user": {
                "id": current_user["id"],
                "username": username,
                "role": role,
                "parentId": parent_id,
                "childId": child_id
            }
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
