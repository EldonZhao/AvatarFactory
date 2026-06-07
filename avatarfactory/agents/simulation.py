"""
Simulation Agent - Predicts engagement and generates comment scenarios.
"""

import json
from datetime import datetime
from typing import Any, Dict, List

from avatarfactory.agents.base import BaseAgent
from avatarfactory.models.schemas import (
    AgentMessage,
    CommentScenario,
    Content,
    EngagementPrediction,
    EngagementRange,
    Persona,
    SimulationReport,
    TaskType,
)


class SimulationAgent(BaseAgent):
    """Agent responsible for engagement simulation and prediction"""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(agent_id="simulation", *args, **kwargs)

    async def process(self, message: AgentMessage) -> Any:
        """Process simulation tasks"""
        self.validate_message(message)

        if message.task_type == TaskType.PREDICT_ENGAGEMENT:
            return await self._predict_engagement(message.payload, message.context)
        else:
            raise ValueError(f"Unknown task type: {message.task_type}")

    async def _predict_engagement(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> SimulationReport:
        """
        Predict engagement for content.

        Expected payload:
            - content_id: str
            - persona_id: str
        """
        content_id = payload.get("content_id")
        persona_id = payload.get("persona_id")

        if not content_id or not persona_id:
            raise ValueError("content_id and persona_id are required")

        # Load content and persona
        content = self.kb.load_content(content_id, status="draft")
        if not content:
            raise ValueError(f"Content {content_id} not found")

        persona = self.kb.load_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        self.log("INFO", f"Simulating engagement for content {content_id}")

        # Predict engagement using LLM
        engagement_prediction = await self._predict_metrics(content, persona)

        # Generate comment scenarios
        comment_scenarios = await self._generate_comment_scenarios(content, persona)

        # Create simulation report
        report = SimulationReport(
            content_id=content_id,
            simulated_at=datetime.now(),
            engagement_prediction=engagement_prediction,
            comment_scenarios=comment_scenarios,
        )

        # Save simulation report
        self.kb.save_simulation_report(report, persona_id)

        # Update content with prediction
        content.predicted_engagement = {
            "views": engagement_prediction.views.model_dump(),
            "likes": engagement_prediction.likes.model_dump(),
            "comments": engagement_prediction.comments.model_dump(),
            "saves": engagement_prediction.saves.model_dump(),
        }
        self.kb.save_content(content, status="draft")

        self.log("INFO", "Simulation complete")
        return report

    async def _predict_metrics(self, content: Content, persona: Persona) -> EngagementPrediction:
        """Predict engagement metrics using LLM"""

        system_prompt = """You are a social media analytics expert. Predict engagement metrics for content based on:
1. Content quality and hook strength
2. Platform algorithm preferences
3. Persona's existing reach (assume early-stage: 100-1000 followers)
4. Topic competitiveness

Be realistic and conservative. For early-stage accounts:
- Views: 100-5000 range
- Likes: 2-10% of views
- Comments: 0.5-3% of views
- Saves: 1-8% of views (higher for valuable content)

Output MUST be valid JSON:
{
  "views": {"min": <int>, "likely": <int>, "max": <int>},
  "likes": {"min": <int>, "likely": <int>, "max": <int>},
  "comments": {"min": <int>, "likely": <int>, "max": <int>},
  "saves": {"min": <int>, "likely": <int>, "max": <int>},
  "confidence": "low|medium|high",
  "confidence_factors": {
    "content_quality": <0.0-1.0>,
    "topic_relevance": <0.0-1.0>,
    "platform_fit": <0.0-1.0>
  },
  "ranking_factors": {
    "hook_strength": <1-10>,
    "value_density": <1-10>,
    "shareability": <1-10>,
    "platform_optimization": <1-10>
  }
}"""

        user_prompt = f"""CONTENT:
Title: {content.title}
Body: {content.body[:500]}...
Platform: {content.platform.value}

PERSONA:
Name: {persona.identity.name}
Expertise: {', '.join(persona.identity.expertise)}
Target Audience: {persona.target_audience.primary}

Predict engagement metrics in JSON format."""

        response = await self.call_llm(user_prompt, system=system_prompt, temperature=0.5)

        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            prediction_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.log("ERROR", f"Failed to parse prediction JSON: {e}")
            # Return conservative defaults
            return EngagementPrediction(
                views=EngagementRange(min=100, likely=300, max=1000),
                likes=EngagementRange(min=5, likely=15, max=50),
                comments=EngagementRange(min=1, likely=3, max=10),
                saves=EngagementRange(min=2, likely=8, max=30),
                confidence="low",
                confidence_factors={},
                ranking_factors={},
            )

        return EngagementPrediction(
            views=EngagementRange(**prediction_data["views"]),
            likes=EngagementRange(**prediction_data["likes"]),
            comments=EngagementRange(**prediction_data["comments"]),
            saves=EngagementRange(**prediction_data["saves"]),
            confidence=prediction_data.get("confidence", "medium"),
            confidence_factors=prediction_data.get("confidence_factors", {}),
            ranking_factors=prediction_data.get("ranking_factors", {}),
        )

    async def _generate_comment_scenarios(
        self, content: Content, persona: Persona
    ) -> Dict[str, List[CommentScenario]]:
        """Generate possible comment scenarios"""

        system_prompt = """You are a social media behavior analyst. Generate realistic comment scenarios that might appear under this content.

Categories:
1. positive: Supportive comments, appreciation
2. questions: Genuine questions from readers
3. challenges: Skeptical or disagreeing comments (not hostile)

For each scenario, suggest a brief reply that maintains the persona's voice.

Output MUST be valid JSON:
{
  "positive": [
    {"text": "comment text", "probability": <0.0-1.0>, "suggested_reply": "reply text"}
  ],
  "questions": [
    {"text": "comment text", "probability": <0.0-1.0>, "suggested_reply": "reply text"}
  ],
  "challenges": [
    {"text": "comment text", "probability": <0.0-1.0>, "suggested_reply": "reply text"}
  ]
}"""

        user_prompt = f"""CONTENT:
Title: {content.title}
Body: {content.body[:400]}...

PERSONA VOICE: {persona.voice_style.tone}

Generate 2-3 scenarios per category in JSON format."""

        response = await self.call_llm(user_prompt, system=system_prompt, temperature=0.7)

        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            scenarios_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.log("WARNING", f"Failed to parse comment scenarios: {e}")
            return {
                "positive": [],
                "questions": [],
                "challenges": [],
            }

        # Convert to CommentScenario objects
        result: Dict[str, List[CommentScenario]] = {}
        for category in ["positive", "questions", "challenges"]:
            scenarios = []
            for scenario_data in scenarios_data.get(category, []):
                scenario = CommentScenario(
                    text=scenario_data["text"],
                    probability=scenario_data.get("probability", 0.5),
                    suggested_reply=scenario_data.get("suggested_reply"),
                )
                scenarios.append(scenario)
            result[category] = scenarios

        return result
