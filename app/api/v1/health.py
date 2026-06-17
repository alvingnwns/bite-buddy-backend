from fastapi import APIRouter

from app.models.health import HealthResponse, build_health_response

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Endpoint untuk memverifikasi server berjalan."""
    return build_health_response()
