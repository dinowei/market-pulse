from uuid import UUID, uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID")
        try:
            value = str(UUID(incoming)) if incoming else str(uuid4())
        except ValueError:
            value = str(uuid4())
        request.state.request_id = value
        response = await call_next(request)
        response.headers["X-Request-ID"] = value
        return response
