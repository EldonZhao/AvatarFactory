"""
AvatarFactory CLI - Command-line interface for interacting with AvatarFactory.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env file from current directory or project root
load_dotenv()

# Fix Windows console encoding for Unicode/Chinese characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from avatarfactory.agents.orchestrator import OrchestratorAgent
from avatarfactory.core.knowledge_base import KnowledgeBase
from avatarfactory.core.llm_provider import LLMProviderFactory
from avatarfactory.models.schemas import AgentMessage
from avatarfactory.connectors import get_connector, ConnectorConfig

app = typer.Typer(
    name="avatarfactory",
    help="AvatarFactory - A Persona Factory for social platforms",
    add_completion=False,
)

console = Console(force_terminal=True)


def get_orchestrator() -> OrchestratorAgent:
    """Initialize orchestrator agent with LLM provider from environment"""
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base")

    try:
        provider = LLMProviderFactory.from_env()
        if not provider.validate_config():
            provider_type = os.getenv("AVATARFACTORY_LLM_PROVIDER", "anthropic")
            console.print(
                f"[red]Error: {provider_type} provider not configured correctly[/red]"
            )
            console.print("Please check your .env file and set the required API keys.")
            raise typer.Exit(1)
    except ImportError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error initializing LLM provider: {e}[/red]")
        raise typer.Exit(1)

    kb = KnowledgeBase(kb_path)

    return OrchestratorAgent(
        knowledge_base=kb,
        llm_provider=provider,
    )


@app.command()
def chat(
    persona_id: Optional[str] = typer.Option(
        None, "--persona", "-p", help="Persona ID to work with"
    ),
):
    """
    Interactive chat mode - talk to AvatarFactory naturally.

    Examples:
        avatarfactory chat
        avatarfactory chat --persona persona_abc123
    """
    provider_type = os.getenv("AVATARFACTORY_LLM_PROVIDER", "anthropic")
    model = os.getenv("AVATARFACTORY_MODEL", "default")

    console.print(
        Panel.fit(
            "[bold cyan]AvatarFactory Interactive Mode[/bold cyan]\n"
            f"Using: {provider_type} ({model})\n"
            "Talk to me naturally! I'll help you create personas, generate content, and more.\n"
            "Type 'exit' or 'quit' to end the session.",
            border_style="cyan",
        )
    )

    orchestrator = get_orchestrator()

    if persona_id:
        console.print(f"\n[dim]Working with persona: {persona_id}[/dim]\n")

    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ")

            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("\n[cyan]Goodbye![/cyan]")
                break

            if not user_input.strip():
                continue

            # Show thinking indicator
            with console.status("[bold cyan]Thinking...", spinner="dots"):
                message = AgentMessage(
                    sender="user",
                    receiver="orchestrator",
                    task_type="chat",  # type: ignore
                    payload={"user_input": user_input, "persona_id": persona_id},
                    context={},
                )

                # Run async function
                result = asyncio.run(orchestrator.process(message))

            # Display result
            if result.get("status") == "error":
                console.print(f"\n[red]Error: {result.get('message')}[/red]")
            else:
                data = result.get("data", {})
                message = data.get("message", "")

                console.print(f"\n[bold cyan]AvatarFactory:[/bold cyan]\n{message}")

                # Show additional data if available
                if "persona" in data:
                    persona_data = data["persona"]
                    console.print(
                        f"\n[dim]Persona ID: {persona_data.get('id')}[/dim]"
                    )

                if "content" in data:
                    content_data = data["content"]
                    console.print(
                        f"\n[dim]Content ID: {content_data.get('id')}[/dim]"
                    )

        except KeyboardInterrupt:
            console.print("\n\n[cyan]Goodbye![/cyan]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


@app.command()
def create_persona(
    description: str = typer.Argument(..., help="Describe your desired persona"),
    platform: str = typer.Option(
        "xiaohongshu", "--platform", "-t", help="Target platform"
    ),
):
    """
    Create a new persona.

    Example:
        avatarfactory create-persona "AI tools reviewer for product managers"
    """
    console.print(Panel.fit(f"Creating persona: {description}", border_style="cyan"))

    orchestrator = get_orchestrator()

    with console.status("[bold cyan]Creating persona...", spinner="dots"):
        message = AgentMessage(
            sender="user",
            receiver="orchestrator",
            task_type="chat",  # type: ignore
            payload={
                "user_input": f"Create a persona: {description}. Platform: {platform}"
            },
            context={},
        )

        result = asyncio.run(orchestrator.process(message))

    if result.get("status") == "error":
        console.print(f"[red]Error: {result.get('message')}[/red]")
        raise typer.Exit(1)

    data = result.get("data", {})
    console.print(f"\n[green]{data.get('message')}[/green]")

    # Show persona details
    if "persona" in data:
        persona = data["persona"]
        console.print(f"\n[bold]Persona Details:[/bold]")
        console.print(f"  ID: {persona.get('id')}")
        console.print(f"  Name: {persona['identity'].get('name')}")
        console.print(f"  Tagline: {persona['identity'].get('tagline')}")


@app.command()
def generate(
    topic: str = typer.Argument(..., help="Topic to write about"),
    persona_id: Optional[str] = typer.Option(
        None, "--persona", "-p", help="Persona ID (uses most recent if not specified)"
    ),
    variants: int = typer.Option(1, "--variants", "-n", help="Number of variants"),
):
    """
    Generate content for a topic.

    Example:
        avatarfactory generate "Notion vs Obsidian comparison"
        avatarfactory generate "AI workflow tips" --persona persona_abc123 --variants 3
    """
    console.print(Panel.fit(f"Generating content: {topic}", border_style="cyan"))

    orchestrator = get_orchestrator()

    with console.status("[bold cyan]Generating content...", spinner="dots"):
        message = AgentMessage(
            sender="user",
            receiver="orchestrator",
            task_type="chat",  # type: ignore
            payload={
                "user_input": f"Generate content about: {topic}",
                "persona_id": persona_id,
            },
            context={},
        )

        result = asyncio.run(orchestrator.process(message))

    if result.get("status") == "error":
        console.print(f"[red]Error: {result.get('message')}[/red]")
        raise typer.Exit(1)

    data = result.get("data", {})
    console.print(f"\n[green]{data.get('message')}[/green]")

    # Show content preview
    if "content" in data:
        content = data["content"]
        console.print(f"\n[bold]Content Preview:[/bold]")
        console.print(f"  Title: {content.get('title')}")
        console.print(f"  Platform: {content.get('platform')}")
        console.print(f"  Content ID: {content.get('id')}")

        # Show body preview
        body = content.get("body", "")
        preview = body[:200] + "..." if len(body) > 200 else body
        console.print(f"\n[dim]{preview}[/dim]")


@app.command()
def list_personas():
    """List all personas in the knowledge base."""
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base")
    kb = KnowledgeBase(kb_path)

    personas = kb.list_personas()

    if not personas:
        console.print("[yellow]No personas found. Create one with 'avatarfactory create-persona'[/yellow]")
        return

    table = Table(title="Personas")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Platform", style="yellow")

    for persona_id in personas:
        persona = kb.load_persona(persona_id)
        if persona:
            table.add_row(
                persona_id,
                persona.identity.name,
                ", ".join(p.value for p in persona.platforms),
            )

    console.print(table)


@app.command()
def list_content(
    persona_id: Optional[str] = typer.Option(
        None, "--persona", "-p", help="Filter by persona ID"
    ),
    status: str = typer.Option("draft", "--status", "-s", help="draft or published"),
):
    """List content in the knowledge base."""
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base")
    kb = KnowledgeBase(kb_path)

    contents = kb.list_content(persona_id=persona_id, status=status)

    if not contents:
        console.print(f"[yellow]No {status} content found.[/yellow]")
        return

    table = Table(title=f"{status.capitalize()} Content")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Pillar", style="yellow")
    table.add_column("Score", style="magenta")

    for content in contents[:20]:  # Show latest 20
        score_str = (
            f"{content.review_score:.0f}" if content.review_score else "N/A"
        )
        table.add_row(
            content.id,
            content.title[:50] + "..." if len(content.title) > 50 else content.title,
            content.pillar,
            score_str,
        )

    console.print(table)


@app.command()
def stats():
    """Show knowledge base statistics."""
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base")
    kb = KnowledgeBase(kb_path)

    stats = kb.get_storage_stats()

    table = Table(title="Knowledge Base Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")

    table.add_row("Total Personas", str(stats["total_personas"]))
    table.add_row("Draft Content", str(stats["draft_contents"]))
    table.add_row("Published Content", str(stats["published_contents"]))
    table.add_row("Total Experiments", str(stats["total_experiments"]))

    console.print(table)


@app.command()
def version():
    """Show AvatarFactory version."""
    console.print("[bold cyan]AvatarFactory[/bold cyan] v0.1.0 (MVP)")
    console.print("A Persona Factory for social platforms")

    # Show current LLM configuration
    provider_type = os.getenv("AVATARFACTORY_LLM_PROVIDER", "anthropic")
    model = os.getenv("AVATARFACTORY_MODEL", "default")
    console.print(f"\nLLM Provider: {provider_type}")
    console.print(f"Model: {model}")


# =============================================================================
# Platform Connector Commands
# =============================================================================

@app.command()
def connect(
    platform: str = typer.Argument(..., help="Platform to connect to (bluesky, twitter)"),
):
    """
    Connect to a social platform.

    Example:
        avatarfactory connect bluesky
        avatarfactory connect twitter
    """
    console.print(Panel.fit(f"Connecting to {platform}...", border_style="cyan"))

    # Build config from environment
    config = ConnectorConfig()

    if platform.lower() == "bluesky":
        config.username = os.getenv("BLUESKY_USERNAME")
        config.password = os.getenv("BLUESKY_PASSWORD")
        if not config.username or not config.password:
            console.print("[red]Error: BLUESKY_USERNAME and BLUESKY_PASSWORD not set in .env[/red]")
            console.print("Set these environment variables:")
            console.print("  BLUESKY_USERNAME=your.handle.bsky.social")
            console.print("  BLUESKY_PASSWORD=your-app-password")
            raise typer.Exit(1)

    elif platform.lower() == "twitter":
        config.api_key = os.getenv("TWITTER_API_KEY")
        config.api_secret = os.getenv("TWITTER_API_SECRET")
        config.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        if not config.access_token and not (config.api_key and config.api_secret):
            console.print("[red]Error: Twitter API credentials not set in .env[/red]")
            console.print("Set these environment variables:")
            console.print("  TWITTER_ACCESS_TOKEN=your-bearer-token")
            console.print("  or")
            console.print("  TWITTER_API_KEY=your-api-key")
            console.print("  TWITTER_API_SECRET=your-api-secret")
            raise typer.Exit(1)
    else:
        console.print(f"[red]Error: Unknown platform '{platform}'[/red]")
        console.print("Available platforms: bluesky, twitter")
        raise typer.Exit(1)

    try:
        connector = get_connector(platform, config)

        async def test_connection():
            await connector.connect()
            return await connector.verify_credentials()

        with console.status(f"[bold cyan]Connecting to {platform}...", spinner="dots"):
            is_valid = asyncio.run(test_connection())

        if is_valid:
            console.print(f"[green]Successfully connected to {platform}![/green]")
        else:
            console.print(f"[yellow]Connected but credentials may have limited permissions[/yellow]")

    except Exception as e:
        console.print(f"[red]Failed to connect: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def fetch(
    platform: str = typer.Argument(..., help="Platform to fetch from (bluesky, twitter)"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of posts to fetch"),
):
    """
    Fetch trending content from a platform.

    Example:
        avatarfactory fetch bluesky --query "AI tools"
        avatarfactory fetch twitter -q "productivity" -n 20
    """
    console.print(Panel.fit(f"Fetching from {platform}...", border_style="cyan"))

    # Build config from environment
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

        async def do_fetch():
            await connector.connect()
            return await connector.fetch_trending(query=query, limit=limit)

        with console.status(f"[bold cyan]Fetching content...", spinner="dots"):
            result = asyncio.run(do_fetch())

        if not result.success:
            console.print(f"[red]Error: {result.error}[/red]")
            raise typer.Exit(1)

        # Display results
        table = Table(title=f"Trending on {platform}" + (f" for '{query}'" if query else ""))
        table.add_column("Author", style="cyan")
        table.add_column("Content", style="white", max_width=60)
        table.add_column("Likes", style="green")
        table.add_column("Comments", style="yellow")

        for post in result.data:
            body = post.get("body", "")
            preview = body[:100] + "..." if len(body) > 100 else body
            # Replace newlines for table display
            preview = preview.replace("\n", " ")

            table.add_row(
                f"@{post.get('author', 'unknown')}",
                preview,
                str(post.get("likes", 0)),
                str(post.get("comments", 0)),
            )

        console.print(table)
        console.print(f"\n[dim]Fetched {len(result.data)} posts[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def publish(
    platform: str = typer.Argument(..., help="Platform to publish to (bluesky, twitter)"),
    content: str = typer.Argument(..., help="Content to publish"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated hashtags"),
):
    """
    Publish content to a platform.

    Example:
        avatarfactory publish bluesky "Hello world!"
        avatarfactory publish twitter "Check this out" --tags "ai,productivity"
    """
    console.print(Panel.fit(f"Publishing to {platform}...", border_style="cyan"))

    # Build config from environment
    config = ConnectorConfig()

    if platform.lower() == "bluesky":
        config.username = os.getenv("BLUESKY_USERNAME")
        config.password = os.getenv("BLUESKY_PASSWORD")
    elif platform.lower() == "twitter":
        config.api_key = os.getenv("TWITTER_API_KEY")
        config.api_secret = os.getenv("TWITTER_API_SECRET")
        config.access_token = os.getenv("TWITTER_ACCESS_TOKEN")

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    try:
        connector = get_connector(platform, config)

        async def do_publish():
            await connector.connect()
            return await connector.publish(content=content, tags=tag_list)

        with console.status(f"[bold cyan]Publishing...", spinner="dots"):
            result = asyncio.run(do_publish())

        if result.success:
            console.print(f"[green]Published successfully![/green]")
            if result.post_url:
                console.print(f"URL: {result.post_url}")
            console.print(f"Post ID: {result.post_id}")
        else:
            console.print(f"[red]Failed to publish: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
