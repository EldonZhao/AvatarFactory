"""
Orchestrator Agent - Main controller that coordinates all sub-agents.
"""

import json
from typing import Any, Dict, Optional

from avatarfactory.agents.base import BaseAgent
from avatarfactory.agents.content import ContentAgent
from avatarfactory.agents.persona import PersonaAgent
from avatarfactory.agents.review import ReviewAgent
from avatarfactory.models.schemas import (
    AgentMessage,
    Intent,
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
        self.log("INFO", "Processing user request")
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

        # Check if we have a persona_id in context
        has_persona = bool(context.get("persona_id"))

        # Step 1: Understand user intent (with persona awareness)
        try:
            intent = await self._understand_intent(user_input, has_persona=has_persona)
        except Exception as e:
            self.log("ERROR", f"Intent understanding failed: {e}")
            return {
                "status": "error",
                "message": (
                    "LLM service is temporarily unavailable. "
                    "Please check model provider settings and retry."
                ),
                "error_type": "llm_unavailable",
            }
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
            # No-persona intents (recommendation-related)
            "browse_recommendations": self._handle_browse_recommendations,
            "create_from_recommendation": self._handle_create_from_recommendation,
            "view_trends": self._handle_view_trends,
            "list_personas": self._handle_list_personas,
            "help": self._handle_help,
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

    async def _understand_intent(self, user_input: str, has_persona: bool = True) -> Intent:
        """Parse user input to understand intent"""

        # Different prompt based on whether user has a persona selected
        if has_persona:
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
        else:
            # No persona selected - focus on persona discovery/creation intents
            system_prompt = """You are an intent classifier. The user has NOT selected any persona yet.
Analyze their request and determine what they want to do.

Possible intents (no persona selected):
- browse_recommendations: User wants to see recommended personas based on trends (e.g., "推荐", "推荐角色", "有什么推荐的角色", "show recommendations", "what personas do you recommend")
- view_trends: User wants to see current hot topics/trends (e.g., "热点", "趋势", "查看热点趋势", "what's trending", "show trends")
- create_from_recommendation: User wants to create a persona from a recommendation (e.g., "用推荐的xxx创建", "create from recommendation X")
- create_persona: User wants to create a new persona from a description (e.g., "创建一个科技博主", "create a tech blogger persona")
- list_personas: User wants to see existing personas (e.g., "有哪些角色", "列出所有角色", "list personas", "show my personas")
- help: User is asking for help or doesn't know what to do (e.g., "怎么用", "帮助", "help", "what can you do")

Output MUST be valid JSON:
{
  "intent_type": "browse_recommendations|view_trends|create_from_recommendation|create_persona|list_personas|help",
  "parameters": {
    // For create_persona: include "user_description"
    // For create_from_recommendation: include "recommendation_id" if specified
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
            self.log("WARNING", f"Failed to parse intent: {e}")
            # Default based on whether persona exists
            if has_persona:
                return Intent(
                    intent_type="create_persona",
                    parameters={"user_description": user_input},
                    confidence=0.5,
                )
            else:
                return Intent(
                    intent_type="browse_recommendations",
                    parameters={},
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

        # Import TopicAgent
        from avatarfactory.agents.topic import TopicAgent

        discovery_agent = TopicAgent(
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
                ideas_text = "\n\nTop content ideas:\n" + "\n".join(
                    [
                        f"  • {idea.get('topic', '')} ({idea.get('estimated_engagement', 'medium')} engagement)"
                        for idea in ideas[:5]
                    ]
                )

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
            suggestion_list.append(
                {
                    "id": s.id,
                    "severity": s.severity.value,
                    "area": s.area.value,
                    "suggestion": s.suggestion,
                    "rationale": s.rationale,
                    "expected_impact": s.expected_impact,
                }
            )

        return {
            "suggestions": suggestion_list,
            "count": len(suggestions),
            "message": (
                f"🔄 Generated {len(suggestions)} suggestion(s):\n\n"
                + "\n".join(
                    [
                        f"  [{s['severity']}] {s['area']}: {s['suggestion']}\n"
                        f"     Rationale: {s['rationale']}\n"
                        f"     Use 'approve suggestion {s['id']}' or 'reject suggestion {s['id']}' to review."
                        for s in suggestion_list
                    ]
                )
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
            suggestion_list.append(
                {
                    "id": s.id,
                    "severity": s.severity.value,
                    "area": s.area.value,
                    "suggestion": s.suggestion,
                    "confidence": s.confidence,
                    "created_at": s.created_at.isoformat(),
                }
            )

        return {
            "suggestions": suggestion_list,
            "count": len(suggestions),
            "message": (
                f"📋 {len(suggestions)} {status} suggestion(s):\n\n"
                + "\n".join(
                    [f"  [{s['severity']}] {s['id']}: {s['suggestion']}" for s in suggestion_list]
                )
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
            config_suggestions = [s for s in suggestions if s.area.value == "agent_config"]
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

    # =========================================================================
    # No-Persona Handlers (Recommendation-related)
    # =========================================================================

    async def _handle_browse_recommendations(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle browsing recommended personas"""

        limit = parameters.get("limit", 5)
        # Get recommendations from storage
        recommendations = self.kb.get_latest_recommendations(limit=limit)

        if not recommendations:
            return {
                "recommendations": [],
                "message": (
                    "📭 暂无推荐的角色。\n\n"
                    "系统每天会自动从社交平台分析热点并生成推荐。\n"
                    "你也可以直接创建角色，例如：\n"
                    "- 「创建一个科技博主」\n"
                    "- 「创建一个生活方式达人」"
                ),
            }

        # Format recommendations
        rec_list = []
        for rec in recommendations:
            rec_list.append(
                {
                    "id": rec.id,
                    "name": rec.name,
                    "tagline": rec.tagline,
                    "domain": rec.domain,
                    "expertise": rec.expertise,
                    "target_audience": rec.target_audience,
                    "relevance_score": rec.relevance_score,
                    "potential_score": rec.potential_score,
                    "rationale": rec.rationale,
                }
            )

        # Build display message
        rec_text = "\n\n".join(
            [
                f"**{i+1}. {r['name']}** ({r['domain']})\n"
                f"   {r['tagline']}\n"
                f"   目标受众: {r['target_audience']}\n"
                f"   热度: {r['relevance_score']:.0f} | 潜力: {r['potential_score']:.0f}\n"
                f"   ID: `{r['id']}`"
                for i, r in enumerate(rec_list)
            ]
        )

        return {
            "recommendations": rec_list,
            "count": len(rec_list),
            "message": (
                f"✨ 基于热点分析，为你推荐 {len(rec_list)} 个角色方向：\n\n"
                f"{rec_text}\n\n"
                "💡 输入「采用 <ID>」可基于推荐创建角色，或直接描述你想要的角色。"
            ),
        }

    async def _handle_create_from_recommendation(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle creating a persona from a recommendation"""

        rec_id = parameters.get("recommendation_id")

        if not rec_id:
            # Try to extract from input
            import re

            match = re.search(r"rec_persona_\w+", original_input)
            if match:
                rec_id = match.group(0)
            else:
                # Show available recommendations
                return await self._handle_browse_recommendations(parameters, original_input)

        # Load recommendation
        recommendation = self.kb.get_recommendation(rec_id)
        if not recommendation:
            return {"message": f"未找到推荐 {rec_id}。请使用「推荐」查看可用的推荐。"}

        # Build persona description from recommendation
        description = (
            f"创建一个{recommendation.domain}领域的角色：{recommendation.name}。\n"
            f"定位：{recommendation.tagline}\n"
            f"目标受众：{recommendation.target_audience}\n"
            f"专业领域：{', '.join(recommendation.expertise)}\n"
            f"内容支柱：{', '.join(recommendation.content_pillars)}\n"
            f"语调风格：{recommendation.suggested_tone}"
        )

        # Create persona using existing handler
        result = await self._handle_create_persona(
            {"user_description": description},
            description,
        )

        # Mark recommendation as adopted
        if result.get("persona"):
            persona_data = result["persona"]
            self.kb.mark_recommendation_adopted(rec_id, persona_data["id"])
            result["message"] = (
                f"✅ 基于推荐「{recommendation.name}」成功创建角色！\n\n"
                + result.get("message", "")
            )

        return result

    async def _handle_list_personas(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle listing existing personas"""

        persona_ids = self.kb.list_personas()

        if not persona_ids:
            return {
                "personas": [],
                "message": (
                    "📭 你还没有创建任何角色。\n\n"
                    "输入「推荐」查看基于热点的推荐角色，或直接描述你想创建的角色。"
                ),
            }

        personas = []
        for pid in persona_ids[:10]:  # Limit to 10
            persona = self.kb.load_persona(pid)
            if persona:
                personas.append(
                    {
                        "id": persona.id,
                        "name": persona.identity.name,
                        "tagline": persona.identity.tagline,
                        "expertise": persona.identity.expertise[:3],
                        "version": persona.version,
                    }
                )

        personas_text = "\n".join(
            [
                f"{i+1}. **{p['name']}** - {p['tagline']}\n   ID: `{p['id']}` | 版本: {p['version']}"
                for i, p in enumerate(personas)
            ]
        )

        return {
            "personas": personas,
            "count": len(personas),
            "message": (
                f"📋 你的角色列表 ({len(personas)} 个):\n\n"
                f"{personas_text}\n\n"
                "💡 在 chat 命令中使用 `--persona <ID>` 选择角色。"
            ),
        }

    async def _handle_view_trends(
        self, parameters: Dict[str, Any], original_input: str
    ) -> Dict[str, Any]:
        """Handle viewing current hot topics/trends"""

        # Get today's trend snapshots
        snapshots = self.kb.get_today_trend_snapshots()

        if not snapshots:
            # No trends captured today, get latest available
            snapshots = self.kb.get_latest_trend_snapshots(limit=5)

        if not snapshots:
            return {
                "trends": [],
                "message": (
                    "📭 暂无热点趋势数据。\n\n"
                    "系统每天 8:00 自动抓取各平台热点。你也可以运行 `avatarfactory scan-trends` 手动触发。\n\n"
                    "💡 热点趋势会用于生成角色推荐，帮助你发现有潜力的内容方向。"
                ),
            }

        # Build trends display
        trends_by_platform = {}
        for snap in snapshots:
            platform = snap.platform
            if platform not in trends_by_platform:
                trends_by_platform[platform] = snap

        trends_text = ""
        all_topics = []
        for platform, snap in trends_by_platform.items():
            topics = snap.trending_topics[:5] if snap.trending_topics else []
            hashtags = snap.trending_hashtags[:3] if snap.trending_hashtags else []
            all_topics.extend(topics)

            trends_text += f"\n**{platform.upper()}**\n"
            if topics:
                trends_text += "🔥 热门话题: " + ", ".join(topics) + "\n"
            if hashtags:
                trends_text += "# 热门标签: " + " ".join(hashtags) + "\n"
            if snap.analysis_summary:
                trends_text += f"💡 {snap.analysis_summary}\n"

        return {
            "trends": [
                {
                    "platform": snap.platform,
                    "topics": snap.trending_topics[:5] if snap.trending_topics else [],
                    "captured_at": snap.captured_at.isoformat(),
                }
                for snap in snapshots
            ],
            "message": (
                f"🔥 当前热点趋势\n{trends_text}\n\n"
                f"💡 输入「推荐」查看基于这些热点生成的角色推荐。"
            ),
        }

    async def _handle_help(self, parameters: Dict[str, Any], original_input: str) -> Dict[str, Any]:
        """Handle help request - guide user on what they can do"""

        # Check if there are any personas
        personas = self.kb.list_personas()
        recommendations = self.kb.get_latest_recommendations(limit=3)

        help_text = """👋 欢迎使用 AvatarFactory!

这是一个 AI 驱动的社交媒体角色管理系统，帮助你设计、模拟和优化社交角色。

**🚀 快速开始:**

"""
        if recommendations:
            help_text += f"""1️⃣ **查看推荐角色** - 输入「推荐」查看基于热点分析的 {len(recommendations)} 个推荐角色
2️⃣ **创建角色** - 直接描述你想要的角色，例如「创建一个科技博主」
"""
        else:
            help_text += """1️⃣ **创建角色** - 直接描述你想要的角色，例如「创建一个科技博主」
"""

        if personas:
            help_text += f"""3️⃣ **选择已有角色** - 你有 {len(personas)} 个角色，使用 `--persona <ID>` 选择
"""

        help_text += """
**📝 选择角色后可以:**
- 生成内容：「写一篇关于AI的帖子」
- 发现热点：「看看最近有什么热点」
- 优化角色：「让角色风格更轻松一些」
- 查看数据：「分析我的内容表现」

**💡 提示:** 输入「推荐」或「角色列表」开始探索！
"""

        return {
            "has_personas": len(personas) > 0,
            "has_recommendations": len(recommendations) > 0,
            "message": help_text,
        }
