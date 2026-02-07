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

        # Deprecated aliases for backward compatibility
        self.persona_lab = self.persona_agent
        self.content_lab = self.content_agent

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
            "analyze_data": self._handle_analyze_data,
            "optimize_persona": self._handle_optimize_persona,
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
- analyze_data: User wants to analyze performance data
- optimize_persona: User wants to optimize an existing persona

Output MUST be valid JSON:
{
  "intent_type": "create_persona|generate_content|analyze_data|optimize_persona",
  "parameters": {
    // Extract relevant parameters from user input
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
