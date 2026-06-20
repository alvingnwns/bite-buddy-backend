from fastapi import APIRouter
from postgrest import CountMethod

from app.core.supabase import supabase
from app.models.health import HealthResponse, build_health_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Endpoint untuk memverifikasi server berjalan."""
    return build_health_response()


@router.get("/db-check")
async def database_check() -> dict:
    """Cek koneksi ke Supabase database."""
    try:
        result = (
            supabase.table("users")
            .select("count", count=CountMethod.exact)
            .limit(1)
            .execute()
        )
        return {
            "status": "ok",
            "db_connected": True,
            "user_count": result.count,
        }
    except Exception as e:
        return {
            "status": "error",
            "db_connected": False,
            "error": str(e),
        }
