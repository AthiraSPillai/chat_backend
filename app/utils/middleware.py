from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import logging

from api.auth.dependency import get_current_user_from_token

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Incoming request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Outgoing response: {request.method} {request.url} - Status {response.status_code}")
        return response

class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, public_routes: list = None):
        super().__init__(app)
        self.public_routes = public_routes or []

    async def dispatch(self, request: Request, call_next):
        # Allow OPTIONS requests to pass through without authentication
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check if the route is public
        for route in self.public_routes:
            if request.url.path.startswith(route):
                return await call_next(request)

        # Attempt to authenticate
        try:
            user = await get_current_user_from_token(request)
            request.state.user = user  # Attach user to request state
        except Exception as e:
            logger.warning(f"Authentication failed: {e}")
            return Response("Unauthorized", status_code=401)

        response = await call_next(request)
        return response


