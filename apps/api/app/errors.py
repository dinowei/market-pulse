from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

MEDIA_TYPE = "application/problem+json"


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def problem(request: Request, status: int, title: str, detail: str, code: str) -> JSONResponse:
    body = {
        "type": f"https://market-pulse.invalid/problems/{code.lower()}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
        "request_id": request_id(request),
    }
    return JSONResponse(body, status_code=status, media_type=MEDIA_TYPE)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {
        401: "UNAUTHORIZED",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        503: "SERVICE_UNAVAILABLE",
    }.get(exc.status_code, "HTTP_ERROR")
    return problem(request, exc.status_code, "HTTP error", str(exc.detail), code)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return problem(
        request,
        422,
        "Validation error",
        "The request could not be validated.",
        "VALIDATION_ERROR",
    )


async def unhandled_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
    return problem(
        request,
        500,
        "Internal server error",
        "An unexpected error occurred.",
        "INTERNAL_ERROR",
    )
