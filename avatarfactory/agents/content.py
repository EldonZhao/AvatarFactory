"""
Content Agent - Handles content generation, variants, and platform adaptation.

Renamed from ContentLabAgent to ContentAgent as part of architecture refactoring.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from avatarfactory.agents.base import BaseAgent
from avatarfactory.models.schemas import (
    AgentMessage,
    Content,
    ContentStructure,
    MediaAttachment,
    Persona,
    PlatformType,
    TaskType,
)


# Content templates for different content types
CONTENT_TEMPLATES = {
    "comparison": {
        "structure": [
            "Hook: Address reader's dilemma",
            "Comparison dimensions with data",
            "Real-world test results",
            "Selection guide by scenario",
            "Call-to-action: Engage in comments",
        ],
        "style_notes": "Objective but can show preference; data-driven; visual aids helpful",
    },
    "tutorial": {
        "structure": [
            "Problem statement",
            "Step-by-step instructions (3-5 steps)",
            "Screenshots/examples",
            "Common pitfalls to avoid",
            "Expected results",
        ],
        "style_notes": "Clear and actionable; numbered steps; beginner-friendly language",
    },
    "case_study": {
        "structure": [
            "Before: The problem/challenge",
            "Solution: What was implemented",
            "After: Results with metrics",
            "Key takeaways",
            "How readers can apply this",
        ],
        "style_notes": "Story-driven; specific numbers; relatable scenario",
    },
    "listicle": {
        "structure": [
            "Hook: Why this list matters",
            "List items (3-7) with brief explanations",
            "Bonus tip (optional)",
            "Summary and next steps",
        ],
        "style_notes": "Scannable; each item is actionable; avoid fluff",
    },
}


class ContentAgent(BaseAgent):
    """Agent responsible for content generation and adaptation"""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(agent_id="content", *args, **kwargs)
        self._notification_connectors: Dict[str, Any] = {}

    # =========================================================================
    # Notification Methods
    # =========================================================================

    async def _get_notification_connector(self, persona: Persona) -> Optional[Any]:
        """
        Get or create notification connector for a persona.

        Args:
            persona: Persona with notification config

        Returns:
            Connected notification connector or None
        """
        if not persona.notification or not persona.notification.enabled:
            return None

        # Check cache
        cache_key = persona.id
        if cache_key in self._notification_connectors:
            connector = self._notification_connectors[cache_key]
            if connector.is_connected():
                return connector

        try:
            from avatarfactory.connectors import ConnectorRegistry, ConnectorConfig

            # Build connector config
            config = ConnectorConfig(
                api_key=persona.notification.webhook_key,
                extra={
                    "webhook_url": persona.notification.webhook_url,
                    "webhook_key": persona.notification.webhook_key,
                    **persona.notification.extra,
                },
            )

            # Create and connect
            connector = ConnectorRegistry.create_connector(
                persona.notification.connector_type,
                config,
            )
            await connector.connect()

            # Cache it
            self._notification_connectors[cache_key] = connector
            self.log("DEBUG", f"Created notification connector for persona {persona.id}")
            return connector

        except Exception as e:
            self.log("WARNING", f"Failed to create notification connector: {e}")
            return None

    async def _send_content_notification(
        self,
        persona: Persona,
        content: Content,
        review_score: Optional[float] = None,
        review_summary: Optional[str] = None,
    ) -> None:
        """
        Send notification about generated content.

        Args:
            persona: Persona with notification config
            content: Generated content
            review_score: Optional review score
            review_summary: Optional review summary
        """
        if not persona.notification or not persona.notification.enabled:
            return

        if not persona.notification.notify_on_content:
            return

        connector = await self._get_notification_connector(persona)
        if not connector:
            return

        try:
            # Check if connector has the convenience method
            if hasattr(connector, "send_content_notification"):
                result = await connector.send_content_notification(
                    content_title=content.title,
                    content_body=content.body,
                    review_score=review_score if persona.notification.notify_on_review else None,
                    review_summary=review_summary if persona.notification.notify_on_review else None,
                    content_id=content.id,
                    persona_name=persona.identity.name,
                    platform=content.platform.value,
                    tags=content.tags,
                )
            else:
                # Fallback to generic publish
                message = f"新内容已创建: {content.title}\n\n{content.body[:300]}..."
                if review_score is not None and persona.notification.notify_on_review:
                    message += f"\n\n评分: {review_score:.0f}/100"
                result = await connector.publish(
                    content=message,
                    title=f"内容创作通知 - {persona.identity.name}",
                )

            if result.success:
                self.log("INFO", f"Sent notification for content {content.id}")
            else:
                self.log("WARNING", f"Failed to send notification: {result.error}")

        except Exception as e:
            self.log("WARNING", f"Error sending notification: {e}")

    # =========================================================================
    # Trending Context
    # =========================================================================

    def _get_trending_context(
        self,
        persona_id: str,
        platform: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get trending context from knowledge base.

        DiscoveryAgent runs on its own schedule and saves results to KB.
        ContentAgent reads from KB - they are decoupled.

        Args:
            persona_id: Persona ID
            platform: Platform name

        Returns:
            Dict with trending data or None if unavailable
        """
        try:
            # Read from knowledge base (saved by DiscoveryAgent)
            data = self.kb.get_latest_discovery(persona_id, platform)
            if data:
                self.log("DEBUG", f"Loaded trending data for {persona_id}/{platform}")
                return data
            else:
                self.log("DEBUG", f"No trending data found for {persona_id}/{platform}")
                return None
        except Exception as e:
            self.log("WARNING", f"Error reading trending context: {e}")
            return None

    def _build_trending_context_prompt(self, trends: Dict[str, Any]) -> str:
        """Build a prompt section from trending data."""
        parts = []

        # Extract pattern analysis
        pattern_analysis = trends.get("pattern_analysis", {})
        if pattern_analysis:
            trending_topics = pattern_analysis.get("trending_topics", [])
            if trending_topics:
                parts.append(f"当前热点话题: {', '.join(trending_topics[:5])}")

            key_insights = pattern_analysis.get("key_insights", [])
            if key_insights:
                parts.append(f"受众洞察: {'; '.join(key_insights[:3])}")

            hook_patterns = pattern_analysis.get("hook_patterns", [])
            if hook_patterns:
                hooks = [p.get("name", "") for p in hook_patterns[:3]]
                parts.append(f"有效开篇模式: {', '.join(hooks)}")

        # Extract ideas for inspiration
        ideas = trends.get("ideas", [])
        if ideas:
            idea_topics = [idea.get("topic", "") for idea in ideas[:3]]
            parts.append(f"推荐创作方向: {', '.join(idea_topics)}")

        if parts:
            return "\n".join([
                "",
                "=== 热点趋势洞察 ===",
                *parts,
                "请在保持人设风格的同时，适当融入这些热点元素以提高内容吸引力。",
                "",
            ])
        return ""

    # =========================================================================
    # Main Process Method
    # =========================================================================

    async def process(self, message: AgentMessage) -> Any:
        """Process content-related tasks"""
        self.validate_message(message)

        task_handlers = {
            TaskType.GENERATE_CONTENT: self._generate_content,
        }

        handler = task_handlers.get(message.task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {message.task_type}")

        return await handler(message.payload, message.context)

    # =========================================================================
    # Content Generation
    # =========================================================================

    async def _generate_content(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> Content:
        """
        Generate content based on persona and topic.

        Expected payload:
            - persona_id: str
            - pillar: str (content pillar name)
            - topic: str (specific topic to write about)
            - template: str (optional, template type)
            - platform: str (optional, defaults to persona's primary platform)
            - variant_count: int (optional, defaults to 1)
            - use_trending: bool (optional, defaults to True, integrate trending data)
        """
        persona_id = payload.get("persona_id")
        pillar = payload.get("pillar")
        topic = payload.get("topic")
        template = payload.get("template", "comparison")
        platform = payload.get("platform")
        variant_count = payload.get("variant_count", 1)
        use_trending = payload.get("use_trending", True)

        if not all([persona_id, pillar, topic]):
            raise ValueError("persona_id, pillar, and topic are required")

        # Load persona
        persona = self.kb.load_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        # Determine platform
        if not platform:
            platform = persona.platforms[0] if persona.platforms else PlatformType.XIAOHONGSHU
        else:
            platform = PlatformType(platform)

        self.log(
            "INFO",
            f"Generating content for persona {persona_id}, topic: {topic}, platform: {platform}",
        )

        # Get trending context if enabled (reads from KB, saved by DiscoveryAgent)
        trending_context = ""
        if use_trending:
            trends = self._get_trending_context(persona_id, platform.value)
            if trends:
                trending_context = self._build_trending_context_prompt(trends)
                self.log("DEBUG", "Integrated trending context into prompt")

        # Generate content
        if variant_count == 1:
            content = await self._generate_single_content(
                persona, pillar, topic, template, platform, trending_context
            )
        else:
            variants = await self._generate_variants(
                persona, pillar, topic, template, platform, variant_count, trending_context
            )
            # Save all variants to KB
            for variant in variants[1:]:
                self.kb.save_content(variant, status="draft")
            content = variants[0]

        # Send notification after content generation
        await self._send_content_notification(
            persona=persona,
            content=content,
            review_score=content.review_score,
            review_summary=None,  # Could be populated by review agent
        )

        return content

    async def _generate_single_content(
        self,
        persona: Persona,
        pillar: str,
        topic: str,
        template: str,
        platform: PlatformType,
        trending_context: str = "",
    ) -> Content:
        """Generate a single content piece"""

        template_info = CONTENT_TEMPLATES.get(template, CONTENT_TEMPLATES["comparison"])

        # Build system prompt with optional trending context
        system_prompt = f"""You are a professional content creator for {platform.value}. Your task is to create high-quality, engaging content that matches the given persona and platform style.

PERSONA:
- Identity: {persona.identity.name} - {persona.identity.tagline}
- Expertise: {', '.join(persona.identity.expertise)}
- Target Audience: {persona.target_audience.primary}
- Audience Pain Points: {', '.join(persona.target_audience.pain_points)}
- Voice/Tone: {persona.voice_style.tone}
- Language Patterns: {', '.join(persona.voice_style.language_patterns)}
- Emoji Usage: {persona.voice_style.emoji_usage}

PLATFORM: {platform.value}
CONTENT PILLAR: {pillar}
{trending_context}
TEMPLATE STRUCTURE:
{json.dumps(template_info['structure'], indent=2, ensure_ascii=False)}

STYLE NOTES: {template_info['style_notes']}

BOUNDARIES (MUST AVOID):
{json.dumps(persona.boundaries.avoid, indent=2, ensure_ascii=False)}

COMPLIANCE REQUIREMENTS:
{json.dumps(persona.boundaries.compliance, indent=2, ensure_ascii=False)}

Output MUST be valid JSON:
{{
  "title": "compelling title (max 60 chars for xiaohongshu)",
  "body": "full content text",
  "tags": ["tag1", "tag2", "tag3"],
  "structure_notes": "brief notes on how you structured the content",
  "image_prompts": [
    "detailed prompt for AI image generation for image 1",
    "detailed prompt for AI image generation for image 2"
  ],
  "image_suggestions": [
    "description of what kind of image/photo would work well here",
    "description of image 2"
  ],
  "recommended_image_count": 2
}}

Generate 2-4 image prompts that would complement the content for visual platforms."""

        user_prompt = f"""Create content about: {topic}

Make it:
- Aligned with the persona's voice and expertise
- Optimized for {platform.value} (platform-native style)
- Valuable and actionable for the target audience
- Following the {template} template structure

Generate the content in JSON format."""

        response = await self.call_llm(user_prompt, system=system_prompt, temperature=0.8)

        # Parse response
        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            content_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.log("ERROR", f"Failed to parse content JSON: {e}")
            raise ValueError(f"Failed to generate valid content: {e}")

        # Create Content object
        content = Content(
            id=f"content_{uuid.uuid4().hex[:8]}",
            persona_id=persona.id,
            created_at=datetime.now(),
            title=content_data["title"],
            body=content_data["body"],
            pillar=pillar,
            platform=platform,
            structure=ContentStructure(
                sections=template_info["structure"],
                style_constraints={"template": template, "persona_voice": persona.voice_style.tone},
            ),
            tags=content_data.get("tags", []),
            metadata={
                "topic": topic,
                "template": template,
                "structure_notes": content_data.get("structure_notes", ""),
                "image_suggestions": content_data.get("image_suggestions", []),
                "recommended_image_count": content_data.get("recommended_image_count", 2),
            },
            image_prompts=content_data.get("image_prompts", []),
        )

        # Save to knowledge base
        self.kb.save_content(content, status="draft")

        self.log("INFO", f"Generated content: {content.id} - {content.title}")
        return content

    async def _generate_variants(
        self,
        persona: Persona,
        pillar: str,
        topic: str,
        template: str,
        platform: PlatformType,
        count: int,
        trending_context: str = "",
    ) -> List[Content]:
        """Generate multiple variants of the same topic"""

        self.log("INFO", f"Generating {count} variants for topic: {topic}")

        system_prompt = f"""You are a professional content creator. Generate {count} different versions of content on the same topic, each with a different angle or hook.

PERSONA:
- Identity: {persona.identity.name} - {persona.identity.tagline}
- Voice: {persona.voice_style.tone}
{trending_context}
Each variant should have:
1. Different hook/angle (e.g., data-driven vs story-driven vs contrarian)
2. Different title style
3. Same core message but different presentation

Output MUST be valid JSON array:
[
  {{
    "title": "title for variant 1",
    "body": "full content for variant 1",
    "angle": "description of the angle used",
    "hook_type": "type of hook (e.g., curiosity/controversy/value)",
    "tags": ["tag1", "tag2"]
  }}
]"""

        user_prompt = f"""Topic: {topic}
Platform: {platform.value}
Content Pillar: {pillar}
Template: {template}

Generate {count} compelling variants in JSON array format."""

        response = await self.call_llm(
            user_prompt, system=system_prompt, temperature=0.9, max_tokens=4096
        )

        # Parse response
        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            variants_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.log("ERROR", f"Failed to parse variants JSON: {e}")
            # Fallback: generate single content
            single = await self._generate_single_content(
                persona, pillar, topic, template, platform
            )
            return [single]

        # Create Content objects
        contents = []
        for i, variant_data in enumerate(variants_data[:count]):
            content = Content(
                id=f"content_{uuid.uuid4().hex[:8]}",
                persona_id=persona.id,
                created_at=datetime.now(),
                title=variant_data["title"],
                body=variant_data["body"],
                pillar=pillar,
                platform=platform,
                tags=variant_data.get("tags", []),
                metadata={
                    "topic": topic,
                    "template": template,
                    "variant_index": i + 1,
                    "angle": variant_data.get("angle", ""),
                    "hook_type": variant_data.get("hook_type", ""),
                },
            )
            contents.append(content)

        self.log("INFO", f"Generated {len(contents)} variants")
        return contents

    # =========================================================================
    # Platform Adaptation
    # =========================================================================

    async def adapt_to_platform(
        self, content: Content, target_platform: PlatformType
    ) -> Content:
        """
        Adapt existing content to a different platform.

        Args:
            content: Original content
            target_platform: Platform to adapt to

        Returns:
            Adapted content
        """
        if content.platform == target_platform:
            return content

        persona = self.kb.load_persona(content.persona_id)
        if not persona:
            raise ValueError(f"Persona {content.persona_id} not found")

        self.log(
            "INFO",
            f"Adapting content from {content.platform} to {target_platform}",
        )

        # Platform-specific guidelines
        platform_guidelines = {
            PlatformType.XIAOHONGSHU: {
                "title_max_length": 60,
                "emoji_density": "moderate-high",
                "image_count": "6-9",
                "tone": "casual, relatable",
                "structure": "visual-first, short paragraphs",
            },
            PlatformType.ZHIHU: {
                "title_style": "question-based or professional",
                "min_length": 800,
                "tone": "professional, in-depth",
                "structure": "logical, data-driven, long-form",
            },
            PlatformType.TWITTER: {
                "format": "thread",
                "max_length_per_tweet": 280,
                "thread_length": "5-10 tweets",
                "tone": "concise, punchy",
            },
        }

        guidelines = platform_guidelines.get(target_platform, {})

        system_prompt = f"""You are a platform adaptation expert. Adapt content from {content.platform.value} to {target_platform.value} while maintaining the core message and persona voice.

ORIGINAL CONTENT:
Title: {content.title}
Body: {content.body}

TARGET PLATFORM: {target_platform.value}
Platform Guidelines: {json.dumps(guidelines, indent=2)}

PERSONA VOICE: {persona.voice_style.tone}

Output MUST be valid JSON:
{{
  "title": "adapted title",
  "body": "adapted content",
  "adaptation_notes": "what was changed and why"
}}"""

        user_prompt = "Adapt the content to the target platform following the guidelines."

        response = await self.call_llm(user_prompt, system=system_prompt, temperature=0.7)

        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            adapted_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.log("ERROR", f"Failed to parse adapted content: {e}")
            raise ValueError(f"Failed to adapt content: {e}")

        # Create adapted content
        adapted_content = Content(
            id=f"content_{uuid.uuid4().hex[:8]}",
            persona_id=content.persona_id,
            created_at=datetime.now(),
            title=adapted_data["title"],
            body=adapted_data["body"],
            pillar=content.pillar,
            platform=target_platform,
            tags=content.tags,
            metadata={
                **content.metadata,
                "adapted_from": content.id,
                "original_platform": content.platform.value,
                "adaptation_notes": adapted_data.get("adaptation_notes", ""),
            },
        )

        self.kb.save_content(adapted_content, status="draft")
        self.log("INFO", f"Created adapted content: {adapted_content.id}")

        return adapted_content


# Deprecated alias for backward compatibility
ContentLabAgent = ContentAgent
