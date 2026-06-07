"""
Middleware package for AvatarFactory.
"""

from avatarfactory.middleware.auth import (
    TenantContext,
    get_tenant_context,
    require_scope,
)

__all__ = [
    "TenantContext",
    "get_tenant_context",
    "require_scope",
]

# Only export TenantAuthMiddleware if FastAPI is available
try:
    from avatarfactory.middleware.auth import TenantAuthMiddleware as _TenantAuthMiddleware

    TenantAuthMiddleware = _TenantAuthMiddleware
    __all__.append("TenantAuthMiddleware")
except ImportError:
    pass
