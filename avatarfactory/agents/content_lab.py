"""
Content Lab Agent - Handles content generation, variants, and platform adaptation.
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


class ContentLabAgent(BaseAgent):
    """Agent responsible for content generation and adaptation"""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(agent_id="content_lab", *args, **kwargs)

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
        """
        persona_id = payload.get("persona_id")
        pillar = payload.get("pillar")
        topic = payload.get("topic")
        template = payload.get("template", "comparison")
        platform = payload.get("platform")
        variant_count = payload.get("variant_count", 1)

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

        # Generate content
        if variant_count == 1:
            content = await self._generate_single_content(
                persona, pillar, topic, template, platform
            )
            return content
        else:
            variants = await self._generate_variants(
                persona, pillar, topic, template, platform, variant_count
            )
            # Return first variant, but save all to KB
            for variant in variants[1:]:
                self.kb.save_content(variant, status="draft")
            return variants[0]

    async def _generate_single_content(
        self,
        persona: Persona,
        pillar: str,
        topic: str,
        template: str,
        platform: PlatformType,
    ) -> Content:
        """Generate a single content piece"""

        template_info = CONTENT_TEMPLATES.get(template, CONTENT_TEMPLATES["comparison"])

        # Build system prompt
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
  "structure_notes": "brief notes on how you structured the content"
}}"""

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
            },
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
    ) -> List[Content]:
        """Generate multiple variants of the same topic"""

        self.log("INFO", f"Generating {count} variants for topic: {topic}")

        system_prompt = f"""You are a professional content creator. Generate {count} different versions of content on the same topic, each with a different angle or hook.

PERSONA:
- Identity: {persona.identity.name} - {persona.identity.tagline}
- Voice: {persona.voice_style.tone}

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
