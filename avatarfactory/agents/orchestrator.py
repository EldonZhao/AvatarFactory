"""
Orchestrator Agent - Main controller that coordinates all sub-agents.
"""

import json
from typing import Any, Dict, List, Optional

from avatarfactory.agents.base import BaseAgent
from avatarfactory.agents.content import ContentAgent
from avatarfactory.agents.persona import PersonaAgent
from avatarfactory.agents.review import ReviewAgent
from avatarfactory.models.schemas import (
    AgentMessage,
    Content,
    Intent,
    Persona,
    ReviewReport,
    TaskType,
)


class OrchestratorAgent(BaseAgent):
    """Main orchestrator that coordinates all sub-agents"""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(agent_id="orchestrator", *args, **kwargs)

        # Initialize sub-agents
        self.persona_agent = PersonaAgent(
            knowledge_base=self.kb,
            llm_provider=self.llm_provider,
        )
        self.content_agent = ContentAgent(
            knowledge_base=self.kb,
            llm_provider=self.llm_provider,
        )
        self.review_agent = ReviewAgent(
            knowledge_base=self.kb,
            llm_provider=self.llm_provider,
        )

        # Evolution agent (lazy initialization)
        self._evolution_agent: Optional[Any] = None

        # Deprecated aliases for backward compatibility
        self.persona_lab = self.persona_agent
        self.content_lab = self.content_agent

    @property
    def evolution_agent(self) -> Any:
        """Lazily initialize evolution agent."""
        if self._evolution_agent is None:
            from avatarfactory.agents.evolution import EvolutionAgent
            self._evolution_agent = EvolutionAgent(
                knowledge_base=self.kb,
                llm_provider=self.llm_provider,
            )
        return self._evolution_agent

    async def process(self, message: AgentMessage) -> Any:
        """Process user request by coordinating sub-agents"""
        self.log("INFO", f"Processing user request")
        return await self._handle_user_input(
            message.payload.get("user_input", ""),
            context=message.payload,
        )

    async def _handle_user_input(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for user interactions.

        Args:
            user_input: Natural language user request
            context: Additional context (e.g., persona_id from scheduler)

        Returns:
            Result dictionary with appropriate response
        """
        self.log("INFO", f"User input: {user_input[:100]}...")
        context = context or {}

        # Step 1: Understand user intent
        intent = await self._understand_intent(user_input)
        self.log("INFO", f"Detected intent: {intent.intent_type}")

        # Merge context into parameters (e.g., persona_id from scheduler)
        if context.get("persona_id") and "persona_id" not in intent.parameters:
            intent.parameters["persona_id"] = context["persona_id"]

        # Step 2: Route to appropriate handler
        handlers = {
            "create_persona": self._handle_create_persona,
            "generate_content": self._handle_generate_content,
            "discover_trends": self._handle_discover_trends,
            "analyze_data": self._handle_analyze_data,
            "optimize_persona": self._handle_optimize_persona,
            # Evolution intents
            "evolve_persona": self._handle_evolve_persona,
            "review_suggestion": self._handle_review_suggestion,
            "show_suggestions": self._handle_show_suggestions,
            "agent_config": self._handle_agent_config,
            "rollback": self._handle_rollback,
        }

        handler = handlers.get(intent.intent_type)
        if not handler:
            return {
                "status": "error",
                "message": f"Unknown intent type: {intent.intent_type}",
            }

        # Step 3: Execute handler
        try:
            result = await handler(intent.parameters, user_input)
            return {"status": "success", "data": result}
        except Exception as e:
            self.log("ERROR", f"Handler failed: {e}")
            return {"status": "error", "message": str(e)}

    async def _understand_intent(self, user_input: str) -> Intent:
        """Parse user input to understand intent"""

        system_prompt = """You are an intent classifier. Analyze the user's request and determine their intent.

Possible intents:
- create_persona: User wants to create a new persona
- generate_content: User wants to generate content for an existing persona
- discover_trends: User wants to discover trending topics, hot topics, or what's popular on social platforms
- analyze_data: User wants to analyze performance data or statistics
- optimize_persona: User wants to optimize an existing persona
- evolve_persona: User wants to suggest or apply changes to persona (e.g., "make it more casual", "change the tone")
- review_suggestion: User wants to approve or reject a pending suggestion (e.g., "approve suggestion X", "reject")
- show_suggestions: User wants to see pending evolution suggestions
- agent_config: User wants to modify agent behavior settings (e.g., "make content longer", "increase creativity")
- rollback: User wants to rollback to a previous persona version

Output MUST be valid JSON:
{
  "intent_type": "create_persona|generate_content|discover_trends|analyze_data|optimize_persona|evolve_persona|review_suggestion|show_suggestions|agent_config|rollback",
  "parameters": {
    // Extract relevant parameters from user input
    // For discover_trends: include "platform" if mentioned (bluesky, twitter, xiaohongshu, etc.)
    // For evolve_persona: include "user_feedback" with the suggestion
    // For review_suggestion: include "suggestion_id" and "approved" (boolean)
    // For rollback: include "version" (e.g., "v1.0")
  },
  "confidence": <0.0-1.0>
}"""

        user_prompt = f"User request: {user_input}\n\nClassify the intent and extract parameters."

        response = await self.call_llm(user_prompt, system=system_prompt, temperature=0.3)

        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            intent_data = json.loads(json_str)
            return Intent(**intent_data)
        except json.JSONDecodeError as e:
            self.log("WARNING", f"Failed to parse intent, defaulting to create_persona: {e}")
            return Intent(
                intent_type="create_persona",
                parameters={"user_description": user_input},
                confidence=0.5,
            )

    async def _handle_create_persona(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle persona creation workflow"""

        self.log("INFO", "Starting persona creation workflow")

        # Step 1: Create persona via Persona Agent
        message = AgentMessage(
            sender="orchestrator",
            receiver="persona",
            task_type=TaskType.CREATE_PERSONA,
            payload={
                "user_description": parameters.get("user_description", original_input),
                "platform": parameters.get("platform", "xiaohongshu"),
            },
            context={},
        )

        persona = await self.persona_agent.process(message)

        # Step 2: Validate persona
        validation = await self.persona_agent.validate_persona(persona)

        # Step 3: Generate sample content (1 piece)
        try:
            # Get first content pillar
            first_pillar = persona.content_pillars[0] if persona.content_pillars else None
            if first_pillar and first_pillar.examples:
                sample_topic = first_pillar.examples[0]

                content_message = AgentMessage(
                    sender="orchestrator",
                    receiver="content",
                    task_type=TaskType.GENERATE_CONTENT,
                    payload={
                        "persona_id": persona.id,
                        "pillar": first_pillar.name,
                        "topic": sample_topic,
                    },
                    context={},
                )

                sample_content = await self.content_agent.process(content_message)

                # Step 4: Review the sample content
                review_message = AgentMessage(
                    sender="orchestrator",
                    receiver="review",
                    task_type=TaskType.REVIEW_CONTENT,
                    payload={
                        "content_id": sample_content.id,
                        "persona_id": persona.id,
                    },
                    context={},
                )

                review_report = await self.review_agent.process(review_message)
            else:
                sample_content = None
                review_report = None

        except Exception as e:
            self.log("WARNING", f"Failed to generate sample content: {e}")
            sample_content = None
            review_report = None

        # Return comprehensive result
        return {
            "persona": persona.model_dump(),
            "validation": validation,
            "sample_content": sample_content.model_dump() if sample_content else None,
            "review": review_report.model_dump() if review_report else None,
            "message": (
                f"✅ Created persona '{persona.identity.name}' (ID: {persona.id})\n"
                f"Validation score: {validation.get('overall_score', 'N/A')}/100\n"
                + (
                    f"Sample content generated with review score: {review_report.overall_score}/100"
                    if review_report
                    else ""
                )
            ),
        }

    async def _handle_generate_content(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle content generation workflow"""

        persona_id = parameters.get("persona_id")
        if not persona_id:
            # Try to find the most recent persona (sorted by created_at desc)
            personas = self.kb.list_personas()
            if not personas:
                return {"message": "No persona found. Please create a persona first."}
            persona_id = personas[0]
            self.log("WARNING", f"No persona_id specified, using most recent: {persona_id}")

        persona = self.kb.load_persona(persona_id)
        if not persona:
            return {"message": f"Persona {persona_id} not found"}

        self.log("INFO", f"Generating content for persona {persona_id} ({persona.identity.name})")

        # Extract topic from parameters or use default
        topic = parameters.get("topic")
        pillar = parameters.get("pillar")

        if not topic:
            # Use original input as topic
            topic = original_input

        if not pillar and persona.content_pillars:
            pillar = persona.content_pillars[0].name

        # Generate content
        content_message = AgentMessage(
            sender="orchestrator",
            receiver="content",
            task_type=TaskType.GENERATE_CONTENT,
            payload={
                "persona_id": persona_id,
                "pillar": pillar,
                "topic": topic,
                "variant_count": parameters.get("variant_count", 1),
            },
            context={},
        )

        content = await self.content_agent.process(content_message)

        # Review content
        review_message = AgentMessage(
            sender="orchestrator",
            receiver="review",
            task_type=TaskType.REVIEW_CONTENT,
            payload={"content_id": content.id, "persona_id": persona_id},
            context={},
        )

        review_report = await self.review_agent.process(review_message)

        return {
            "content": content.model_dump(),
            "review": review_report.model_dump(),
            "message": (
                f"✅ Generated content: '{content.title}'\n"
                f"Review score: {review_report.overall_score}/100\n"
                f"Status: {'✅ Approved' if review_report.overall_score >= 70 else '⚠️ Needs revision'}"
            ),
        }

    async def _handle_discover_trends(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle trending topics discovery workflow"""

        persona_id = parameters.get("persona_id")
        if not persona_id:
            personas = self.kb.list_personas()
            if not personas:
                return {"message": "No persona found. Please create a persona first."}
            persona_id = personas[0]

        persona = self.kb.load_persona(persona_id)
        if not persona:
            return {"message": f"Persona {persona_id} not found"}

        platform = parameters.get("platform", "bluesky")

        self.log("INFO", f"Discovering trends for persona {persona_id} on {platform}")

        # Import DiscoveryAgent
        from avatarfactory.agents.discovery import DiscoveryAgent

        discovery_agent = DiscoveryAgent(
            knowledge_base=self.kb,
            llm_provider=self.llm_provider,
        )

        try:
            result = await discovery_agent.discover_and_analyze(
                persona_id=persona_id,
                platform=platform,
                limit=20,
            )

            if result.get("status") != "success":
                return {"message": f"Discovery failed: {result.get('message', 'Unknown error')}"}

            data = result.get("data", {})
            ideas = data.get("ideas", [])
            trending_count = data.get("trending_count", 0)

            # Build message with top ideas
            ideas_text = ""
            if ideas:
                ideas_text = "\n\nTop content ideas:\n" + "\n".join([
                    f"  • {idea.get('topic', '')} ({idea.get('estimated_engagement', 'medium')} engagement)"
                    for idea in ideas[:5]
                ])

            return {
                "trending_count": trending_count,
                "ideas": ideas,
                "message": (
                    f"🔍 Discovered {trending_count} trending posts on {platform}\n"
                    f"Generated {len(ideas)} content ideas for {persona.identity.name}"
                    f"{ideas_text}"
                ),
            }

        except Exception as e:
            self.log("ERROR", f"Discovery failed: {e}")
            return {"message": f"Discovery failed: {str(e)}"}

    async def _handle_analyze_data(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle data analysis workflow (MVP: basic stats)"""

        persona_id = parameters.get("persona_id")
        if not persona_id:
            personas = self.kb.list_personas()
            if not personas:
                return {"message": "No persona found."}
            persona_id = personas[0]

        # Get content statistics
        published_content = self.kb.list_content(persona_id, status="published")
        draft_content = self.kb.list_content(persona_id, status="draft")

        stats = {
            "total_published": len(published_content),
            "total_drafts": len(draft_content),
            "avg_review_score": (
                sum(c.review_score for c in draft_content if c.review_score)
                / len([c for c in draft_content if c.review_score])
                if any(c.review_score for c in draft_content)
                else 0
            ),
        }

        return {
            "stats": stats,
            "message": (
                f"📊 Analysis for persona {persona_id}:\n"
                f"- Published content: {stats['total_published']}\n"
                f"- Draft content: {stats['total_drafts']}\n"
                f"- Avg review score: {stats['avg_review_score']:.1f}/100"
            ),
        }

    async def _handle_optimize_persona(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle persona optimization workflow (MVP: suggestions only)"""

        persona_id = parameters.get("persona_id")
        if not persona_id:
            personas = self.kb.list_personas()
            if not personas:
                return {"message": "No persona found."}
            persona_id = personas[0]

        # Get basic trend data
        published_content = self.kb.list_content(persona_id, status="published")

        trend_data = {
            "total_content": len(published_content),
            "content_by_pillar": {},
        }

        for content in published_content:
            pillar = content.pillar
            if pillar not in trend_data["content_by_pillar"]:
                trend_data["content_by_pillar"][pillar] = 0
            trend_data["content_by_pillar"][pillar] += 1

        # Get optimization suggestions
        suggestions = await self.persona_agent.suggest_optimizations(persona_id, trend_data)

        return {
            "suggestions": suggestions,
            "message": f"💡 Found {len(suggestions)} optimization suggestions",
        }

    # =========================================================================
    # Evolution Handlers
    # =========================================================================

    async def _handle_evolve_persona(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle persona evolution - generate suggestions from user feedback"""

        persona_id = parameters.get("persona_id")
        if not persona_id:
            personas = self.kb.list_personas()
            if not personas:
                return {"message": "No persona found."}
            persona_id = personas[0]

        # Get user feedback from parameters or use original input
        user_feedback = parameters.get("user_feedback", original_input)

        # Generate suggestions via evolution agent
        suggestions = await self.evolution_agent.generate_suggestions_from_user_input(
            persona_id, user_feedback
        )

        if not suggestions:
            return {
                "message": "Could not generate suggestions from the feedback.",
                "suggestions": [],
            }

        # Format suggestions for display
        suggestion_list = []
        for s in suggestions:
            suggestion_list.append({
                "id": s.id,
                "severity": s.severity.value,
                "area": s.area.value,
                "suggestion": s.suggestion,
                "rationale": s.rationale,
                "expected_impact": s.expected_impact,
            })

        return {
            "suggestions": suggestion_list,
            "count": len(suggestions),
            "message": (
                f"🔄 Generated {len(suggestions)} suggestion(s):\n\n"
                + "\n".join([
                    f"  [{s['severity']}] {s['area']}: {s['suggestion']}\n"
                    f"     Rationale: {s['rationale']}\n"
                    f"     Use 'approve suggestion {s['id']}' or 'reject suggestion {s['id']}' to review."
                    for s in suggestion_list
                ])
            ),
        }

    async def _handle_review_suggestion(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle suggestion review - approve or reject"""

        persona_id = parameters.get("persona_id")
        if not persona_id:
            personas = self.kb.list_personas()
            if not personas:
                return {"message": "No persona found."}
            persona_id = personas[0]

        suggestion_id = parameters.get("suggestion_id")
        if not suggestion_id:
            # Try to find suggestion ID from pending suggestions
            pending = self.kb.list_evolution_suggestions(persona_id, status="pending")
            if pending:
                suggestion_id = pending[0].id
            else:
                return {"message": "No pending suggestions to review."}

        approved = parameters.get("approved", True)
        rejection_reason = parameters.get("rejection_reason")

        # Review the suggestion
        suggestion = await self.evolution_agent.review_suggestion(
            persona_id, suggestion_id, approved, rejection_reason
        )

        if approved:
            return {
                "suggestion": suggestion.model_dump(mode="json"),
                "message": (
                    f"✅ Approved and applied suggestion: {suggestion.suggestion}\n"
                    f"New version: {suggestion.applied_version}"
                ),
            }
        else:
            return {
                "suggestion": suggestion.model_dump(mode="json"),
                "message": f"❌ Rejected suggestion: {suggestion.suggestion}",
            }

    async def _handle_show_suggestions(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle showing pending evolution suggestions"""

        persona_id = parameters.get("persona_id")
        if not persona_id:
            personas = self.kb.list_personas()
            if not personas:
                return {"message": "No persona found."}
            persona_id = personas[0]

        status = parameters.get("status", "pending")
        suggestions = self.kb.list_evolution_suggestions(persona_id, status=status)

        if not suggestions:
            return {
                "suggestions": [],
                "message": f"No {status} suggestions found.",
            }

        suggestion_list = []
        for s in suggestions:
            suggestion_list.append({
                "id": s.id,
                "severity": s.severity.value,
                "area": s.area.value,
                "suggestion": s.suggestion,
                "confidence": s.confidence,
                "created_at": s.created_at.isoformat(),
            })

        return {
            "suggestions": suggestion_list,
            "count": len(suggestions),
            "message": (
                f"📋 {len(suggestions)} {status} suggestion(s):\n\n"
                + "\n".join([
                    f"  [{s['severity']}] {s['id']}: {s['suggestion']}"
                    for s in suggestion_list
                ])
            ),
        }

    async def _handle_agent_config(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle agent configuration changes"""

        persona_id = parameters.get("persona_id")
        if not persona_id:
            personas = self.kb.list_personas()
            if not personas:
                return {"message": "No persona found."}
            persona_id = personas[0]

        agent_type = parameters.get("agent_type", "content")
        updates = parameters.get("updates", {})

        # If no updates provided, interpret user feedback as config change
        if not updates and original_input:
            # Use evolution agent to generate config suggestion
            suggestions = await self.evolution_agent.generate_suggestions_from_user_input(
                persona_id, original_input
            )
            # Filter to agent config suggestions
            config_suggestions = [
                s for s in suggestions
                if s.area.value == "agent_config"
            ]
            if config_suggestions:
                return {
                    "suggestions": [s.model_dump(mode="json") for s in config_suggestions],
                    "message": f"Generated {len(config_suggestions)} agent config suggestions. Use 'approve' to apply.",
                }

        # Apply direct config updates
        if updates:
            from avatarfactory.core.agent_config import AgentConfigManager
            config_manager = AgentConfigManager(self.kb)
            new_config = config_manager.update_config(persona_id, agent_type, updates)
            return {
                "config": new_config.model_dump(),
                "message": f"✅ Updated {agent_type} agent configuration.",
            }

        return {"message": "No configuration changes specified."}

    async def _handle_rollback(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle persona rollback to previous version"""

        persona_id = parameters.get("persona_id")
        if not persona_id:
            personas = self.kb.list_personas()
            if not personas:
                return {"message": "No persona found."}
            persona_id = personas[0]

        version = parameters.get("version")
        if not version:
            # Show available versions
            versions = self.kb.list_persona_versions(persona_id)
            if len(versions) <= 1:
                return {"message": "No previous versions available for rollback."}
            return {
                "versions": versions,
                "message": (
                    f"Available versions: {', '.join(versions)}\n"
                    "Specify a version to rollback to."
                ),
            }

        # Perform rollback
        persona = await self.evolution_agent.rollback_change(persona_id, version)

        return {
            "persona": persona.model_dump(mode="json"),
            "message": f"⏪ Rolled back to version {version}. Current version: {persona.version}",
        }
