"""
Agent Configuration Manager for AvatarFactory.

Manages per-persona agent configurations for customizing agent behavior.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from avatarfactory.core.knowledges import KnowledgeBase
from avatarfactory.models.schemas import AgentConfig


class AgentConfigManager:
    """
    Manager for per-persona agent configurations.

    Handles loading, saving, and applying agent configurations
    that customize LLM behavior for each persona.
    """

    # Default configurations for each agent type
    DEFAULT_CONFIGS: Dict[str, Dict[str, Any]] = {
        "content": {
            "agent_type": "content",
            "temperature": 0.7,
            "max_tokens": 4096,
            "creativity_level": "balanced",
            "detail_level": "standard",
        },
        "review": {
            "agent_type": "review",
            "temperature": 0.3,
            "max_tokens": 2048,
            "creativity_level": "conservative",
            "detail_level": "detailed",
        },
        "topic": {
            "agent_type": "topic",
            "temperature": 0.5,
            "max_tokens": 4096,
            "creativity_level": "balanced",
            "detail_level": "standard",
        },
    }

    def __init__(self, knowledge_base: KnowledgeBase):
        """
        Initialize the AgentConfigManager.

        Args:
            knowledge_base: KnowledgeBase instance for persistence
        """
        self.kb = knowledge_base

    def get_config(
        self, persona_id: str, agent_type: str
    ) -> AgentConfig:
        """
        Get agent configuration for a persona.

        Returns the persona-specific config if available,
        otherwise returns default config for the agent type.

        Args:
            persona_id: Persona ID
            agent_type: Agent type (content, review, topic)

        Returns:
            AgentConfig for the agent
        """
        # Try to load persona-specific config
        config = self.kb.load_agent_config(persona_id, agent_type)
        if config is not None:
            return config

        # Return default config
        return self.get_default_config(agent_type)

    def get_default_config(self, agent_type: str) -> AgentConfig:
        """
        Get default configuration for an agent type.

        Args:
            agent_type: Agent type (content, review, topic)

        Returns:
            Default AgentConfig for the agent type
        """
        default = self.DEFAULT_CONFIGS.get(
            agent_type,
            {
                "agent_type": agent_type,
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        )
        return AgentConfig(**default)

    def save_config(
        self, persona_id: str, agent_type: str, config: AgentConfig
    ) -> None:
        """
        Save agent configuration for a persona.

        Args:
            persona_id: Persona ID
            agent_type: Agent type (content, review, topic)
            config: AgentConfig to save
        """
        self.kb.save_agent_config(persona_id, agent_type, config)

    def update_config(
        self,
        persona_id: str,
        agent_type: str,
        updates: Dict[str, Any],
    ) -> AgentConfig:
        """
        Update specific fields of an agent configuration.

        Args:
            persona_id: Persona ID
            agent_type: Agent type
            updates: Dictionary of fields to update

        Returns:
            Updated AgentConfig
        """
        # Load current config
        config = self.get_config(persona_id, agent_type)
        config_dict = config.model_dump()

        # Apply updates
        for key, value in updates.items():
            if key in config_dict:
                config_dict[key] = value

        # Create new config
        updated_config = AgentConfig(**config_dict)

        # Save
        self.save_config(persona_id, agent_type, updated_config)
        return updated_config

    def apply_llm_params(
        self,
        persona_id: Optional[str],
        agent_type: str,
        base_temperature: float = 0.7,
        base_max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Get LLM parameters to apply for a call.

        Merges base parameters with persona-specific config.

        Args:
            persona_id: Persona ID (optional, uses defaults if None)
            agent_type: Agent type
            base_temperature: Default temperature
            base_max_tokens: Default max tokens

        Returns:
            Dict with temperature, max_tokens, and optional system_prompt_additions
        """
        if persona_id is None:
            return {
                "temperature": base_temperature,
                "max_tokens": base_max_tokens,
            }

        config = self.get_config(persona_id, agent_type)

        # Adjust temperature based on creativity level
        temperature = config.temperature
        if config.creativity_level == "conservative":
            temperature = min(temperature, 0.4)
        elif config.creativity_level == "creative":
            temperature = max(temperature, 0.8)

        result = {
            "temperature": temperature,
            "max_tokens": config.max_tokens,
        }

        # Include system prompt additions if present
        if config.system_prompt_additions:
            result["system_prompt_additions"] = config.system_prompt_additions

        # Include style emphasis and avoid patterns
        if config.style_emphasis:
            result["style_emphasis"] = config.style_emphasis
        if config.avoid_patterns:
            result["avoid_patterns"] = config.avoid_patterns

        return result

    def record_performance(
        self,
        persona_id: str,
        agent_type: str,
        metrics: Dict[str, Any],
    ) -> None:
        """
        Record performance metrics for an agent.

        Used for tracking how well the current config performs.

        Args:
            persona_id: Persona ID
            agent_type: Agent type
            metrics: Performance metrics to record
        """
        config = self.get_config(persona_id, agent_type)

        # Add timestamp
        record = {
            "timestamp": datetime.now().isoformat(),
            **metrics,
        }

        # Append to history (keep last 100 records)
        config.performance_history.append(record)
        if len(config.performance_history) > 100:
            config.performance_history = config.performance_history[-100:]

        # Save updated config
        self.save_config(persona_id, agent_type, config)

    def get_performance_summary(
        self, persona_id: str, agent_type: str
    ) -> Dict[str, Any]:
        """
        Get performance summary for an agent.

        Args:
            persona_id: Persona ID
            agent_type: Agent type

        Returns:
            Dict with performance summary statistics
        """
        config = self.get_config(persona_id, agent_type)
        history = config.performance_history

        if not history:
            return {
                "record_count": 0,
                "avg_score": None,
            }

        # Calculate averages for numeric metrics
        scores = [r.get("score") for r in history if r.get("score") is not None]
        avg_score = sum(scores) / len(scores) if scores else None

        return {
            "record_count": len(history),
            "avg_score": avg_score,
            "latest_record": history[-1] if history else None,
        }
