"""
Recommendation Agent for AvatarFactory.

Responsible for:
1. Analyzing trending topics from multiple platforms
2. Generating recommended persona templates based on trends
3. Identifying market opportunities and content niches
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from avatarfactory.agents.base import BaseAgent
from avatarfactory.models.schemas import (
    AgentMessage,
    RecommendedPersona,
    TrendSnapshot,
)


class RecommendationAgent(BaseAgent):
    """
    Recommendation Agent - generates persona recommendations from trending data.

    Capabilities:
    - Analyze multi-platform trend data
    - Identify high-potential persona opportunities
    - Generate structured persona templates
    - Score recommendations by relevance and potential
    """

    def __init__(self, **kwargs):
        super().__init__(agent_id="recommendation", **kwargs)

    async def process(self, message: AgentMessage) -> Dict[str, Any]:
        """Process recommendation-related messages."""
        task_type = (
            message.task_type.value
            if hasattr(message.task_type, "value")
            else str(message.task_type)
        )
        payload = message.payload

        if task_type == "generate_recommendations":
            return await self._generate_recommendations(payload)
        elif task_type == "analyze_opportunities":
            return await self._analyze_opportunities(payload)
        else:
            return {
                "status": "error",
                "message": f"Unknown task type: {task_type}",
            }

    async def generate_recommendations(
        self,
        trend_snapshots: List[TrendSnapshot],
        count: int = 3,
    ) -> List[RecommendedPersona]:
        """
        Generate persona recommendations from trend snapshots.

        Args:
            trend_snapshots: List of TrendSnapshot from various platforms
            count: Number of recommendations to generate

        Returns:
            List of RecommendedPersona
        """
        if not trend_snapshots:
            self.log("WARNING", "No trend snapshots provided for recommendations")
            return []

        # Build trending context for LLM
        trends_context = self._build_trends_context(trend_snapshots)
        platforms = list(set(s.platform for s in trend_snapshots))

        # Generate recommendations via LLM
        system_prompt = """You are an expert social media strategist and persona designer.
Your task is to analyze trending topics and patterns across social platforms,
then recommend persona templates that have high growth potential.

Focus on:
1. Identifying underserved niches with growing interest
2. Finding intersection of multiple trends
3. Designing personas that can create unique value
4. Balancing specificity with sustainable content potential"""

        user_prompt = f"""Based on the following trending data from {', '.join(platforms)},
generate {count} recommended persona templates.

## Trending Data
{trends_context}

## Requirements
For each recommended persona, provide:
1. A unique name and tagline
2. Domain/niche (e.g., tech, lifestyle, finance, health)
3. Target audience with their pain points
4. 3-5 expertise areas
5. Suggested content pillars (3-4)
6. Recommended content types
7. Suggested tone/voice
8. Relevance score (0-100) - how well this aligns with current trends
9. Potential score (0-100) - growth potential and sustainability
10. Rationale - why this persona is recommended

Return as JSON array:
```json
[
  {{
    "name": "string",
    "tagline": "string",
    "domain": "string",
    "target_audience": "string",
    "audience_pain_points": ["string"],
    "expertise": ["string"],
    "content_pillars": ["string"],
    "content_types": ["string"],
    "suggested_tone": "string",
    "relevance_score": number,
    "potential_score": number,
    "rationale": "string",
    "source_trends": ["string"]
  }}
]
```"""

        try:
            response = await self.call_llm(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.8,
                max_tokens=4096,
            )

            # Parse JSON from response
            recommendations = self._parse_recommendations(response, platforms)
            return recommendations

        except Exception as e:
            self.log("ERROR", f"Failed to generate recommendations: {e}")
            return []

    async def analyze_trend_opportunities(
        self,
        trend_snapshots: List[TrendSnapshot],
    ) -> Dict[str, Any]:
        """
        Analyze trends to identify opportunities without generating full personas.

        Args:
            trend_snapshots: List of TrendSnapshot

        Returns:
            Analysis dict with opportunities, themes, and insights
        """
        if not trend_snapshots:
            return {"opportunities": [], "themes": [], "insights": []}

        trends_context = self._build_trends_context(trend_snapshots)

        system_prompt = """You are a social media trend analyst.
Analyze the trending data and identify opportunities, themes, and key insights."""

        user_prompt = f"""Analyze the following trending data and identify opportunities:

{trends_context}

Return as JSON:
```json
{{
  "opportunities": [
    {{
      "domain": "string",
      "opportunity": "string",
      "evidence": ["string"],
      "potential": "high|medium|low"
    }}
  ],
  "emerging_themes": ["string"],
  "content_gaps": ["string"],
  "key_insights": ["string"]
}}
```"""

        try:
            response = await self.call_llm(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.7,
                max_tokens=2048,
            )

            # Extract JSON from response
            json_str = self._extract_json(response)
            if json_str:
                return json.loads(json_str)
            return {"opportunities": [], "themes": [], "insights": []}

        except Exception as e:
            self.log("ERROR", f"Failed to analyze opportunities: {e}")
            return {"opportunities": [], "themes": [], "insights": []}

    def _build_trends_context(self, snapshots: List[TrendSnapshot]) -> str:
        """Build context string from trend snapshots."""
        parts = []
        for snapshot in snapshots:
            part = f"""### {snapshot.platform.upper()} ({snapshot.captured_at.strftime('%Y-%m-%d')})
**Trending Topics:** {', '.join(snapshot.trending_topics[:10])}
**Hashtags:** {', '.join(snapshot.trending_hashtags[:10])}
**Key Themes:** {', '.join(snapshot.key_themes[:5])}
**Summary:** {snapshot.analysis_summary}
**Content Patterns:** {', '.join(snapshot.content_patterns[:5])}
"""
            # Add sample posts if available
            if snapshot.top_posts:
                post_samples = []
                for post in snapshot.top_posts[:3]:
                    body = post.get("body", "")[:200]
                    likes = post.get("likes", 0)
                    post_samples.append(f"- {body}... ({likes} likes)")
                part += f"**Sample Posts:**\n" + "\n".join(post_samples) + "\n"

            parts.append(part)

        return "\n".join(parts)

    def _parse_recommendations(
        self,
        response: str,
        platforms: List[str],
    ) -> List[RecommendedPersona]:
        """Parse LLM response into RecommendedPersona objects."""
        json_str = self._extract_json(response)
        if not json_str:
            self.log("WARNING", "Could not extract JSON from recommendation response")
            return []

        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                data = [data]

            recommendations = []
            for item in data:
                rec = RecommendedPersona(
                    id=f"rec_persona_{uuid.uuid4().hex[:8]}",
                    created_at=datetime.now(),
                    source_platforms=platforms,
                    source_trends=item.get("source_trends", []),
                    name=item.get("name", "Unnamed Persona"),
                    tagline=item.get("tagline", ""),
                    domain=item.get("domain", "general"),
                    expertise=item.get("expertise", []),
                    target_audience=item.get("target_audience", ""),
                    audience_pain_points=item.get("audience_pain_points", []),
                    suggested_tone=item.get("suggested_tone", "professional"),
                    content_types=item.get("content_types", []),
                    content_pillars=item.get("content_pillars", []),
                    relevance_score=float(item.get("relevance_score", 50)),
                    potential_score=float(item.get("potential_score", 50)),
                    rationale=item.get("rationale", ""),
                )
                recommendations.append(rec)

            return recommendations

        except json.JSONDecodeError as e:
            self.log("ERROR", f"Failed to parse recommendations JSON: {e}")
            return []

    def _extract_json(self, response: str) -> Optional[str]:
        """Extract JSON from LLM response."""
        # Try to find JSON in code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()

        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()

        # Try to find raw JSON array or object
        for start_char, end_char in [("[", "]"), ("{", "}")]:
            start = response.find(start_char)
            if start >= 0:
                # Find matching end
                depth = 0
                for i, c in enumerate(response[start:], start):
                    if c == start_char:
                        depth += 1
                    elif c == end_char:
                        depth -= 1
                        if depth == 0:
                            return response[start : i + 1]

        return None

    async def _generate_recommendations(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Internal handler for generate_recommendations message."""
        snapshots_data = payload.get("trend_snapshots", [])
        count = payload.get("count", 3)

        # Convert dict to TrendSnapshot if needed
        snapshots = []
        for item in snapshots_data:
            if isinstance(item, TrendSnapshot):
                snapshots.append(item)
            elif isinstance(item, dict):
                snapshots.append(TrendSnapshot(**item))

        recommendations = await self.generate_recommendations(snapshots, count)

        return {
            "status": "success",
            "data": {
                "recommendations": [r.model_dump(mode="json") for r in recommendations],
                "count": len(recommendations),
            },
        }

    async def _analyze_opportunities(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Internal handler for analyze_opportunities message."""
        snapshots_data = payload.get("trend_snapshots", [])

        snapshots = []
        for item in snapshots_data:
            if isinstance(item, TrendSnapshot):
                snapshots.append(item)
            elif isinstance(item, dict):
                snapshots.append(TrendSnapshot(**item))

        analysis = await self.analyze_trend_opportunities(snapshots)

        return {
            "status": "success",
            "data": analysis,
        }
