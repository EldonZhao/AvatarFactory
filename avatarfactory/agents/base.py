"""
Base Agent class and utilities for all AvatarFactory agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from avatarfactory.core.knowledge_base import KnowledgeBase
from avatarfactory.core.llm_provider import BaseLLMProvider, LLMProviderFactory
from avatarfactory.models.schemas import AgentMessage


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
