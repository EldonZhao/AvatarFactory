"""
Quick Start Guide for AvatarFactory
"""

# Example 1: Create a persona and generate content programmatically
import asyncio
import os
from anthropic import Anthropic
from avatarfactory.core.knowledges import KnowledgeBase
from avatarfactory.agents.orchestrator import OrchestratorAgent
from avatarfactory.models.schemas import AgentMessage


async def main():
    # Setup
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Please set ANTHROPIC_API_KEY environment variable")
        return

    kb = KnowledgeBase("./knowledge")
    client = Anthropic(api_key=api_key)
    orchestrator = OrchestratorAgent(
        knowledge_base=kb,
        anthropic_client=client,
        model="claude-3-5-sonnet-20241022",
    )

    # Example 1: Create a persona
    print("=== Creating Persona ===")
    message = AgentMessage(
        sender="user",
        receiver="orchestrator",
        task_type="chat",
        payload={
            "user_input": "Create a persona for an AI tools reviewer targeting product managers on Xiaohongshu"
        },
        context={},
    )

    result = await orchestrator.process(message)
    if result["status"] == "success":
        data = result["data"]
        print(f"✅ {data.get('message')}")
        persona_id = data["persona"]["id"]

        # Example 2: Generate content
        print("\n=== Generating Content ===")
        content_message = AgentMessage(
            sender="user",
            receiver="orchestrator",
            task_type="chat",
            payload={
                "user_input": "Generate content comparing Notion AI vs Claude for product documentation",
                "persona_id": persona_id,
            },
            context={},
        )

        content_result = await orchestrator.process(content_message)
        if content_result["status"] == "success":
            content_data = content_result["data"]
            print(f"✅ {content_data.get('message')}")

            # Show content details
            content = content_data["content"]
            print(f"\nTitle: {content['title']}")
            print(f"Review Score: {content_data['review']['overall_score']}/100")
    else:
        print(f"❌ Error: {result.get('message')}")


if __name__ == "__main__":
    asyncio.run(main())
