"""
Tests for Orchestrator direct intent parsing and execution paths.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

from avatarfactory.agents.orchestrator import OrchestratorAgent
from avatarfactory.core.knowledges import KnowledgeBase
from avatarfactory.core.llm_provider import BaseLLMProvider
from avatarfactory.models.schemas import (
    Boundaries,
    ContentPillar,
    Identity,
    Persona,
    TargetAudience,
    VoiceStyle,
)
from avatarfactory.scheduler.engine import ScheduledTask


class MockLLMProvider(BaseLLMProvider):
    """Minimal mock provider for agent initialization."""

    def __init__(self) -> None:
        super().__init__(model="mock")

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 4096,
        images: Optional[List[str]] = None,
    ) -> str:
        return '{"intent_type":"help","parameters":{},"confidence":0.5}'

    def validate_config(self) -> bool:
        return True


class FakeScheduler:
    """Simple in-memory scheduler stub for unit tests."""

    def __init__(self, tasks: Optional[List[ScheduledTask]] = None) -> None:
        self._tasks = list(tasks or [])
        self.add_calls: List[Dict[str, Any]] = []

    def list_tasks(self) -> List[ScheduledTask]:
        return list(self._tasks)

    async def add_task_from_dict(self, task_dict: Dict[str, Any]) -> ScheduledTask:
        self.add_calls.append(task_dict)
        task = ScheduledTask(**task_dict)
        self._tasks.append(task)
        return task


def _build_persona(persona_id: str) -> Persona:
    return Persona(
        id=persona_id,
        version="v1.0",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        identity=Identity(
            name="测试人设",
            tagline="用于Orchestrator测试",
            expertise=["新能源"],
        ),
        target_audience=TargetAudience(primary="从业者", pain_points=["信息噪声"], goals=["快速洞察"]),
        voice_style=VoiceStyle(tone="专业友好", language_patterns=["中文"], emoji_usage="minimal"),
        content_pillars=[ContentPillar(name="行业洞察", description="洞察", frequency="daily")],
        boundaries=Boundaries(avoid=["夸大宣传"], compliance=["事实准确"]),
        metadata={
            "prompt_preferences": {
                "language": "zh-CN-only",
                "allow_colloquial": True,
                "base_prompt": "请全中文并支持口语化表达。",
                "style_keywords": ["中文", "口语化"],
                "avoid_words": [],
            }
        },
    )


@pytest.fixture
def orchestrator() -> OrchestratorAgent:
    with tempfile.TemporaryDirectory() as tmpdir:
        kb = KnowledgeBase(tmpdir)
        kb.save_persona(_build_persona("persona_test_direct"))
        yield OrchestratorAgent(knowledge_base=kb, llm_provider=MockLLMProvider())


def test_parse_prompt_show_intent(orchestrator: OrchestratorAgent) -> None:
    intent = orchestrator._parse_direct_intent("查看prompt配置")
    assert intent is not None
    assert intent.intent_type == "prompt_config"
    assert intent.parameters["operation"] == "show"


def test_parse_evolution_review_and_rollback(orchestrator: OrchestratorAgent) -> None:
    approve = orchestrator._parse_direct_intent("批准建议 abc12345")
    assert approve is not None
    assert approve.intent_type == "review_suggestion"
    assert approve.parameters["suggestion_id"] == "abc12345"
    assert approve.parameters["approved"] is True

    rollback = orchestrator._parse_direct_intent("回滚到 v1.2")
    assert rollback is not None
    assert rollback.intent_type == "rollback"
    assert rollback.parameters["version"] == "v1.2"


@pytest.mark.asyncio
async def test_direct_intent_path_works_without_llm(orchestrator: OrchestratorAgent) -> None:
    async def _boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("should not call llm intent classifier")

    # For direct-intent command, _understand_intent must not be called.
    orchestrator._understand_intent = _boom  # type: ignore[assignment]

    result = await orchestrator._handle_user_input(
        "查看prompt配置",
        context={"persona_id": "persona_test_direct"},
    )
    assert result["status"] == "success"
    assert "Prompt 配置" in result["data"]["message"]


@pytest.mark.asyncio
async def test_scheduler_bundle_reuses_existing_tasks(orchestrator: OrchestratorAgent) -> None:
    existing_tasks = [
        ScheduledTask(
            id="topic_keep01",
            name="周期发现热点",
            task_type="topic",
            schedule="0 9 * * *",
            enabled=True,
            persona_id="persona_test_direct",
            platform="bluesky",
            extra_params={"limit": 20},
        ),
        ScheduledTask(
            id="publish_keep01",
            name="周期发布内容",
            task_type="publish",
            schedule="0 18 * * *",
            enabled=True,
            persona_id="persona_test_direct",
            platform="bluesky",
            extra_params={},
        ),
    ]
    scheduler = FakeScheduler(tasks=existing_tasks)
    orchestrator._get_runtime_scheduler = lambda: scheduler  # type: ignore[assignment]

    result = await orchestrator._handle_scheduler_manage(
        {"operation": "create_bundle", "persona_id": "persona_test_direct"},
        "为这个persona创建周期发现和发布任务",
    )
    assert len(scheduler.add_calls) == 0
    assert "不会重复创建" in result["message"]
    assert len(result["tasks"]) == 2
