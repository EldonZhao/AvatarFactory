"""
Topic Agent for AvatarFactory.

Responsible for:
1. Fetching trending content from social platforms
2. Analyzing content patterns and trends
3. Generating content ideas based on persona
4. Providing persona optimization suggestions
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from avatarfactory.agents.base import BaseAgent
from avatarfactory.connectors import ConnectorConfig, get_connector
from avatarfactory.models.schemas import (
    AgentMessage,
    ContentIdea,
    ContentPattern,
    ContentPatternAnalysis,
    DiscoveryReport,
    Persona,
    TrendingContent,
)


class TopicAgent(BaseAgent):
    """
    Topic Agent - discovers and analyzes hot topics from social platforms to guide content creation.

    Capabilities:
    - Search trending content based on persona keywords
    - Analyze successful content patterns
    - Generate content ideas inspired by trends
    - Suggest persona optimizations based on market analysis
    """

    def __init__(self, **kwargs):
        super().__init__(agent_id="topic", **kwargs)
        self._connector_configs: Dict[str, ConnectorConfig] = {}

    def configure_platform(self, platform: str, config: ConnectorConfig) -> None:
        """Configure credentials for a platform."""
        self._connector_configs[platform.lower()] = config

    async def process(self, message: AgentMessage) -> Dict[str, Any]:
        """Process discovery-related messages."""
        task_type = (
            message.task_type.value
            if hasattr(message.task_type, "value")
            else str(message.task_type)
        )
        payload = message.payload

        if task_type == "discover_trending":
            return await self._discover_trending(payload)
        elif task_type == "analyze_patterns":
            return await self._analyze_patterns(payload)
        elif task_type == "get_inspiration":
            return await self._get_inspiration(payload)
        else:
            return {
                "status": "error",
                "message": f"Unknown task type: {task_type}",
            }

    async def _discover_trending(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Discover trending content from platforms based on persona.

        Args:
            payload: {
                "persona_id": str (optional),
                "platform": str (bluesky/twitter),
                "query": str (optional, uses persona keywords if not provided),
                "limit": int (default 20)
            }
        """
        platform = payload.get("platform", "bluesky")
        query = payload.get("query")
        limit = payload.get("limit", 20)
        persona_id = payload.get("persona_id")

        # Get search keywords from persona if no query provided
        if not query and persona_id:
            try:
                persona = self.kb.load_persona(persona_id)
                if persona:
                    # Build query from persona expertise and pillars
                    keywords = persona.identity.expertise[:3]
                    pillar_names = [p.name for p in persona.content_pillars[:2]]
                    query = " ".join(keywords + pillar_names)
            except Exception as e:
                self.log("WARNING", f"Could not load persona for keywords: {e}")

        # Get connector config
        config = self._connector_configs.get(platform.lower())
        if not config:
            # Try to create from environment
            import os

            config = ConnectorConfig()
            if platform.lower() == "bluesky":
                config.username = os.getenv("BLUESKY_USERNAME")
                config.password = os.getenv("BLUESKY_PASSWORD")
            elif platform.lower() == "twitter":
                config.api_key = os.getenv("TWITTER_API_KEY")
                config.api_secret = os.getenv("TWITTER_API_SECRET")
                config.access_token = os.getenv("TWITTER_ACCESS_TOKEN")

        try:
            connector = get_connector(platform, config)
            await connector.connect()

            result = await connector.fetch_trending(query=query, limit=limit)

            if not result.success:
                return {
                    "status": "error",
                    "message": f"Failed to fetch trending: {result.error}",
                }

            # Convert to TrendingContent objects
            trending_contents = []
            for item in result.data:
                tc = TrendingContent(
                    id=f"trending_{uuid.uuid4().hex[:8]}",
                    platform=platform,
                    post_id=item.get("post_id", ""),
                    author=item.get("author", ""),
                    author_id=item.get("author_id"),
                    body=item.get("body", ""),
                    likes=item.get("likes", 0),
                    comments=item.get("comments", 0),
                    shares=item.get("shares", 0),
                    views=item.get("views", 0),
                    url=item.get("url"),
                    published_at=item.get("published_at"),
                    # Image information
                    images=item.get("images", []),
                    image_count=item.get("image_count", 0),
                    has_media=item.get("has_media", False),
                )
                trending_contents.append(tc)

            await connector.disconnect()

            return {
                "status": "success",
                "data": {
                    "platform": platform,
                    "query": query,
                    "count": len(trending_contents),
                    "contents": [c.model_dump(mode="json") for c in trending_contents],
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Discovery failed: {str(e)}",
            }

    async def _analyze_patterns(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze patterns in trending content using LLM.

        Args:
            payload: {
                "contents": List[Dict] - trending content to analyze,
                "persona_id": str (optional) - for relevance scoring
            }
        """
        contents = payload.get("contents", [])
        persona_id = payload.get("persona_id")

        if not contents:
            return {
                "status": "error",
                "message": "No contents provided for analysis",
            }

        # Get persona for context
        persona_context = ""
        if persona_id:
            try:
                persona = self.kb.load_persona(persona_id)
                if persona:
                    persona_context = f"""
Target Persona Context:
- Name: {persona.identity.name}
- Expertise: {', '.join(persona.identity.expertise)}
- Content Pillars: {', '.join(p.name for p in persona.content_pillars)}
- Target Audience: {persona.target_audience.primary}
- Voice Tone: {persona.voice_style.tone}
"""
            except Exception:
                pass

        # Prepare content summaries for LLM
        content_summaries = []
        for i, c in enumerate(contents[:15]):  # Limit to 15 for token efficiency
            # Include image/media info
            media_info = ""
            if c.get("has_media") or c.get("image_count", 0) > 0:
                img_count = c.get("image_count", 0)
                media_info = f" | Images: {img_count}"

            summary = f"""
Content {i+1}:
- Author: @{c.get('author', 'unknown')}
- Likes: {c.get('likes', 0)} | Comments: {c.get('comments', 0)} | Shares: {c.get('shares', 0)}{media_info}
- Has Media: {'Yes' if c.get('has_media') else 'No'}
- Text: {c.get('body', '')[:300]}...
"""
            content_summaries.append(summary)

        prompt = f"""Analyze the following trending social media content and identify patterns.
{persona_context}

=== TRENDING CONTENT ===
{"".join(content_summaries)}

=== ANALYSIS TASK ===
Identify patterns in the successful content above, including visual/media patterns. Return a JSON object with:

{{
    "hook_patterns": [
        {{"name": "pattern name", "description": "how it works", "frequency": count}}
    ],
    "structure_patterns": [
        {{"name": "pattern name", "description": "content structure pattern", "frequency": count}}
    ],
    "topic_patterns": [
        {{"name": "topic theme", "description": "what makes it engaging", "frequency": count}}
    ],
    "style_patterns": [
        {{"name": "style element", "description": "writing style pattern", "frequency": count}}
    ],
    "visual_patterns": [
        {{"name": "visual pattern", "description": "how images/media are used", "avg_image_count": number, "frequency": count}}
    ],
    "trending_topics": ["topic1", "topic2", ...],
    "trending_hashtags": ["#tag1", "#tag2", ...],
    "key_insights": [
        "insight 1 about what makes this content successful",
        "insight 2 about audience preferences",
        "insight 3 about visual content strategy"
    ],
    "media_recommendations": {{
        "optimal_image_count": number,
        "image_style": "description of effective image styles",
        "visual_themes": ["theme1", "theme2"]
    }}
}}

Focus on actionable patterns that could inform content creation, especially regarding visual content.
Return ONLY valid JSON, no other text."""

        try:
            response = await self.call_llm(
                prompt=prompt,
                system="You are a social media content analyst. Analyze content patterns and return structured JSON.",
                temperature=0.3,
            )

            # Parse JSON response
            try:
                # Clean response - find JSON object
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    analysis_data = json.loads(response[json_start:json_end])
                else:
                    raise ValueError("No JSON found in response")
            except json.JSONDecodeError as e:
                self.log("WARNING", f"Failed to parse LLM response as JSON: {e}")
                analysis_data = {
                    "hook_patterns": [],
                    "structure_patterns": [],
                    "topic_patterns": [],
                    "style_patterns": [],
                    "trending_topics": [],
                    "trending_hashtags": [],
                    "key_insights": ["Analysis parsing failed - raw insights available"],
                }

            # Build ContentPatternAnalysis
            analysis = ContentPatternAnalysis(
                platform=contents[0].get("platform", "unknown") if contents else "unknown",
                content_count=len(contents),
                hook_patterns=[
                    ContentPattern(
                        pattern_type="hook",
                        name=p.get("name", ""),
                        description=p.get("description", ""),
                        frequency=p.get("frequency", 1),
                    )
                    for p in analysis_data.get("hook_patterns", [])
                ],
                structure_patterns=[
                    ContentPattern(
                        pattern_type="structure",
                        name=p.get("name", ""),
                        description=p.get("description", ""),
                        frequency=p.get("frequency", 1),
                    )
                    for p in analysis_data.get("structure_patterns", [])
                ],
                topic_patterns=[
                    ContentPattern(
                        pattern_type="topic",
                        name=p.get("name", ""),
                        description=p.get("description", ""),
                        frequency=p.get("frequency", 1),
                    )
                    for p in analysis_data.get("topic_patterns", [])
                ],
                style_patterns=[
                    ContentPattern(
                        pattern_type="style",
                        name=p.get("name", ""),
                        description=p.get("description", ""),
                        frequency=p.get("frequency", 1),
                    )
                    for p in analysis_data.get("style_patterns", [])
                ],
                trending_topics=analysis_data.get("trending_topics", []),
                trending_hashtags=analysis_data.get("trending_hashtags", []),
                key_insights=analysis_data.get("key_insights", []),
            )

            return {
                "status": "success",
                "data": {
                    "analysis": analysis.model_dump(mode="json"),
                    "content_count": len(contents),
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Pattern analysis failed: {str(e)}",
            }

    async def _get_inspiration(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate content ideas based on persona and trend analysis.

        Args:
            payload: {
                "persona_id": str - required,
                "pattern_analysis": Dict (optional) - from analyze_patterns,
                "trending_contents": List[Dict] (optional) - raw trending content,
                "idea_count": int (default 5)
            }
        """
        persona_id = payload.get("persona_id")
        pattern_analysis = payload.get("pattern_analysis")
        trending_contents = payload.get("trending_contents", [])
        idea_count = payload.get("idea_count", 5)

        if not persona_id:
            return {
                "status": "error",
                "message": "persona_id is required",
            }

        # Load persona
        try:
            persona = self.kb.load_persona(persona_id)
            if not persona:
                return {
                    "status": "error",
                    "message": f"Persona {persona_id} not found",
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to load persona: {str(e)}",
            }

        # Build context
        persona_context = f"""
=== PERSONA ===
Name: {persona.identity.name}
Tagline: {persona.identity.tagline}
Expertise: {', '.join(persona.identity.expertise)}
Target Audience: {persona.target_audience.primary}
Pain Points: {', '.join(persona.target_audience.pain_points[:3])}
Voice Tone: {persona.voice_style.tone}
Content Pillars: {', '.join(f"{p.name}: {p.description}" for p in persona.content_pillars)}
Avoid: {', '.join(persona.boundaries.avoid[:3])}
"""

        # Add pattern analysis if available
        patterns_context = ""
        media_context = ""
        if pattern_analysis:
            insights = pattern_analysis.get("key_insights", [])
            topics = pattern_analysis.get("trending_topics", [])
            hooks = [p.get("name", "") for p in pattern_analysis.get("hook_patterns", [])]

            patterns_context = f"""
=== TREND ANALYSIS ===
Trending Topics: {', '.join(topics[:5])}
Effective Hook Patterns: {', '.join(hooks[:5])}
Key Insights:
{chr(10).join(f"- {i}" for i in insights[:5])}
"""
            # Add media recommendations if available
            media_recs = pattern_analysis.get("media_recommendations", {})
            if media_recs:
                media_context = f"""
=== VISUAL CONTENT PATTERNS ===
Optimal Image Count: {media_recs.get('optimal_image_count', 2)}
Image Style: {media_recs.get('image_style', 'Not specified')}
Visual Themes: {', '.join(media_recs.get('visual_themes', []))}
"""

        # Add sample trending content
        trending_context = ""
        if trending_contents:
            samples = trending_contents[:5]
            trending_context = """
=== HIGH-PERFORMING CONTENT EXAMPLES ===
"""
            for i, c in enumerate(samples):
                img_info = f" | Images: {c.get('image_count', 0)}" if c.get("has_media") else ""
                trending_context += f"""
Example {i+1} (Likes: {c.get('likes', 0)}{img_info}):
{c.get('body', '')[:200]}...
"""

        prompt = f"""{persona_context}
{patterns_context}
{media_context}
{trending_context}

=== TASK ===
Generate {idea_count} unique content ideas that:
1. Align with the persona's expertise and voice
2. Address target audience pain points
3. Leverage trending topics and successful patterns
4. Fit within the persona's content pillars
5. Include visual content suggestions for engagement

Return a JSON array of content ideas:
[
    {{
        "topic": "specific topic",
        "angle": "unique angle or perspective",
        "hook": "attention-grabbing opening line",
        "content_type": "post/thread/tutorial/comparison",
        "suggested_pillar": "which content pillar this fits",
        "estimated_engagement": "low/medium/high",
        "reasoning": "why this idea could resonate with the audience",
        "image_suggestions": [
            "description of recommended image 1",
            "description of recommended image 2"
        ],
        "recommended_image_count": 2
    }}
]

Be specific and actionable. Each idea should be distinct and include image recommendations.
Return ONLY valid JSON array, no other text."""

        try:
            response = await self.call_llm(
                prompt=prompt,
                system="You are a creative content strategist. Generate engaging content ideas aligned with persona and trends.",
                temperature=0.7,
            )

            # Parse JSON response
            try:
                json_start = response.find("[")
                json_end = response.rfind("]") + 1
                if json_start >= 0 and json_end > json_start:
                    ideas_data = json.loads(response[json_start:json_end])
                else:
                    raise ValueError("No JSON array found")
            except json.JSONDecodeError as e:
                self.log("WARNING", f"Failed to parse ideas JSON: {e}")
                ideas_data = []

            # Convert to ContentIdea objects
            content_ideas = []
            for idea in ideas_data:
                ci = ContentIdea(
                    id=f"idea_{uuid.uuid4().hex[:8]}",
                    topic=idea.get("topic", ""),
                    angle=idea.get("angle", ""),
                    hook=idea.get("hook"),
                    content_type=idea.get("content_type", "post"),
                    suggested_pillar=idea.get("suggested_pillar"),
                    estimated_engagement=idea.get("estimated_engagement", "medium"),
                    reasoning=idea.get("reasoning", ""),
                    image_suggestions=idea.get("image_suggestions", []),
                    recommended_image_count=idea.get("recommended_image_count", 2),
                )
                content_ideas.append(ci)

            # Generate persona optimization suggestions
            suggestions = await self._generate_persona_suggestions(
                persona, pattern_analysis, trending_contents
            )

            # Create discovery report
            report = DiscoveryReport(
                id=f"discovery_{uuid.uuid4().hex[:8]}",
                persona_id=persona_id,
                platforms_searched=[c.get("platform", "unknown") for c in trending_contents[:1]],
                trending_content_count=len(trending_contents),
                patterns_found=(
                    len(pattern_analysis.get("hook_patterns", [])) if pattern_analysis else 0
                ),
                ideas_generated=len(content_ideas),
                content_ideas=content_ideas,
                persona_suggestions=suggestions,
            )

            return {
                "status": "success",
                "data": {
                    "report": report.model_dump(mode="json"),
                    "ideas": [idea.model_dump(mode="json") for idea in content_ideas],
                    "persona_suggestions": suggestions,
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Inspiration generation failed: {str(e)}",
            }

    async def _generate_persona_suggestions(
        self,
        persona: Persona,
        pattern_analysis: Optional[Dict],
        trending_contents: List[Dict],
    ) -> List[str]:
        """Generate persona optimization suggestions based on discovery."""
        if not pattern_analysis and not trending_contents:
            return []

        context_parts = []

        if pattern_analysis:
            topics = pattern_analysis.get("trending_topics", [])
            insights = pattern_analysis.get("key_insights", [])
            context_parts.append(f"Trending topics: {', '.join(topics[:5])}")
            context_parts.append(f"Insights: {'; '.join(insights[:3])}")

        if trending_contents:
            avg_likes = sum(c.get("likes", 0) for c in trending_contents) / len(trending_contents)
            context_parts.append(
                f"Analyzed {len(trending_contents)} posts, avg likes: {avg_likes:.0f}"
            )

        prompt = f"""Based on the following market analysis, suggest 2-4 optimizations for this persona:

PERSONA:
- Name: {persona.identity.name}
- Expertise: {', '.join(persona.identity.expertise)}
- Content Pillars: {', '.join(p.name for p in persona.content_pillars)}
- Voice: {persona.voice_style.tone}

MARKET ANALYSIS:
{chr(10).join(context_parts)}

Provide 2-4 specific, actionable suggestions to improve the persona's content strategy.
Return ONLY a JSON array of suggestion strings:
["suggestion 1", "suggestion 2", ...]"""

        try:
            response = await self.call_llm(
                prompt=prompt,
                system="You are a personal branding strategist. Provide actionable optimization suggestions.",
                temperature=0.5,
                max_tokens=500,
            )

            json_start = response.find("[")
            json_end = response.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response[json_start:json_end])
            return []
        except Exception:
            return []

    # =========================================================================
    # High-level convenience methods
    # =========================================================================

    async def discover_and_analyze(
        self,
        persona_id: str,
        platform: str = "bluesky",
        query: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Complete discovery workflow: fetch → analyze → generate ideas.

        This is the main entry point for discovery functionality.
        """
        # Step 1: Fetch trending content
        trending_result = await self._discover_trending(
            {
                "persona_id": persona_id,
                "platform": platform,
                "query": query,
                "limit": limit,
            }
        )

        if trending_result.get("status") != "success":
            return trending_result

        contents = trending_result["data"]["contents"]

        # Step 2: Analyze patterns
        analysis_result = await self._analyze_patterns(
            {
                "contents": contents,
                "persona_id": persona_id,
            }
        )

        pattern_analysis = None
        if analysis_result.get("status") == "success":
            pattern_analysis = analysis_result["data"]["analysis"]

        # Step 3: Generate inspiration
        inspiration_result = await self._get_inspiration(
            {
                "persona_id": persona_id,
                "pattern_analysis": pattern_analysis,
                "trending_contents": contents,
                "idea_count": 5,
            }
        )

        if inspiration_result.get("status") != "success":
            return inspiration_result

        # Build result data
        result_data = {
            "trending_count": len(contents),
            "pattern_analysis": pattern_analysis,
            "ideas": inspiration_result["data"]["ideas"],
            "persona_suggestions": inspiration_result["data"]["persona_suggestions"],
            "report": inspiration_result["data"]["report"],
        }

        # Step 4: Save results to knowledges for ContentAgent to read
        try:
            self.kb.save_discovery_results(persona_id, platform, result_data)
            self.log("INFO", f"Saved discovery results to knowledges for {persona_id}/{platform}")
        except Exception as e:
            self.log("WARNING", f"Failed to save discovery results: {e}")

        # Note: Discovery notifications are now handled by the Scheduler engine
        # to ensure consistent notification format across all task types.

        return {
            "status": "success",
            "data": result_data,
            "message": f"Discovered {len(contents)} trending posts, analyzed patterns, generated {len(inspiration_result['data']['ideas'])} content ideas.",
        }
