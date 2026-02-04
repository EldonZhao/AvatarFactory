"""
Review Agent - Content review, compliance checking, and scoring.
"""

import json
from datetime import datetime
from typing import Any, Dict

from avatarfactory.agents.base import BaseAgent
from avatarfactory.models.schemas import (
    AgentMessage,
    ComplianceCheck,
    Content,
    DimensionScore,
    Persona,
    ReviewReport,
    RiskLevel,
    TaskType,
)


class ReviewAgent(BaseAgent):
    """Agent responsible for content review and compliance"""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(agent_id="review", *args, **kwargs)

    async def process(self, message: AgentMessage) -> Any:
        """Process review tasks"""
        self.validate_message(message)

        if message.task_type == TaskType.REVIEW_CONTENT:
            return await self._review_content(message.payload, message.context)
        else:
            raise ValueError(f"Unknown task type: {message.task_type}")

    async def _review_content(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> ReviewReport:
        """
        Review content across multiple dimensions.

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

        self.log("INFO", f"Reviewing content {content_id}")

        # Perform review using LLM
        system_prompt = """You are a professional content reviewer. Review the content across four dimensions:

1. PERSONA CONSISTENCY: How well does the content match the persona's voice, expertise, and positioning?
2. PLATFORM FIT: How well is the content optimized for the target platform?
3. COMPLIANCE: Are there any risks (sensitive words, misleading claims, spam patterns)?
4. ENGAGEMENT POTENTIAL: How likely is this content to engage the target audience?

For each dimension, provide:
- score (0-100)
- issues (list of problems found)
- strengths (list of good points)
- reasoning (why this score)

Output MUST be valid JSON:
{
  "persona_consistency": {
    "score": <0-100>,
    "issues": [],
    "strengths": [],
    "reasoning": []
  },
  "platform_fit": {
    "score": <0-100>,
    "issues": [],
    "strengths": [],
    "reasoning": []
  },
  "compliance": {
    "score": <0-100>,
    "risk_level": "low|medium|high",
    "checks": {
      "sensitive_words": "pass|fail",
      "misleading_claims": "pass|fail",
      "spam_patterns": "pass|fail"
    },
    "issues": []
  },
  "engagement_potential": {
    "score": <0-100>,
    "issues": [],
    "strengths": [],
    "reasoning": []
  },
  "suggestions": {
    "critical": [],
    "recommended": [],
    "optional": []
  }
}"""

        user_prompt = f"""CONTENT TO REVIEW:
Title: {content.title}
Body: {content.body}
Platform: {content.platform.value}

PERSONA:
- Identity: {persona.identity.name} - {persona.identity.tagline}
- Voice: {persona.voice_style.tone}
- Language Patterns: {', '.join(persona.voice_style.language_patterns)}
- Target Audience: {persona.target_audience.primary}
- Boundaries to Avoid: {', '.join(persona.boundaries.avoid)}
- Compliance Rules: {', '.join(persona.boundaries.compliance)}

Provide comprehensive review in JSON format."""

        response = await self.call_llm(user_prompt, system=system_prompt, temperature=0.3)

        # Parse response
        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            review_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.log("ERROR", f"Failed to parse review JSON: {e}")
            raise ValueError(f"Failed to generate review: {e}")

        # Create review report
        report = ReviewReport(
            content_id=content_id,
            reviewed_at=datetime.now(),
            persona_consistency=DimensionScore(**review_data["persona_consistency"]),
            platform_fit=DimensionScore(**review_data["platform_fit"]),
            compliance=ComplianceCheck(
                score=review_data["compliance"]["score"],
                risk_level=RiskLevel(review_data["compliance"]["risk_level"]),
                checks=review_data["compliance"].get("checks", {}),
                issues=review_data["compliance"].get("issues", []),
            ),
            engagement_potential=DimensionScore(**review_data["engagement_potential"]),
            overall_score=self._calculate_overall_score(review_data),
            suggestions=review_data.get("suggestions", {}),
        )

        # Save review report
        self.kb.save_review_report(report, persona_id)

        # Update content with review results
        content.review_score = report.overall_score
        content.review_issues = (
            report.persona_consistency.issues
            + report.platform_fit.issues
            + report.compliance.issues
            + report.engagement_potential.issues
        )
        self.kb.save_content(content, status="draft")

        self.log("INFO", f"Review complete. Overall score: {report.overall_score}")
        return report

    def _calculate_overall_score(self, review_data: Dict[str, Any]) -> int:
        """Calculate weighted overall score"""
        weights = {
            "persona_consistency": 0.3,
            "platform_fit": 0.25,
            "compliance": 0.3,  # Higher weight for compliance
            "engagement_potential": 0.15,
        }

        total = 0.0
        for dimension, weight in weights.items():
            score = review_data.get(dimension, {}).get("score", 0)
            total += score * weight

        return int(total)
