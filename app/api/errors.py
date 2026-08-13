from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


def api_error(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "details": details or {}},
    )


def error_payload(request: Request, detail: Any, status_code: int) -> dict[str, Any]:
    if isinstance(detail, dict) and "code" in detail:
        payload = dict(detail)
    else:
        code = {
            400: "bad_request",
            401: "authentication_required",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            413: "upload_too_large",
            415: "unsupported_media_type",
        }.get(status_code, "request_failed")
        payload = {"code": code, "message": str(detail), "details": {}}
    payload["requestId"] = getattr(request.state, "request_id", "unknown")
    return payload


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(request, exc.detail, exc.status_code),
        headers=exc.headers,
    )

