"""
Tenant API endpoints for AvatarFactory multi-tenancy.

Provides REST API endpoints for:
- Admin tenant management (CRUD, API keys)
- Tenant self-service configuration (LLM, connectors)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from fastapi import APIRouter, HTTPException, Request, status, Depends
except ImportError:
    raise ImportError(
        "FastAPI is required for tenant API. " "Install with: pip install avatarfactory[service]"
    )


# =============================================================================
# Request/Response Models
# =============================================================================


class TenantCreateRequest(BaseModel):
    """Request to create a tenant."""

    name: str = Field(..., description="Tenant display name")
    contact_email: Optional[str] = Field(None, description="Contact email")
    max_personas: int = Field(default=10, ge=1, le=100)
    max_content_per_day: int = Field(default=100, ge=1, le=1000)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TenantResponse(BaseModel):
    """Tenant response model."""

    id: str
    name: str
    status: str
    max_personas: int
    max_content_per_day: int
    max_api_keys: int
    contact_email: Optional[str]
    created_at: str
    updated_at: str


class APIKeyCreateRequest(BaseModel):
    """Request to create an API key."""

    name: str = Field(default="Default", description="Key name/description")
    scopes: List[str] = Field(default=["read", "write"], description="Permission scopes")
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime")


class APIKeyResponse(BaseModel):
    """API key response model (without the actual key)."""

    id: str
    tenant_id: str
    key_prefix: str
    name: str
    status: str
    scopes: List[str]
    created_at: str
    expires_at: Optional[str]


class APIKeyCreatedResponse(APIKeyResponse):
    """Response when creating an API key (includes the key once)."""

    api_key: str = Field(..., description="The API key (only shown once!)")


class LLMConfigRequest(BaseModel):
    """Request to configure LLM provider."""

    provider: str = Field(..., description="Provider: anthropic, azure_openai, openai")
    api_key: str = Field(..., description="API key for the provider")
    model: Optional[str] = Field(None, description="Model name")
    azure_endpoint: Optional[str] = Field(None)
    azure_deployment: Optional[str] = Field(None)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=100, le=128000)


class LLMConfigResponse(BaseModel):
    """LLM configuration response (without API key)."""

    provider: str
    model: str
    azure_endpoint: Optional[str]
    temperature: float
    max_tokens: int
    configured: bool


class ConnectorCredentialsRequest(BaseModel):
    """Request to configure connector credentials."""

    credentials: Dict[str, str] = Field(
        ..., description="Credential key-value pairs for the connector"
    )


class ConnectorStatusResponse(BaseModel):
    """Connector status response."""

    connector_type: str
    configured: bool
    created_at: Optional[str]
    updated_at: Optional[str]


# =============================================================================
# Router Factory
# =============================================================================


def create_admin_router() -> APIRouter:
    """Create the admin API router for tenant management."""
    from avatarfactory.core.tenant import TenantManager, get_tenant_manager

    router = APIRouter(prefix="/admin", tags=["Admin"])

    def get_manager(request: Request) -> TenantManager:
        """Get tenant manager, ensuring admin authentication."""
        # Note: Admin auth is handled by middleware
        import os

        kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
        return get_tenant_manager(kb_path)

    @router.get("/tenants", response_model=List[TenantResponse])
    async def list_tenants(
        include_deleted: bool = False,
        manager: TenantManager = Depends(get_manager),
    ):
        """List all tenants."""
        tenants = manager.list_tenants(include_deleted=include_deleted)
        return [
            TenantResponse(
                id=t.id,
                name=t.name,
                status=t.status,
                max_personas=t.max_personas,
                max_content_per_day=t.max_content_per_day,
                max_api_keys=t.max_api_keys,
                contact_email=t.contact_email,
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat(),
            )
            for t in tenants
        ]

    @router.post("/tenants", response_model=TenantResponse, status_code=201)
    async def create_tenant(
        request: TenantCreateRequest,
        manager: TenantManager = Depends(get_manager),
    ):
        """Create a new tenant."""
        tenant = manager.create_tenant(
            name=request.name,
            contact_email=request.contact_email,
            max_personas=request.max_personas,
            max_content_per_day=request.max_content_per_day,
            metadata=request.metadata,
        )
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            status=tenant.status,
            max_personas=tenant.max_personas,
            max_content_per_day=tenant.max_content_per_day,
            max_api_keys=tenant.max_api_keys,
            contact_email=tenant.contact_email,
            created_at=tenant.created_at.isoformat(),
            updated_at=tenant.updated_at.isoformat(),
        )

    @router.get("/tenants/{tenant_id}", response_model=TenantResponse)
    async def get_tenant(
        tenant_id: str,
        manager: TenantManager = Depends(get_manager),
    ):
        """Get a specific tenant."""
        tenant = manager.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found",
            )
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            status=tenant.status,
            max_personas=tenant.max_personas,
            max_content_per_day=tenant.max_content_per_day,
            max_api_keys=tenant.max_api_keys,
            contact_email=tenant.contact_email,
            created_at=tenant.created_at.isoformat(),
            updated_at=tenant.updated_at.isoformat(),
        )

    @router.delete("/tenants/{tenant_id}")
    async def delete_tenant(
        tenant_id: str,
        hard_delete: bool = False,
        manager: TenantManager = Depends(get_manager),
    ):
        """Delete a tenant."""
        try:
            result = manager.delete_tenant(tenant_id, hard_delete=hard_delete)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant {tenant_id} not found",
                )
            return {"status": "deleted", "tenant_id": tenant_id}
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @router.get("/tenants/{tenant_id}/api-keys", response_model=List[APIKeyResponse])
    async def list_api_keys(
        tenant_id: str,
        manager: TenantManager = Depends(get_manager),
    ):
        """List API keys for a tenant."""
        keys = manager.list_api_keys(tenant_id)
        return [
            APIKeyResponse(
                id=k.id,
                tenant_id=k.tenant_id,
                key_prefix=k.key_prefix,
                name=k.name,
                status=k.status,
                scopes=k.scopes,
                created_at=k.created_at.isoformat(),
                expires_at=k.expires_at.isoformat() if k.expires_at else None,
            )
            for k in keys
        ]

    @router.post(
        "/tenants/{tenant_id}/api-keys",
        response_model=APIKeyCreatedResponse,
        status_code=201,
    )
    async def create_api_key(
        tenant_id: str,
        request: APIKeyCreateRequest,
        manager: TenantManager = Depends(get_manager),
    ):
        """Create an API key for a tenant."""
        try:
            api_key, raw_key = manager.create_api_key(
                tenant_id=tenant_id,
                name=request.name,
                scopes=request.scopes,
                expires_at=request.expires_at,
            )
            return APIKeyCreatedResponse(
                id=api_key.id,
                tenant_id=api_key.tenant_id,
                key_prefix=api_key.key_prefix,
                name=api_key.name,
                status=api_key.status,
                scopes=api_key.scopes,
                created_at=api_key.created_at.isoformat(),
                expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
                api_key=raw_key,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @router.delete("/tenants/{tenant_id}/api-keys/{key_id}")
    async def revoke_api_key(
        tenant_id: str,
        key_id: str,
        manager: TenantManager = Depends(get_manager),
    ):
        """Revoke an API key."""
        result = manager.revoke_api_key(key_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key {key_id} not found",
            )
        return {"status": "revoked", "key_id": key_id}

    return router


def create_tenant_router() -> APIRouter:
    """Create the tenant self-service API router."""
    from avatarfactory.core.tenant import TenantManager, get_tenant_manager
    from avatarfactory.middleware.auth import get_tenant_context

    router = APIRouter(prefix="/tenant", tags=["Tenant"])

    def get_manager() -> TenantManager:
        """Get tenant manager."""
        import os

        kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
        return get_tenant_manager(kb_path)

    @router.get("/config")
    async def get_tenant_config(request: Request):
        """Get current tenant configuration."""
        tenant_ctx = get_tenant_context(request)
        manager = get_manager()

        tenant = manager.get_tenant(tenant_ctx.tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )

        return {
            "tenant_id": tenant.id,
            "name": tenant.name,
            "status": tenant.status,
            "quotas": {
                "max_personas": tenant.max_personas,
                "max_content_per_day": tenant.max_content_per_day,
            },
            "llm_configured": manager.get_llm_config(tenant.id) is not None,
            "connectors_configured": manager.list_configured_connectors(tenant.id),
        }

    @router.get("/llm", response_model=LLMConfigResponse)
    async def get_llm_config(request: Request):
        """Get LLM configuration (without API key)."""
        tenant_ctx = get_tenant_context(request)
        manager = get_manager()

        config = manager.get_llm_config(tenant_ctx.tenant_id)
        if not config:
            return LLMConfigResponse(
                provider="",
                model="",
                azure_endpoint=None,
                temperature=0.7,
                max_tokens=4096,
                configured=False,
            )

        return LLMConfigResponse(
            provider=config.provider,
            model=config.model,
            azure_endpoint=config.azure_endpoint,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            configured=True,
        )

    @router.put("/llm", response_model=LLMConfigResponse)
    async def set_llm_config(request: Request, config_request: LLMConfigRequest):
        """Set LLM configuration."""
        tenant_ctx = get_tenant_context(request)
        manager = get_manager()

        try:
            config = manager.set_llm_config(
                tenant_id=tenant_ctx.tenant_id,
                provider=config_request.provider,
                api_key=config_request.api_key,
                model=config_request.model,
                azure_endpoint=config_request.azure_endpoint,
                azure_deployment=config_request.azure_deployment,
                temperature=config_request.temperature,
                max_tokens=config_request.max_tokens,
            )
            return LLMConfigResponse(
                provider=config.provider,
                model=config.model,
                azure_endpoint=config.azure_endpoint,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                configured=True,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @router.get("/connectors", response_model=List[ConnectorStatusResponse])
    async def list_connectors(request: Request):
        """List configured connectors."""
        tenant_ctx = get_tenant_context(request)
        manager = get_manager()

        # Get configured connectors for this tenant
        from avatarfactory.connectors.registry import ConnectorRegistry

        all_platforms = ConnectorRegistry.list_platforms()
        configured = manager.list_configured_connectors(tenant_ctx.tenant_id)

        results = []
        for platform in set(all_platforms):
            is_configured = platform in configured
            results.append(
                ConnectorStatusResponse(
                    connector_type=platform,
                    configured=is_configured,
                    created_at=None,
                    updated_at=None,
                )
            )

        return results

    @router.put("/connectors/{connector_type}")
    async def set_connector_credentials(
        request: Request,
        connector_type: str,
        cred_request: ConnectorCredentialsRequest,
    ):
        """Set credentials for a connector."""
        tenant_ctx = get_tenant_context(request)
        manager = get_manager()

        # Validate connector type
        from avatarfactory.connectors.registry import ConnectorRegistry

        if not ConnectorRegistry.is_registered(connector_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown connector type: {connector_type}",
            )

        try:
            manager.set_connector_credentials(
                tenant_id=tenant_ctx.tenant_id,
                connector_type=connector_type,
                credentials=cred_request.credentials,
            )
            return {
                "status": "configured",
                "connector_type": connector_type,
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @router.delete("/connectors/{connector_type}")
    async def delete_connector_credentials(
        request: Request,
        connector_type: str,
    ):
        """Delete credentials for a connector."""
        tenant_ctx = get_tenant_context(request)
        manager = get_manager()

        result = manager.delete_connector_credentials(
            tenant_id=tenant_ctx.tenant_id,
            connector_type=connector_type,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No credentials found for {connector_type}",
            )

        return {
            "status": "deleted",
            "connector_type": connector_type,
        }

    @router.post("/connectors/{connector_type}/test")
    async def test_connector(
        request: Request,
        connector_type: str,
    ):
        """Test a connector connection."""
        tenant_ctx = get_tenant_context(request)
        manager = get_manager()

        from avatarfactory.connectors.registry import ConnectorRegistry

        try:
            connector = ConnectorRegistry.get_for_tenant(
                platform=connector_type,
                tenant_id=tenant_ctx.tenant_id,
                kb_path=str(manager.kb_path),
            )

            # Try to connect
            await connector.connect()
            await connector.disconnect()

            return {
                "status": "success",
                "connector_type": connector_type,
                "message": "Connection successful",
            }

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            return {
                "status": "error",
                "connector_type": connector_type,
                "message": str(e),
            }

    return router
