"""
Multi-tenant KnowledgeBase wrapper.

Provides tenant-isolated access to the KnowledgeBase.
This is a separate class to avoid modifying the core KnowledgeBase.
"""

from pathlib import Path
from typing import Optional

from avatarfactory.core.knowledges import KnowledgeBase


class TenantKnowledgeBase(KnowledgeBase):
    """
    Tenant-aware KnowledgeBase that isolates data per tenant.

    Each tenant's data is stored in a separate subdirectory:
    - {base_path}/default/ - Default tenant (backward compatible)
    - {base_path}/{tenant_id}/ - Other tenants

    For the default tenant, data remains at the root for backward compatibility.
    """

    def __init__(
        self,
        base_path: str = "./knowledges",
        tenant_id: str = "default",
    ):
        """
        Initialize tenant-aware knowledge base.

        Args:
            base_path: Root path for all tenant data
            tenant_id: Tenant ID for data isolation
        """
        self.root_path = Path(base_path)
        self.tenant_id = tenant_id

        # For default tenant, use root path for backward compatibility
        # For other tenants, use subdirectory
        if tenant_id == "default":
            effective_path = base_path
        else:
            effective_path = str(self.root_path / tenant_id)

        # Initialize parent class with the effective path
        super().__init__(effective_path)

    @classmethod
    def for_tenant(
        cls,
        tenant_id: str,
        base_path: Optional[str] = None,
    ) -> "TenantKnowledgeBase":
        """
        Factory method to create a KnowledgeBase for a specific tenant.

        Args:
            tenant_id: Tenant ID
            base_path: Optional base path (defaults to AVATARFACTORY_KB_PATH or ./knowledges)

        Returns:
            TenantKnowledgeBase instance for the tenant
        """
        import os

        if base_path is None:
            base_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")

        return cls(base_path=base_path, tenant_id=tenant_id)
