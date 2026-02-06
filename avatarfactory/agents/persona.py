"""
Persona Agent - Handles persona creation, versioning, and optimization.

Renamed from PersonaLabAgent to PersonaAgent as part of architecture refactoring.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from avatarfactory.agents.base import BaseAgent
from avatarfactory.models.schemas import (
    AgentMessage,
    Boundaries,
    ContentPillar,
    Identity,
    Persona,
    PersonaVersion,
    PlatformType,
    TargetAudience,
    TaskType,
    VoiceStyle,
)


class PersonaAgent(BaseAgent):
    """Agent responsible for persona management and evolution"""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(agent_id="persona", *args, **kwargs)

    async def process(self, message: AgentMessage) -> Any:
        """Process persona-related tasks"""
        self.validate_message(message)

        task_handlers = {
            TaskType.CREATE_PERSONA: self._create_persona,
            TaskType.UPDATE_PERSONA: self._update_persona,
        }

        handler = task_handlers.get(message.task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {message.task_type}")

        return await handler(message.payload, message.context)

    async def _create_persona(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> Persona:
        """
        Create a new persona from user description.

        Expected payload:
            - user_description: str (user's rough description of desired persona)
            - platform: str (target platform, optional)
        """
        user_description = payload.get("user_description", "")
        target_platform = payload.get("platform", "xiaohongshu")

        self.log("INFO", f"Creating persona from description: {user_description[:100]}...")

        # Generate persona using LLM
        system_prompt = """You are a social media persona design expert. Your task is to create a detailed, structured persona configuration based on the user's description.

Output MUST be valid JSON matching this exact structure:
{
  "identity": {
    "name": "persona name/title",
    "tagline": "one-line positioning statement",
    "expertise": ["area1", "area2", "area3"]
  },
  "target_audience": {
    "primary": "primary audience description",
    "pain_points": ["pain1", "pain2", "pain3"],
    "goals": ["goal1", "goal2", "goal3"]
  },
  "voice_style": {
    "tone": "overall tone description",
    "language_patterns": ["pattern1", "pattern2", "pattern3"],
    "emoji_usage": "usage guidance"
  },
  "content_pillars": [
    {
      "name": "pillar name",
      "description": "pillar description",
      "frequency": "weekly",
      "examples": ["example topic 1", "example topic 2"]
    }
  ],
  "boundaries": {
    "avoid": ["thing to avoid 1", "thing to avoid 2"],
    "compliance": ["compliance rule 1", "compliance rule 2"]
  }
}

IMPORTANT:
- Be specific and actionable
- Ensure consistency across all fields
- Design for sustainable content creation (not one-off viral posts)
- Consider platform-specific best practices
"""

        user_prompt = f"""Create a persona for: {user_description}

Target platform: {target_platform}

Provide a complete persona configuration in JSON format."""

        response = await self.call_llm(user_prompt, system=system_prompt, temperature=0.7)

        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            persona_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.log("ERROR", f"Failed to parse LLM response as JSON: {e}")
            self.log("DEBUG", f"Response was: {response}")
            raise ValueError(f"Failed to generate valid persona configuration: {e}")

        # Create Persona object
        persona = Persona(
            id=f"persona_{uuid.uuid4().hex[:8]}",
            version="v1.0",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            identity=Identity(**persona_data["identity"]),
            target_audience=TargetAudience(**persona_data["target_audience"]),
            voice_style=VoiceStyle(**persona_data["voice_style"]),
            content_pillars=[
                ContentPillar(**pillar) for pillar in persona_data["content_pillars"]
            ],
            boundaries=Boundaries(**persona_data["boundaries"]),
            platforms=[PlatformType(target_platform)],
        )

        # Save to knowledges
        self.kb.save_persona(persona)

        # Save initial version record
        version_record = PersonaVersion(
            version="v1.0",
            timestamp=datetime.now(),
            changes=["Initial persona creation"],
            reason="User request",
            expected_impact="Establish baseline persona",
            author=context.get("user_id", "user"),
            approved=True,
        )
        self.kb.save_persona_version(persona.id, version_record)

        self.log("INFO", f"Created persona: {persona.id} - {persona.identity.name}")
        return persona

    async def _update_persona(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> Persona:
        """
        Update an existing persona.

        Expected payload:
            - persona_id: str
            - changes: dict (fields to update)
            - reason: str (why updating)
        """
        persona_id = payload.get("persona_id")
        changes = payload.get("changes", {})
        reason = payload.get("reason", "User requested update")

        if not persona_id:
            raise ValueError("persona_id is required")

        # Load existing persona
        persona = self.kb.load_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        self.log("INFO", f"Updating persona {persona_id}: {list(changes.keys())}")

        # Apply changes
        persona_dict = persona.model_dump()
        for key, value in changes.items():
            if key in persona_dict:
                persona_dict[key] = value

        # Increment version
        old_version = persona.version
        version_parts = old_version.lstrip("v").split(".")
        major, minor = int(version_parts[0]), int(version_parts[1])
        minor += 1
        new_version = f"v{major}.{minor}"

        persona_dict["version"] = new_version
        persona_dict["updated_at"] = datetime.now()

        # Create updated persona
        updated_persona = Persona(**persona_dict)

        # Analyze expected impact using LLM
        impact = await self._analyze_impact(persona, updated_persona, reason)

        # Save updated persona
        self.kb.save_persona(updated_persona)

        # Save version record
        change_descriptions = [f"Updated {k}" for k in changes.keys()]
        version_record = PersonaVersion(
            version=new_version,
            timestamp=datetime.now(),
            changes=change_descriptions,
            reason=reason,
            expected_impact=impact,
            author=context.get("user_id", "user"),
            approved=True,
        )
        self.kb.save_persona_version(persona_id, version_record)

        self.log("INFO", f"Updated persona to {new_version}")
        return updated_persona

    async def _analyze_impact(
        self, old_persona: Persona, new_persona: Persona, reason: str
    ) -> str:
        """Analyze expected impact of persona changes using LLM"""
        prompt = f"""Analyze the impact of these persona changes:

REASON FOR CHANGE:
{reason}

OLD PERSONA:
- Identity: {old_persona.identity.name} - {old_persona.identity.tagline}
- Content Pillars: {[p.name for p in old_persona.content_pillars]}
- Voice: {old_persona.voice_style.tone}

NEW PERSONA:
- Identity: {new_persona.identity.name} - {new_persona.identity.tagline}
- Content Pillars: {[p.name for p in new_persona.content_pillars]}
- Voice: {new_persona.voice_style.tone}

Provide a concise (1-2 sentence) analysis of the expected impact on content performance and audience perception."""

        response = await self.call_llm(prompt, temperature=0.5, max_tokens=200)
        return response.strip()

    async def validate_persona(self, persona: Persona) -> Dict[str, Any]:
        """
        Validate persona for internal consistency and sustainability.

        Returns:
            Validation report with issues and suggestions
        """
        self.log("INFO", f"Validating persona {persona.id}")

        prompt = f"""Validate this social media persona for:
1. Internal consistency (identity vs content pillars vs voice)
2. Market positioning clarity (unique value proposition)
3. Content sustainability (can produce content long-term)

PERSONA:
Identity: {persona.identity.name} - {persona.identity.tagline}
Expertise: {persona.identity.expertise}
Target Audience: {persona.target_audience.primary}
Content Pillars: {[p.name for p in persona.content_pillars]}
Voice: {persona.voice_style.tone}

Provide your analysis in JSON format:
{{
  "overall_score": <0-100>,
  "consistency_score": <0-100>,
  "clarity_score": <0-100>,
  "sustainability_score": <0-100>,
  "issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1", "suggestion2"]
}}"""

        response = await self.call_llm(prompt, temperature=0.3, max_tokens=500)

        try:
            # Extract JSON
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            validation_result = json.loads(json_str)
            return validation_result
        except json.JSONDecodeError:
            self.log("WARNING", "Failed to parse validation response")
            return {
                "overall_score": 70,
                "consistency_score": 70,
                "clarity_score": 70,
                "sustainability_score": 70,
                "issues": [],
                "suggestions": [],
            }

    async def suggest_optimizations(
        self, persona_id: str, trend_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Suggest persona optimizations based on performance data.

        Args:
            persona_id: Persona ID
            trend_data: Performance trends and insights

        Returns:
            List of optimization suggestions
        """
        persona = self.kb.load_persona(persona_id)
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        self.log("INFO", f"Generating optimization suggestions for {persona_id}")

        prompt = f"""Based on performance data, suggest persona optimizations:

CURRENT PERSONA:
Identity: {persona.identity.name} - {persona.identity.tagline}
Content Pillars: {[p.name for p in persona.content_pillars]}
Voice: {persona.voice_style.tone}

PERFORMANCE DATA:
{json.dumps(trend_data, indent=2, ensure_ascii=False)}

Provide 2-4 specific, actionable optimization suggestions in JSON format:
[
  {{
    "area": "identity|content_pillars|voice_style|boundaries",
    "suggestion": "specific suggestion",
    "rationale": "why this would help",
    "expected_impact": "what to expect"
  }}
]"""

        response = await self.call_llm(prompt, temperature=0.6, max_tokens=800)

        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            suggestions = json.loads(json_str)
            return suggestions
        except json.JSONDecodeError:
            self.log("WARNING", "Failed to parse optimization suggestions")
            return []


# Deprecated alias for backward compatibility
PersonaLabAgent = PersonaAgent
