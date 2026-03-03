"""
AvatarFactory Agents.

Multi-agent system for persona management and content generation.
"""

from avatarfactory.agents.base import BaseAgent
from avatarfactory.agents.discovery import DiscoveryAgent
from avatarfactory.agents.persona import PersonaAgent, PersonaLabAgent
from avatarfactory.agents.content import ContentAgent, ContentLabAgent
from avatarfactory.agents.recommendation import RecommendationAgent

__all__ = [
    "BaseAgent",
    "DiscoveryAgent",
    "PersonaAgent",
    "ContentAgent",
    "RecommendationAgent",
    # Deprecated aliases for backward compatibility
    "PersonaLabAgent",
    "ContentLabAgent",
]
