"""
Base Agent class and utilities for all AvatarFactory agents.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from avatarfactory.core.knowledges import KnowledgeBase
from avatarfactory.core.llm_provider import BaseLLMProvider, LLMProviderFactory
from avatarfactory.models.schemas import AgentMessage


@dataclass
class PublishResult:
    """Result of a multi-platform publish operation."""
    platform: str
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None


class BaseAgent(ABC):
    """Base class for all agents in AvatarFactory"""

    def __init__(
        self,
        agent_id: str,
        knowledge_base: KnowledgeBase,
        llm_provider: Optional[BaseLLMProvider] = None,
        # Deprecated parameters (kept for backward compatibility)
        anthropic_client: Optional[Any] = None,
        model: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.kb = knowledge_base

        # Use new LLM provider system
        if llm_provider:
            self.llm_provider = llm_provider
        else:
            # Backward compatibility: create from environment or defaults
            self.llm_provider = LLMProviderFactory.from_env()

        self.logger = logging.getLogger(f"avatarfactory.agents.{agent_id}")

        # Multi-connector support
        self._connectors: Dict[str, Any] = {}

    @abstractmethod
    async def process(self, message: AgentMessage) -> Any:
        """
        Process an incoming message and return result.

        Args:
            message: AgentMessage containing task information

        Returns:
            Task-specific result (varies by agent and task type)
        """
        pass

    def log(self, level: str, message: str, **kwargs: Any) -> None:
        """
        Unified logging interface.

        Args:
            level: Log level (DEBUG/INFO/WARNING/ERROR)
            message: Log message
            **kwargs: Additional context to log
        """
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        if kwargs:
            message = f"{message} | {kwargs}"
        log_func(message)

    async def call_llm(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
    ) -> str:
        """
        Call LLM with the given prompt.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            LLM response text
        """
        try:
            return await self.llm_provider.generate(
                prompt=prompt,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            self.log("ERROR", f"LLM call failed: {e}")
            raise

    def get_persona_context(self, persona_id: str) -> Dict[str, Any]:
        """
        Get persona context from knowledge base.

        Args:
            persona_id: Persona ID

        Returns:
            Dictionary containing persona data
        """
        persona = self.kb.load_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")
        return persona.model_dump()

    def validate_message(self, message: AgentMessage) -> bool:
        """
        Validate that a message is intended for this agent.

        Args:
            message: Message to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        if message.receiver != self.agent_id:
            raise ValueError(
                f"Message intended for {message.receiver}, but received by {self.agent_id}"
            )
        return True

    # =========================================================================
    # Multi-Connector Support
    # =========================================================================

    def add_connector(self, name: str, connector: Any) -> None:
        """
        Add a platform connector to this agent.

        Args:
            name: Connector name/identifier
            connector: BasePlatformConnector instance
        """
        self._connectors[name.lower()] = connector
        self.log("DEBUG", f"Added connector: {name}")

    def get_connector(self, name: str) -> Optional[Any]:
        """
        Get a connector by name.

        Args:
            name: Connector name

        Returns:
            Connector instance or None
        """
        return self._connectors.get(name.lower())

    def list_connectors(self) -> List[str]:
        """
        List all registered connector names.

        Returns:
            List of connector names
        """
        return list(self._connectors.keys())

    def remove_connector(self, name: str) -> bool:
        """
        Remove a connector by name.

        Args:
            name: Connector name

        Returns:
            True if removed, False if not found
        """
        if name.lower() in self._connectors:
            del self._connectors[name.lower()]
            return True
        return False

    async def publish_to_platforms(
        self,
        content: str,
        platforms: List[str],
        title: Optional[str] = None,
        images: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, "PublishResult"]:
        """
        Publish content to multiple platforms.

        Args:
            content: Content text to publish
            platforms: List of platform names to publish to
            title: Optional title (for platforms that support it)
            images: Optional list of image paths
            tags: Optional list of tags/hashtags

        Returns:
            Dict mapping platform name to PublishResult
        """
        results: Dict[str, PublishResult] = {}

        for platform in platforms:
            connector = self.get_connector(platform)
            if not connector:
                results[platform] = PublishResult(
                    platform=platform,
                    success=False,
                    error=f"No connector registered for platform: {platform}",
                )
                continue

            try:
                if not connector.is_connected():
                    await connector.connect()

                result = await connector.publish(
                    content=content,
                    title=title,
                    images=images,
                    tags=tags,
                )

                results[platform] = PublishResult(
                    platform=platform,
                    success=result.success,
                    post_id=result.post_id,
                    post_url=result.post_url,
                    error=result.error,
                )

            except Exception as e:
                self.log("ERROR", f"Failed to publish to {platform}: {e}")
                results[platform] = PublishResult(
                    platform=platform,
                    success=False,
                    error=str(e),
                )

        return results
