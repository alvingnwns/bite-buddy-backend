from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uuid import uuid4

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.api.errors import http_exception_handler


from app.workers.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Startup: Start Background Worker
    start_scheduler()
    yield
    # Shutdown: Stop Background Worker
    stop_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Format Pydantic errors to: {"fields": {"field_name": ["error msg"]}}
        fields = {}
        for err in exc.errors():
            # Get the field name from the location tuple, e.g. ('body', 'username')
            loc = err.get('loc', [])
            field_name = str(loc[-1]) if len(loc) > 0 else "unknown"
            # In camelCase validation, field names might need fixing, but pydantic should handle it with aliases
            if field_name not in fields:
                fields[field_name] = []
            fields[field_name].append(err.get('msg', 'Invalid value'))
            
        return JSONResponse(
            status_code=422,
            content={
                "code": "validation_error",
                "message": "One or more fields are invalid.",
                "details": {
                    "fields": fields
                },
                "requestId": getattr(request.state, "request_id", "unknown")
            },
        )

    app.add_exception_handler(HTTPException, http_exception_handler)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, _: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "code": "internal_error",
                "message": "An unexpected error occurred.",
                "details": {},
                "requestId": getattr(request.state, "request_id", "unknown"),
            },
        )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or str(uuid4())
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router, prefix="/api/v1")

    @app.get("/health", response_model=dict[str, str], tags=["health"])
    async def root_health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
