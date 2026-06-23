import uuid

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request.state.request_id = request_id

        with logger.contextualize(request_id=request_id):
            logger.info(f"{request.method} {request.url.path}")
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
