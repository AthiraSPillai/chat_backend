"""
Custom OpenAPI documentation with secure admin login for FastAPI Azure Backend.

This module provides secure documentation endpoints with admin authentication.
"""

import logging
from typing import Dict, Any, List, Optional, Callable

from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings
from utils.password import verify_password
from api.auth.schema import UserInDB
from services.admin import AdminService

logger = logging.getLogger(__name__)

# HTTP Basic security scheme for docs
security = HTTPBasic()


async def get_admin_user(
    credentials: HTTPBasicCredentials = Depends(security),
    admin_service: AdminService = Depends()
) -> UserInDB:
    """
    Get admin user from credentials.
    
    Args:
        credentials: HTTP Basic credentials
        admin_service: Admin service
        
    Returns:
        UserInDB: Admin user
        
    Raises:
        HTTPException: If authentication fails
    """
    #For quick test only/WebAPP/
    # Check if credentials match admin credentials in settings
    # if credentials.username == settings.ADMIN_USERNAME:
    #     if settings.ADMIN_PASSWORD_HASH and verify_password(credentials.password, settings.ADMIN_PASSWORD_HASH):
    #         # Return a mock admin user
    #         return UserInDB(
    #             id="admin",
    #             username=settings.ADMIN_USERNAME,
    #             email="admin@example.com",
    #             password_hash=settings.ADMIN_PASSWORD_HASH,
    #             role="admin",
    #             is_admin=True,
    #             permissions=["admin:all"],
    #             created_at="2025-01-01T00:00:00Z",
    #             updated_at="2025-01-01T00:00:00Z",
    #             last_login=None,
    #             active=True
    #         )
    
    # If not using hardcoded admin, try to authenticate against database
    query = f"SELECT * FROM c WHERE c.username = @username AND c.is_admin = true"
    params = [{"name": "@username", "value": credentials.username}]
    
    users_container = admin_service.users_container
    
    if users_container:
        admin_users = []
        async for item in users_container.query_items(
            query=query,
            parameters=params
        ):
            admin_users.append(item)
        
        if admin_users and verify_password(credentials.password, admin_users[0]["password_hash"]):
            return UserInDB(**admin_users[0])
    
    # Authentication failed
    logger.warning(f"Failed admin login attempt for username: {credentials.username}")
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )


class SecureDocsMiddleware(BaseHTTPMiddleware):
    """Middleware for securing documentation endpoints."""
    
    def __init__(
        self,
        app: FastAPI,
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
        openapi_url: str = "/openapi.json"
    ):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI application
            docs_url: Swagger UI URL
            redoc_url: ReDoc URL
            openapi_url: OpenAPI JSON URL
        """
        super().__init__(app)
        self.docs_url = docs_url
        self.redoc_url = redoc_url
        self.openapi_url = openapi_url
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process a request and secure documentation endpoints.
        
        Args:
            request: The request to process
            call_next: The next middleware or route handler
            
        Returns:
            Response: The response from the next middleware or route handler
        """
        path = request.url.path
        
        # Allow normal processing for non-docs endpoints
        if path not in [self.docs_url, self.redoc_url, self.openapi_url]:
            return await call_next(request)
        
        # Check for authentication header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Basic "):
            # No authentication provided, return 401
            return Response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic"},
                content="Authentication required"
            )
        
        # Continue with normal processing (authentication will be handled by dependencies)
        return await call_next(request)


def setup_secure_docs(app: FastAPI) -> None:
    """
    Set up secure documentation endpoints.
    
    Args:
        app: FastAPI application
    """
    # Store original docs URLs
    docs_url = app.docs_url
    redoc_url = app.redoc_url
    openapi_url = app.openapi_url
    
    # Disable automatic docs
    app.docs_url = None
    app.redoc_url = None
    app.openapi_url = None
    
    # Add middleware for securing docs endpoints
    app.add_middleware(
        SecureDocsMiddleware,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url
    )
    
    # Create custom endpoints with authentication
    @app.get(openapi_url, include_in_schema=False)
    async def get_open_api_endpoint(admin: UserInDB = Depends(get_admin_user)):
        return get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes
        )
    
    @app.get(docs_url, include_in_schema=False)
    async def get_swagger_ui(admin: UserInDB = Depends(get_admin_user)):
        return get_swagger_ui_html(
            openapi_url=openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )
    
    @app.get(redoc_url, include_in_schema=False)
    async def get_redoc_ui(admin: UserInDB = Depends(get_admin_user)):
        return get_redoc_html(
            openapi_url=openapi_url,
            title=f"{app.title} - ReDoc",
            redoc_js_url="/static/redoc.standalone.js",
        )
    
    # Add logout endpoint
    @app.get("/docs/logout", include_in_schema=False)
    async def logout_from_docs():
        response = HTMLResponse(
            """
            <html>
                <head>
                    <title>Logged Out</title>
                    <meta http-equiv="refresh" content="3;url=/">
                </head>
                <body>
                    <h1>Logged Out</h1>
                    <p>You have been logged out. Redirecting to home page in 3 seconds...</p>
                </body>
            </html>
            """
        )
        response.headers["WWW-Authenticate"] = "Basic"
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return response
