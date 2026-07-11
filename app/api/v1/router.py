from fastapi import APIRouter

from app.api.v1 import health, scan, users, clinical, schedules, pets, logs

api_v1_router = APIRouter()

api_v1_router.include_router(health.router)
api_v1_router.include_router(scan.router)
api_v1_router.include_router(users.router, prefix="/users", tags=["Users"])
api_v1_router.include_router(clinical.router, prefix="/clinical", tags=["Clinical Parameters"])
api_v1_router.include_router(schedules.router, prefix="/schedules", tags=["Schedules"])
api_v1_router.include_router(pets.router, prefix="/pets", tags=["Virtual Pets"])
api_v1_router.include_router(logs.router, prefix="/logs", tags=["Logs & History"])
