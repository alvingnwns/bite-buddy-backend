from typing import Any

from fastapi import Depends

from app.api.errors import api_error
from app.core.auth import get_current_user
from app.core.supabase import get_supabase_service_client


def get_identity(token_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    response = (
        get_supabase_service_client()
        .table("users")
        .select("id,username,email,full_name,role,parent_id,is_active")
        .eq("id", token_user["id"])
        .single()
        .execute()
    )
    user = response.data
    if not user or not user.get("is_active", True):
        raise api_error(401, "authentication_required", "Authentication is required.")
    user["id"] = str(user["id"])
    return user


def require_child(identity: dict[str, Any] = Depends(get_identity)) -> dict[str, Any]:
    if identity.get("role") != "child":
        raise api_error(403, "forbidden", "This operation is not permitted.")
    return identity


def require_parent(identity: dict[str, Any] = Depends(get_identity)) -> dict[str, Any]:
    if identity.get("role") != "parent":
        raise api_error(403, "forbidden", "This operation is not permitted.")
    return identity


def assert_parent_child(parent_id: str, child_id: str) -> dict[str, Any]:
    response = (
        get_supabase_service_client()
        .table("users")
        .select("id,username,full_name,birth_date,gender,parent_id,role")
        .eq("id", child_id)
        .eq("parent_id", parent_id)
        .eq("role", "child")
        .execute()
    )
    if not response.data:
        raise api_error(403, "forbidden", "This operation is not permitted.")
    return response.data[0]
