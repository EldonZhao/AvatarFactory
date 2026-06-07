"""
LLM Provider abstraction layer - supports multiple LLM providers.

Supported providers:
- Anthropic Claude (claude-3-5-sonnet, claude-3-5-haiku, etc.)
- Azure OpenAI (GPT-4, GPT-3.5, etc.)
- OpenAI (GPT-4, GPT-3.5, etc.)

All providers support multimodal input (text + images) via the `images` parameter.
"""

import base64
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from anthropic import Anthropic


def _resolve_image_content(image: str) -> Dict[str, Any]:
    """
    Resolve an image reference to a content dict suitable for LLM APIs.

    Supports:
    - URLs (http:// or https://) → returned as-is
    - Local file paths → read and base64-encoded
    - Base64 strings (data:image/...) → returned as-is

    Args:
        image: URL, file path, or base64 data URI

    Returns:
        Dict with 'type' and 'data'/'url' keys for API consumption
    """
    if image.startswith(("http://", "https://")):
        return {"type": "url", "url": image}
    elif image.startswith("data:"):
        # Already a data URI (e.g., data:image/png;base64,...)
        return {"type": "base64", "data_uri": image}
    else:
        # Assume local file path
        path = Path(image)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {image}")

        # Detect MIME type from extension
        ext_to_mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = ext_to_mime.get(path.suffix.lower(), "image/png")

        # Guard against excessively large files (20 MB limit)
        max_size = 20 * 1024 * 1024
        file_size = path.stat().st_size
        if file_size > max_size:
            raise ValueError(
                f"Image file too large ({file_size / 1024 / 1024:.1f} MB). "
                f"Maximum allowed size is {max_size / 1024 / 1024:.0f} MB."
            )

        with open(path, "rb") as f:
            b64_data = base64.standard_b64encode(f.read()).decode("utf-8")
        return {
            "type": "base64",
            "data_uri": f"data:{mime_type};base64,{b64_data}",
            "mime_type": mime_type,
            "base64_data": b64_data,
        }


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""

    def __init__(self, model: str, **kwargs: Any):
        self.model = model
        self.config = kwargs

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        images: Optional[List[str]] = None,
    ) -> str:
        """
        Generate text from the LLM.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            images: Optional list of image references (URLs, file paths, or
                    base64 data URIs) for multimodal/vision input

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration"""
        pass


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider"""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        super().__init__(model)
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        images: Optional[List[str]] = None,
    ) -> str:
        try:
            # Build user content: text-only or multimodal (text + images)
            if images:
                content_blocks: List[Dict[str, Any]] = []
                for img in images:
                    resolved = _resolve_image_content(img)
                    if resolved["type"] == "url":
                        content_blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "url",
                                    "url": resolved["url"],
                                },
                            }
                        )
                    else:
                        # base64 data
                        content_blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": resolved.get("mime_type", "image/png"),
                                    "data": resolved["base64_data"],
                                },
                            }
                        )
                content_blocks.append({"type": "text", "text": prompt})
                user_content: Union[str, List[Dict[str, Any]]] = content_blocks
            else:
                user_content = prompt

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else [],
                messages=[{"role": "user", "content": user_content}],
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic API call failed: {e}")

    def validate_config(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI provider"""

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_version: str = "2024-02-15-preview",
    ):
        super().__init__(model)
        try:
            from openai import AsyncAzureOpenAI
        except ImportError:
            raise ImportError(
                "openai package required for Azure OpenAI. Install with: pip install openai"
            )

        self.client = AsyncAzureOpenAI(
            api_key=api_key or os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=endpoint or os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=api_version,
        )

        # Detect if model is a reasoning model (o1, gpt-5, etc.) that doesn't support temperature
        self._is_reasoning_model = any(
            x in model.lower() for x in ["o1", "o3", "gpt-5", "reasoning"]
        )

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        images: Optional[List[str]] = None,
    ) -> str:
        try:
            messages: List[Dict[str, Any]] = []
            if system:
                messages.append({"role": "system", "content": system})

            # Build user message: text-only or multimodal (vision)
            if images:
                user_content: List[Dict[str, Any]] = []
                for img in images:
                    resolved = _resolve_image_content(img)
                    if resolved["type"] == "url":
                        image_url = resolved["url"]
                    else:
                        image_url = resolved["data_uri"]
                    user_content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        }
                    )
                user_content.append({"type": "text", "text": prompt})
                messages.append({"role": "user", "content": user_content})
            else:
                messages.append({"role": "user", "content": prompt})

            # Build kwargs based on model type
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "max_completion_tokens": max_tokens,
            }

            # Reasoning models (o1, gpt-5) don't support temperature
            if not self._is_reasoning_model:
                kwargs["temperature"] = temperature

            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            # Handle unsupported parameters by retrying without them
            if "temperature" in error_str and "unsupported" in error_str.lower():
                # Retry without temperature
                try:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_completion_tokens=max_tokens,
                    )
                    return response.choices[0].message.content
                except Exception as e2:
                    raise RuntimeError(f"Azure OpenAI API call failed: {e2}")
            elif "max_completion_tokens" in error_str:
                # Try with max_tokens instead
                try:
                    kwargs_fallback: Dict[str, Any] = {
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                    }
                    if not self._is_reasoning_model:
                        kwargs_fallback["temperature"] = temperature
                    response = await self.client.chat.completions.create(**kwargs_fallback)
                    return response.choices[0].message.content
                except Exception as e2:
                    raise RuntimeError(f"Azure OpenAI API call failed: {e2}")
            raise RuntimeError(f"Azure OpenAI API call failed: {e}")
            raise RuntimeError(f"Azure OpenAI API call failed: {e}")

    def validate_config(self) -> bool:
        return bool(os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"))


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider"""

    def __init__(self, model: str = "gpt-4-turbo-preview", api_key: Optional[str] = None):
        super().__init__(model)
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package required for OpenAI. Install with: pip install openai"
            )

        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        images: Optional[List[str]] = None,
    ) -> str:
        try:
            messages: List[Dict[str, Any]] = []
            if system:
                messages.append({"role": "system", "content": system})

            # Build user message: text-only or multimodal (vision)
            if images:
                user_content: List[Dict[str, Any]] = []
                for img in images:
                    resolved = _resolve_image_content(img)
                    if resolved["type"] == "url":
                        image_url = resolved["url"]
                    else:
                        image_url = resolved["data_uri"]
                    user_content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        }
                    )
                user_content.append({"type": "text", "text": prompt})
                messages.append({"role": "user", "content": user_content})
            else:
                messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}")

    def validate_config(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))


class LLMProviderFactory:
    """Factory for creating LLM providers"""

    _providers = {
        "anthropic": AnthropicProvider,
        "azure_openai": AzureOpenAIProvider,
        "openai": OpenAIProvider,
    }

    @classmethod
    def create(
        cls, provider_type: str, model: Optional[str] = None, **kwargs: Any
    ) -> BaseLLMProvider:
        """
        Create an LLM provider.

        Args:
            provider_type: Provider type (anthropic/azure_openai/openai)
            model: Model name (optional, uses default if not specified)
            **kwargs: Additional provider-specific configuration

        Returns:
            LLM provider instance

        Examples:
            # Anthropic
            provider = LLMProviderFactory.create("anthropic")

            # Azure OpenAI
            provider = LLMProviderFactory.create(
                "azure_openai",
                model="gpt-4",
                endpoint="https://your-resource.openai.azure.com/"
            )

            # OpenAI
            provider = LLMProviderFactory.create("openai", model="gpt-4-turbo-preview")
        """
        if provider_type not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider_type}. " f"Supported: {list(cls._providers.keys())}"
            )

        provider_class = cls._providers[provider_type]

        # Use model if provided, otherwise use provider default
        if model:
            kwargs["model"] = model

        return provider_class(**kwargs)

    @classmethod
    def from_env(cls) -> BaseLLMProvider:
        """
        Create provider from environment variables.

        Environment variables checked (in order):
        1. AVATARFACTORY_LLM_PROVIDER (anthropic/azure_openai/openai)
        2. AVATARFACTORY_MODEL (model name)
        3. Provider-specific API keys

        Returns:
            LLM provider instance
        """
        provider_type = os.getenv("AVATARFACTORY_LLM_PROVIDER", "anthropic").lower()
        model = os.getenv("AVATARFACTORY_MODEL")

        # Provider-specific configuration
        kwargs: Dict[str, Any] = {}
        if provider_type == "azure_openai":
            kwargs["endpoint"] = os.getenv("AZURE_OPENAI_ENDPOINT")
            kwargs["api_version"] = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

        return cls.create(provider_type, model=model, **kwargs)

    @classmethod
    def list_providers(cls) -> list[str]:
        """List available providers"""
        return list(cls._providers.keys())

    @classmethod
    def create_for_tenant(
        cls,
        tenant_id: str,
        kb_path: str = "./knowledges",
    ) -> BaseLLMProvider:
        """
        Create LLM provider for a specific tenant.

        Loads LLM configuration from the tenant's config, including
        decrypted API key and provider settings.

        If tenant has no LLM config, falls back to environment variables.

        Args:
            tenant_id: Tenant ID
            kb_path: Knowledge base path

        Returns:
            LLM provider instance configured for the tenant
        """
        # Import here to avoid circular dependency
        from avatarfactory.core.tenant import TenantManager

        tenant_manager = TenantManager(kb_path)
        llm_config = tenant_manager.get_llm_config(tenant_id)

        if not llm_config or not llm_config.api_key_encrypted:
            # Fallback to environment-based config
            return cls.from_env()

        # Decrypt the API key
        api_key = tenant_manager.get_decrypted_llm_api_key(tenant_id)

        # Build kwargs based on provider
        kwargs: Dict[str, Any] = {
            "model": llm_config.model,
            "api_key": api_key,
        }

        if llm_config.provider == "azure_openai":
            kwargs["endpoint"] = llm_config.azure_endpoint
            kwargs["api_version"] = llm_config.azure_api_version

        return cls.create(llm_config.provider, **kwargs)
