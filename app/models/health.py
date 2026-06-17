from pydantic import BaseModel

from app.core.config import settings


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str


def build_health_response() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.app_version,
    )
