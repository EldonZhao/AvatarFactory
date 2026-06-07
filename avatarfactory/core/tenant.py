"""
Tenant management for AvatarFactory multi-tenancy support.

Provides models and management for:
- Tenant configuration and lifecycle
- Tenant API keys for authentication
- Per-tenant LLM configuration
- Per-tenant connector credentials
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from avatarfactory.core.credentials import CredentialManager, get_credential_manager

# =============================================================================
# Models
# =============================================================================


class TenantStatus(str):
    """Tenant status values."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Tenant(BaseModel):
    """
    Tenant configuration model.

    Represents a tenant in the multi-tenant system with their
    configuration, quotas, and metadata.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Tenant display name")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: str = Field(default=TenantStatus.ACTIVE)

    # Quotas
    max_personas: int = Field(default=10, description="Maximum personas allowed")
    max_content_per_day: int = Field(default=100, description="Max content per day")
    max_api_keys: int = Field(default=5, description="Maximum API keys allowed")

    # Contact and metadata
    contact_email: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TenantAPIKey(BaseModel):
    """
    API key for tenant authentication.

    The actual API key is never stored - only its hash.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    tenant_id: str
    key_hash: str = Field(..., description="SHA-256 hash of the API key")
    key_prefix: str = Field(..., description="First 8 chars of key for identification")
    name: str = Field(default="Default", description="Key name/description")
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(default=None)
    status: str = Field(default="active")
    scopes: List[str] = Field(
        default_factory=lambda: ["read", "write"],
        description="Permission scopes: read, write, admin",
    )


class TenantLLMConfig(BaseModel):
    """
    Per-tenant LLM provider configuration.

    API keys are stored encrypted.
    """

    provider: str = Field(default="anthropic", description="LLM provider")
    model: str = Field(default="claude-3-5-sonnet-20241022", description="Model name")
    api_key_encrypted: str = Field(default="", description="Encrypted API key")

    # Azure-specific config
    azure_endpoint: Optional[str] = Field(default=None)
    azure_deployment: Optional[str] = Field(default=None)
    azure_api_version: str = Field(default="2024-02-15-preview")

    # Default parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=100, le=128000)


class TenantConnectorCredentials(BaseModel):
    """
    Per-tenant platform connector credentials.

    All credential values are stored encrypted.
    """

    connector_type: str = Field(..., description="Platform connector type")
    credentials_encrypted: Dict[str, str] = Field(
        default_factory=dict, description="Encrypted credential key-value pairs"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TenantConfig(BaseModel):
    """
    Complete tenant configuration including LLM and connectors.

    Stored in {kb_path}/{tenant_id}/tenant_config.yaml
    """

    tenant: Tenant
    llm_config: Optional[TenantLLMConfig] = Field(default=None)
    connectors: Dict[str, TenantConnectorCredentials] = Field(default_factory=dict)


# =============================================================================
# Tenant Manager
# =============================================================================


class TenantManager:
    """
    Manages tenant lifecycle and configuration.

    Handles:
    - Tenant CRUD operations
    - API key management
    - LLM configuration per tenant
    - Connector credentials per tenant
    """

    DEFAULT_TENANT_ID = "default"

    def __init__(self, kb_path: str = "./knowledges"):
        self.kb_path = Path(kb_path)
        self._ensure_structure()
        self._credential_manager = get_credential_manager(str(self.kb_path))

        # Cache for API key lookups
        self._api_key_cache: Dict[str, TenantAPIKey] = {}

    def _ensure_structure(self) -> None:
        """Ensure the multi-tenant directory structure exists."""
        # System directory for tenants list
        system_dir = self.kb_path / "_system"
        system_dir.mkdir(parents=True, exist_ok=True)

        # Ensure default tenant exists
        default_dir = self.kb_path / self.DEFAULT_TENANT_ID
        if not default_dir.exists():
            self._create_default_tenant()

    def _create_default_tenant(self) -> Tenant:
        """Create the default tenant for backward compatibility."""
        tenant = Tenant(
            id=self.DEFAULT_TENANT_ID,
            name="Default Tenant",
            max_personas=999,  # Unlimited for default
            max_content_per_day=9999,
        )
        self.save_tenant(tenant)
        return tenant

    def _get_tenants_file(self) -> Path:
        """Get path to tenants list file."""
        return self.kb_path / "_system" / "tenants.yaml"

    def _get_api_keys_file(self) -> Path:
        """Get path to API keys file."""
        return self.kb_path / "_system" / "api_keys.yaml"

    def _get_tenant_config_path(self, tenant_id: str) -> Path:
        """Get path to tenant config file."""
        return self.kb_path / tenant_id / "tenant_config.yaml"

    # -------------------------------------------------------------------------
    # Tenant CRUD
    # -------------------------------------------------------------------------

    def create_tenant(
        self,
        name: str,
        contact_email: Optional[str] = None,
        max_personas: int = 10,
        max_content_per_day: int = 100,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tenant:
        """
        Create a new tenant.

        Args:
            name: Tenant display name
            contact_email: Optional contact email
            max_personas: Maximum personas quota
            max_content_per_day: Maximum content generation quota
            metadata: Optional metadata dict

        Returns:
            The created Tenant
        """
        tenant = Tenant(
            name=name,
            contact_email=contact_email,
            max_personas=max_personas,
            max_content_per_day=max_content_per_day,
            metadata=metadata or {},
        )

        self.save_tenant(tenant)
        return tenant

    def save_tenant(self, tenant: Tenant) -> None:
        """
        Save or update a tenant.

        Args:
            tenant: Tenant to save
        """
        # Update timestamp
        tenant.updated_at = datetime.now()

        # Ensure tenant directory exists
        tenant_dir = self.kb_path / tenant.id
        tenant_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for tenant data
        (tenant_dir / "personas").mkdir(exist_ok=True)

        # Load existing config or create new
        config_path = self._get_tenant_config_path(tenant.id)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            existing_config = TenantConfig(**data)
            existing_config.tenant = tenant
        else:
            existing_config = TenantConfig(tenant=tenant)

        # Save config
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                existing_config.model_dump(mode="json"),
                f,
                allow_unicode=True,
                sort_keys=False,
            )

        # Update tenants list
        self._update_tenants_list(tenant)

    def _update_tenants_list(self, tenant: Tenant) -> None:
        """Update the global tenants list."""
        tenants_file = self._get_tenants_file()

        tenants = {}
        if tenants_file.exists():
            with open(tenants_file, "r", encoding="utf-8") as f:
                tenants = yaml.safe_load(f) or {}

        tenants[tenant.id] = {
            "name": tenant.name,
            "status": tenant.status,
            "created_at": tenant.created_at.isoformat(),
        }

        with open(tenants_file, "w", encoding="utf-8") as f:
            yaml.dump(tenants, f, allow_unicode=True)

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """
        Get a tenant by ID.

        Args:
            tenant_id: Tenant ID

        Returns:
            Tenant or None if not found
        """
        config_path = self._get_tenant_config_path(tenant_id)
        if not config_path.exists():
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = TenantConfig(**data)
        return config.tenant

    def list_tenants(self, include_deleted: bool = False) -> List[Tenant]:
        """
        List all tenants.

        Args:
            include_deleted: Whether to include deleted tenants

        Returns:
            List of Tenant objects
        """
        tenants = []

        # Iterate through directories
        for item in self.kb_path.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue

            config_path = self._get_tenant_config_path(item.name)
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                config = TenantConfig(**data)
                tenant = config.tenant

                if include_deleted or tenant.status != TenantStatus.DELETED:
                    tenants.append(tenant)

        return sorted(tenants, key=lambda t: t.created_at, reverse=True)

    def delete_tenant(self, tenant_id: str, hard_delete: bool = False) -> bool:
        """
        Delete a tenant.

        Args:
            tenant_id: Tenant ID to delete
            hard_delete: If True, remove all data. If False, mark as deleted.

        Returns:
            True if deleted successfully
        """
        if tenant_id == self.DEFAULT_TENANT_ID:
            raise ValueError("Cannot delete the default tenant")

        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False

        if hard_delete:
            import shutil

            tenant_dir = self.kb_path / tenant_id
            if tenant_dir.exists():
                shutil.rmtree(tenant_dir)

            # Remove from tenants list
            tenants_file = self._get_tenants_file()
            if tenants_file.exists():
                with open(tenants_file, "r", encoding="utf-8") as f:
                    tenants = yaml.safe_load(f) or {}
                if tenant_id in tenants:
                    del tenants[tenant_id]
                with open(tenants_file, "w", encoding="utf-8") as f:
                    yaml.dump(tenants, f, allow_unicode=True)
        else:
            # Soft delete
            tenant.status = TenantStatus.DELETED
            self.save_tenant(tenant)

        # Revoke all API keys
        self._revoke_tenant_api_keys(tenant_id)

        return True

    # -------------------------------------------------------------------------
    # API Key Management
    # -------------------------------------------------------------------------

    def create_api_key(
        self,
        tenant_id: str,
        name: str = "Default",
        scopes: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> tuple[TenantAPIKey, str]:
        """
        Create a new API key for a tenant.

        Args:
            tenant_id: Tenant ID
            name: Key name/description
            scopes: Permission scopes
            expires_at: Optional expiration datetime

        Returns:
            Tuple of (TenantAPIKey, raw_api_key)
            Note: The raw API key is only returned once!
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")

        # Check quota
        existing_keys = self.list_api_keys(tenant_id)
        if len(existing_keys) >= tenant.max_api_keys:
            raise ValueError(f"API key quota exceeded. Maximum: {tenant.max_api_keys}")

        # Generate API key
        raw_key = CredentialManager.generate_api_key()
        key_hash = CredentialManager.hash_api_key(raw_key)

        api_key = TenantAPIKey(
            tenant_id=tenant_id,
            key_hash=key_hash,
            key_prefix=raw_key[:8],
            name=name,
            scopes=scopes or ["read", "write"],
            expires_at=expires_at,
        )

        # Save to keys file
        self._save_api_key(api_key)

        return api_key, raw_key

    def _save_api_key(self, api_key: TenantAPIKey) -> None:
        """Save an API key to storage."""
        keys_file = self._get_api_keys_file()

        keys = {}
        if keys_file.exists():
            with open(keys_file, "r", encoding="utf-8") as f:
                keys = yaml.safe_load(f) or {}

        keys[api_key.id] = api_key.model_dump(mode="json")

        with open(keys_file, "w", encoding="utf-8") as f:
            yaml.dump(keys, f, allow_unicode=True)

    def validate_api_key(self, raw_key: str) -> Optional[TenantAPIKey]:
        """
        Validate an API key and return the associated key object.

        Args:
            raw_key: The raw API key to validate

        Returns:
            TenantAPIKey if valid, None otherwise
        """
        if not raw_key:
            return None

        key_hash = CredentialManager.hash_api_key(raw_key)

        # Check cache first
        if key_hash in self._api_key_cache:
            api_key = self._api_key_cache[key_hash]
            if self._is_key_valid(api_key):
                return api_key
            return None

        # Load from storage
        keys_file = self._get_api_keys_file()
        if not keys_file.exists():
            return None

        with open(keys_file, "r", encoding="utf-8") as f:
            keys = yaml.safe_load(f) or {}

        for key_data in keys.values():
            api_key = TenantAPIKey(**key_data)
            if api_key.key_hash == key_hash:
                if self._is_key_valid(api_key):
                    # Cache the valid key
                    self._api_key_cache[key_hash] = api_key
                    return api_key
                return None

        return None

    def _is_key_valid(self, api_key: TenantAPIKey) -> bool:
        """Check if an API key is currently valid."""
        if api_key.status != "active":
            return False
        if api_key.expires_at and api_key.expires_at < datetime.now():
            return False
        return True

    def list_api_keys(self, tenant_id: str) -> List[TenantAPIKey]:
        """List all API keys for a tenant."""
        keys_file = self._get_api_keys_file()
        if not keys_file.exists():
            return []

        with open(keys_file, "r", encoding="utf-8") as f:
            keys = yaml.safe_load(f) or {}

        return [
            TenantAPIKey(**data) for data in keys.values() if data.get("tenant_id") == tenant_id
        ]

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        keys_file = self._get_api_keys_file()
        if not keys_file.exists():
            return False

        with open(keys_file, "r", encoding="utf-8") as f:
            keys = yaml.safe_load(f) or {}

        if key_id not in keys:
            return False

        keys[key_id]["status"] = "revoked"

        with open(keys_file, "w", encoding="utf-8") as f:
            yaml.dump(keys, f, allow_unicode=True)

        # Clear from cache
        key_hash = keys[key_id].get("key_hash")
        if key_hash in self._api_key_cache:
            del self._api_key_cache[key_hash]

        return True

    def _revoke_tenant_api_keys(self, tenant_id: str) -> None:
        """Revoke all API keys for a tenant."""
        for api_key in self.list_api_keys(tenant_id):
            self.revoke_api_key(api_key.id)

    # -------------------------------------------------------------------------
    # LLM Configuration
    # -------------------------------------------------------------------------

    def get_llm_config(self, tenant_id: str) -> Optional[TenantLLMConfig]:
        """
        Get LLM configuration for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            TenantLLMConfig or None if not configured
        """
        config_path = self._get_tenant_config_path(tenant_id)
        if not config_path.exists():
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = TenantConfig(**data)
        return config.llm_config

    def set_llm_config(
        self,
        tenant_id: str,
        provider: str,
        api_key: str,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> TenantLLMConfig:
        """
        Set LLM configuration for a tenant.

        Args:
            tenant_id: Tenant ID
            provider: LLM provider (anthropic, azure_openai, openai)
            api_key: API key (will be encrypted)
            model: Optional model name
            **kwargs: Additional provider-specific config

        Returns:
            The saved TenantLLMConfig
        """
        config_path = self._get_tenant_config_path(tenant_id)
        if not config_path.exists():
            raise ValueError(f"Tenant not found: {tenant_id}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = TenantConfig(**data)

        # Create LLM config with encrypted API key
        llm_config = TenantLLMConfig(
            provider=provider,
            model=model or TenantLLMConfig.model_fields["model"].default,
            api_key_encrypted=self._credential_manager.encrypt(api_key),
            azure_endpoint=kwargs.get("azure_endpoint"),
            azure_deployment=kwargs.get("azure_deployment"),
            azure_api_version=kwargs.get(
                "azure_api_version",
                TenantLLMConfig.model_fields["azure_api_version"].default,
            ),
            temperature=kwargs.get(
                "temperature",
                TenantLLMConfig.model_fields["temperature"].default,
            ),
            max_tokens=kwargs.get(
                "max_tokens",
                TenantLLMConfig.model_fields["max_tokens"].default,
            ),
        )

        config.llm_config = llm_config

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                config.model_dump(mode="json"),
                f,
                allow_unicode=True,
                sort_keys=False,
            )

        return llm_config

    def get_decrypted_llm_api_key(self, tenant_id: str) -> Optional[str]:
        """
        Get the decrypted LLM API key for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Decrypted API key or None
        """
        llm_config = self.get_llm_config(tenant_id)
        if not llm_config or not llm_config.api_key_encrypted:
            return None

        return self._credential_manager.decrypt(llm_config.api_key_encrypted)

    # -------------------------------------------------------------------------
    # Connector Credentials
    # -------------------------------------------------------------------------

    def get_connector_credentials(
        self,
        tenant_id: str,
        connector_type: str,
    ) -> Optional[Dict[str, str]]:
        """
        Get decrypted connector credentials for a tenant.

        Args:
            tenant_id: Tenant ID
            connector_type: Connector type (bluesky, twitter, etc.)

        Returns:
            Decrypted credentials dict or None
        """
        config_path = self._get_tenant_config_path(tenant_id)
        if not config_path.exists():
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = TenantConfig(**data)
        connector_config = config.connectors.get(connector_type)

        if not connector_config:
            return None

        # Decrypt credentials
        return self._credential_manager.decrypt_dict(connector_config.credentials_encrypted)

    def set_connector_credentials(
        self,
        tenant_id: str,
        connector_type: str,
        credentials: Dict[str, str],
    ) -> TenantConnectorCredentials:
        """
        Set connector credentials for a tenant.

        Args:
            tenant_id: Tenant ID
            connector_type: Connector type
            credentials: Credential key-value pairs (will be encrypted)

        Returns:
            The saved TenantConnectorCredentials
        """
        config_path = self._get_tenant_config_path(tenant_id)
        if not config_path.exists():
            raise ValueError(f"Tenant not found: {tenant_id}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = TenantConfig(**data)

        # Create connector config with encrypted credentials
        connector_config = TenantConnectorCredentials(
            connector_type=connector_type,
            credentials_encrypted=self._credential_manager.encrypt_dict(credentials),
        )

        config.connectors[connector_type] = connector_config

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                config.model_dump(mode="json"),
                f,
                allow_unicode=True,
                sort_keys=False,
            )

        return connector_config

    def delete_connector_credentials(
        self,
        tenant_id: str,
        connector_type: str,
    ) -> bool:
        """
        Delete connector credentials for a tenant.

        Args:
            tenant_id: Tenant ID
            connector_type: Connector type

        Returns:
            True if deleted
        """
        config_path = self._get_tenant_config_path(tenant_id)
        if not config_path.exists():
            return False

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = TenantConfig(**data)

        if connector_type not in config.connectors:
            return False

        del config.connectors[connector_type]

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                config.model_dump(mode="json"),
                f,
                allow_unicode=True,
                sort_keys=False,
            )

        return True

    def list_configured_connectors(self, tenant_id: str) -> List[str]:
        """
        List connector types configured for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            List of connector type names
        """
        config_path = self._get_tenant_config_path(tenant_id)
        if not config_path.exists():
            return []

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = TenantConfig(**data)
        return list(config.connectors.keys())


# Global tenant manager instance (lazy initialization)
_tenant_manager: Optional[TenantManager] = None


def get_tenant_manager(kb_path: Optional[str] = None) -> TenantManager:
    """
    Get or create the global tenant manager instance.

    Args:
        kb_path: Optional knowledge base path

    Returns:
        The global TenantManager instance
    """
    global _tenant_manager

    if _tenant_manager is None:
        _tenant_manager = TenantManager(kb_path or "./knowledges")

    return _tenant_manager
