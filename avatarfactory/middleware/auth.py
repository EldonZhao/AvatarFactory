"""
Authentication middleware for AvatarFactory multi-tenancy.

Provides API key validation and tenant context injection.
"""

import os
from typing import Optional

from avatarfactory.core.tenant import TenantAPIKey, TenantManager, get_tenant_manager

# Try to import FastAPI components
try:
    from fastapi import HTTPException, Request, status
    from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
    from starlette.responses import Response

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


class TenantContext:
    """
    Tenant context for the current request.

    Attached to request.state for access in route handlers.
    """

    def __init__(
        self,
        tenant_id: str,
        api_key: Optional[TenantAPIKey] = None,
        is_admin: bool = False,
    ):
        self.tenant_id = tenant_id
        self.api_key = api_key
        self.is_admin = is_admin

    @property
    def scopes(self) -> list[str]:
        """Get permission scopes for this context."""
        if self.is_admin:
            return ["read", "write", "admin"]
        if self.api_key:
            return self.api_key.scopes
        return ["read", "write"]  # Default for unauthenticated (default tenant)

    def has_scope(self, scope: str) -> bool:
        """Check if context has a specific scope."""
        return scope in self.scopes


if FASTAPI_AVAILABLE:

    class TenantAuthMiddleware(BaseHTTPMiddleware):
        """
        Middleware for tenant authentication and context injection.

        Behavior:
        1. If X-API-Key header is present, validate it and set tenant context
        2. If X-Admin-Key header matches the admin key, grant admin access
        3. If no key is provided, use the default tenant (backward compatible)

        Admin endpoints require the X-Admin-Key header.
        """

        # Paths that don't require authentication
        PUBLIC_PATHS = {
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }

        # Paths that require admin authentication
        ADMIN_PATHS = {
            "/admin/",
        }

        def __init__(self, app, kb_path: Optional[str] = None):
            super().__init__(app)
            self.kb_path = kb_path or os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
            self._tenant_manager: Optional[TenantManager] = None
            self._admin_key = os.getenv("AVATARFACTORY_ADMIN_KEY")

        @property
        def tenant_manager(self) -> TenantManager:
            """Lazy load tenant manager."""
            if self._tenant_manager is None:
                self._tenant_manager = get_tenant_manager(self.kb_path)
            return self._tenant_manager

        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            """Process the request and inject tenant context."""
            path = request.url.path

            # Skip auth for public paths
            if self._is_public_path(path):
                request.state.tenant = TenantContext(tenant_id=TenantManager.DEFAULT_TENANT_ID)
                return await call_next(request)

            # Check for admin key on admin paths
            if self._is_admin_path(path):
                admin_key = request.headers.get("X-Admin-Key")
                if not self._validate_admin_key(admin_key):
                    return self._unauthorized_response("Invalid or missing admin key")

                request.state.tenant = TenantContext(
                    tenant_id=TenantManager.DEFAULT_TENANT_ID,
                    is_admin=True,
                )
                return await call_next(request)

            # Check for tenant API key
            api_key_header = request.headers.get("X-API-Key")

            if api_key_header:
                # Validate API key
                api_key = self.tenant_manager.validate_api_key(api_key_header)
                if not api_key:
                    return self._unauthorized_response("Invalid API key")

                # Check if tenant is active
                tenant = self.tenant_manager.get_tenant(api_key.tenant_id)
                if not tenant or tenant.status != "active":
                    return self._unauthorized_response("Tenant is not active")

                request.state.tenant = TenantContext(
                    tenant_id=api_key.tenant_id,
                    api_key=api_key,
                )
            else:
                # No API key - use default tenant (backward compatible)
                request.state.tenant = TenantContext(tenant_id=TenantManager.DEFAULT_TENANT_ID)

            return await call_next(request)

        def _is_public_path(self, path: str) -> bool:
            """Check if path is public (no auth required)."""
            return path in self.PUBLIC_PATHS or path.startswith("/docs")

        def _is_admin_path(self, path: str) -> bool:
            """Check if path requires admin authentication."""
            for admin_path in self.ADMIN_PATHS:
                if path.startswith(admin_path):
                    return True
            return False

        def _validate_admin_key(self, key: Optional[str]) -> bool:
            """Validate the admin key."""
            if not self._admin_key:
                # Admin key not configured - deny all admin requests
                return False
            if not key:
                return False
            return key == self._admin_key

        def _unauthorized_response(self, detail: str) -> Response:
            """Create an unauthorized response."""
            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=401,
                content={"detail": detail},
            )


def get_tenant_context(request) -> TenantContext:
    """
    Get the tenant context from a request.

    Usage in route handlers:
        @app.get("/example")
        async def example(request: Request):
            tenant = get_tenant_context(request)
            print(f"Tenant ID: {tenant.tenant_id}")
    """
    if hasattr(request.state, "tenant"):
        return request.state.tenant
    # Fallback to default tenant
    return TenantContext(tenant_id=TenantManager.DEFAULT_TENANT_ID)


def require_scope(scope: str):
    """
    Dependency to require a specific scope.

    Usage:
        @app.post("/admin/tenants", dependencies=[Depends(require_scope("admin"))])
        async def create_tenant():
            ...
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required for require_scope")

    from fastapi import Depends

    async def check_scope(request: Request):
        tenant = get_tenant_context(request)
        if not tenant.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {scope}",
            )
        return tenant

    return Depends(check_scope)
