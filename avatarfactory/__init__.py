"""
AvatarFactory - A Persona Factory for social platforms.

This package helps you design, simulate, evaluate, and evolve social personas (avatars)
across different platforms.
"""

__version__ = "0.1.0"
__author__ = "AvatarFactory Team"
__license__ = "MIT"

from avatarfactory.agents.orchestrator import OrchestratorAgent
from avatarfactory.core.knowledges import KnowledgeBase
from avatarfactory.models.schemas import (
    Content,
    Persona,
    ReviewReport,
)

__all__ = [
    "OrchestratorAgent",
    "KnowledgeBase",
    "Persona",
    "Content",
    "ReviewReport",
]
