from fastapi import APIRouter
from app.api.v1 import health, logs, auth, children, parents

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_v1_router.include_router(children.router, prefix="/children", tags=["Children"])
api_v1_router.include_router(parents.router, prefix="/parents", tags=["Parents"])
api_v1_router.include_router(health.router)
api_v1_router.include_router(logs.router, tags=["Activity Logs"])
