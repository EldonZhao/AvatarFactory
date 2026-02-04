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
from avatarfactory.agents.discovery import DiscoveryAgent
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
def show_content(
    content_id: str = typer.Argument(..., help="Content ID to show"),
):
    """
    Show content details with social platform preview.

    Example:
        avatarfactory show-content content_178b3925
    """
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base")
    kb = KnowledgeBase(kb_path)

    content = kb.load_content(content_id)

    if not content:
        console.print(f"[red]Content not found: {content_id}[/red]")
        raise typer.Exit(1)

    # Get platform info for styling
    platform = content.platform.value if hasattr(content.platform, 'value') else str(content.platform)

    # Platform-specific styling
    platform_styles = {
        "xiaohongshu": {"emoji": "📕", "color": "red", "name": "小红书"},
        "bluesky": {"emoji": "🦋", "color": "blue", "name": "Bluesky"},
        "twitter": {"emoji": "𝕏", "color": "white", "name": "Twitter/X"},
        "zhihu": {"emoji": "知", "color": "blue", "name": "知乎"},
        "douyin": {"emoji": "🎵", "color": "magenta", "name": "抖音"},
    }
    style = platform_styles.get(platform, {"emoji": "📱", "color": "cyan", "name": platform})

    # Header with platform info
    console.print()
    console.print(f"[bold {style['color']}]{style['emoji']} {style['name']} Preview[/bold {style['color']}]")
    console.print("─" * 60)

    # Title (platform-native style)
    console.print(f"\n[bold]{content.title}[/bold]\n")

    # Body content
    console.print(content.body)

    # Tags/Hashtags
    if content.tags:
        console.print()
        tags_str = " ".join(f"[{style['color']}]#{tag}[/{style['color']}]" for tag in content.tags)
        console.print(tags_str)

    # Image prompts section
    if content.image_prompts:
        console.print("\n" + "─" * 60)
        console.print(f"[bold yellow]🖼️ Recommended Images ({len(content.image_prompts)})[/bold yellow]")
        for i, prompt in enumerate(content.image_prompts, 1):
            console.print(f"\n[dim]Image {i}:[/dim]")
            console.print(f"  {prompt}")

    # Image suggestions from metadata
    if content.metadata.get("image_suggestions"):
        console.print("\n[dim]Image Ideas:[/dim]")
        for suggestion in content.metadata["image_suggestions"]:
            console.print(f"  • {suggestion}")

    # Metadata footer
    console.print("\n" + "─" * 60)
    console.print(f"[dim]Content ID: {content.id}[/dim]")
    console.print(f"[dim]Persona: {content.persona_id}[/dim]")
    console.print(f"[dim]Pillar: {content.pillar}[/dim]")
    console.print(f"[dim]Created: {content.created_at.strftime('%Y-%m-%d %H:%M')}[/dim]")

    if content.review_score:
        score_color = "green" if content.review_score >= 80 else "yellow" if content.review_score >= 60 else "red"
        console.print(f"[dim]Review Score: [{score_color}]{content.review_score:.0f}/100[/{score_color}][/dim]")

    if content.review_issues:
        console.print(f"\n[yellow]Review Notes:[/yellow]")
        for issue in content.review_issues[:3]:
            console.print(f"  • {issue}")

    console.print()


@app.command()
def publish_draft(
    content_id: str = typer.Argument(..., help="Content ID to publish"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Override platform (bluesky, twitter)"),
    images: Optional[str] = typer.Option(None, "--images", "-i", help="Comma-separated image paths"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    force_single: bool = typer.Option(False, "--single", "-s", help="Force single post (truncate instead of thread)"),
):
    """
    Publish a draft content to social platform.

    Long content will be automatically split into a thread for platforms
    with character limits (Bluesky: 300, Twitter: 280).

    Example:
        avatarfactory publish-draft content_178b3925
        avatarfactory publish-draft content_178b3925 --platform bluesky
        avatarfactory publish-draft content_178b3925 -i "img1.jpg,img2.jpg"
        avatarfactory publish-draft content_178b3925 --single  # Force truncate
    """
    from avatarfactory.connectors.adapters import get_adapter, get_platform_limits

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base")
    kb = KnowledgeBase(kb_path)

    content = kb.load_content(content_id)

    if not content:
        console.print(f"[red]Content not found: {content_id}[/red]")
        raise typer.Exit(1)

    # Determine platform
    target_platform = platform or (content.platform.value if hasattr(content.platform, 'value') else str(content.platform))

    # For now, only bluesky is fully implemented
    if target_platform not in ["bluesky", "twitter"]:
        console.print(f"[yellow]Note: Platform '{target_platform}' connector not fully implemented.[/yellow]")
        console.print(f"[yellow]Using bluesky for publishing.[/yellow]")
        target_platform = "bluesky"

    # Parse images
    image_list = [img.strip() for img in images.split(",")] if images else []

    # Get platform limits and adapt content
    limits = get_platform_limits(target_platform)
    adapter = get_adapter(target_platform)
    adapted = adapter.adapt(content, images=image_list, force_single=force_single)

    # Show preview with adaptation info
    console.print(Panel.fit(
        f"[bold]Publishing to {target_platform}[/bold]\n\n"
        f"[cyan]Title:[/cyan] {content.title}\n"
        f"[cyan]Original length:[/cyan] {adapted.original_length} chars\n"
        f"[cyan]Platform limit:[/cyan] {limits.max_text_length} chars/post\n"
        f"[cyan]Adapted:[/cyan] {'Thread with ' + str(len(adapted.parts)) + ' posts' if adapted.is_thread else 'Single post'}"
        + (f" [yellow](truncated)[/yellow]" if adapted.truncated else "") + "\n"
        f"[cyan]Tags:[/cyan] {', '.join(adapted.tags) if adapted.tags else 'None'}\n"
        f"[cyan]Images:[/cyan] {len(image_list)} provided",
        title=f"Content: {content_id}",
        border_style="cyan",
    ))

    # Show adapted content preview
    if adapted.is_thread:
        console.print(f"\n[bold]Thread Preview ({len(adapted.parts)} posts):[/bold]")
        for i, part in enumerate(adapted.parts, 1):
            console.print(f"\n[cyan]━━━ Post {i}/{len(adapted.parts)} ━━━[/cyan]")
            # Show first 150 chars of each part
            preview = part[:150] + "..." if len(part) > 150 else part
            console.print(f"[dim]{preview}[/dim]")
            console.print(f"[dim]({len(part)} chars)[/dim]")
    else:
        console.print(f"\n[bold]Post Preview:[/bold]")
        preview = adapted.parts[0][:300] + "..." if len(adapted.parts[0]) > 300 else adapted.parts[0]
        console.print(f"[dim]{preview}[/dim]")
        console.print(f"[dim]({len(adapted.parts[0])} chars)[/dim]")

    console.print()

    # Confirm
    if not confirm:
        if adapted.is_thread:
            proceed = typer.confirm(f"Publish as {len(adapted.parts)}-post thread?")
        else:
            proceed = typer.confirm("Publish this content?")
        if not proceed:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    # Build connector config
    config = ConnectorConfig()

    if target_platform == "bluesky":
        config.username = os.getenv("BLUESKY_USERNAME")
        config.password = os.getenv("BLUESKY_PASSWORD")
        if not config.username or not config.password:
            console.print("[red]Error: BLUESKY_USERNAME and BLUESKY_PASSWORD not set[/red]")
            raise typer.Exit(1)
    elif target_platform == "twitter":
        config.api_key = os.getenv("TWITTER_API_KEY")
        config.api_secret = os.getenv("TWITTER_API_SECRET")
        config.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    elif target_platform in ("xiaohongshu", "xhs"):
        xhs_cookie = os.getenv("XIAOHONGSHU_COOKIE")
        if not xhs_cookie:
            console.print("[red]Error: XIAOHONGSHU_COOKIE not set[/red]")
            console.print("Get your cookie from browser DevTools after logging in to xiaohongshu.com")
            raise typer.Exit(1)
        config.extra = {
            "cookie": xhs_cookie,
            "user_id": os.getenv("XIAOHONGSHU_USER_ID"),
        }

    try:
        connector = get_connector(target_platform, config)

        async def do_publish():
            await connector.connect()

            # Use publish_thread for threads if connector supports it
            if adapted.is_thread and hasattr(connector, 'publish_thread'):
                # Use the dedicated thread publishing method
                results = await connector.publish_thread(
                    posts=adapted.parts,
                    images=image_list if image_list else None,
                )
                return results
            else:
                # Fallback: publish each part separately (no reply chain)
                results = []
                for i, part in enumerate(adapted.parts):
                    part_images = image_list if i == 0 else None
                    result = await connector.publish(
                        content=part,
                        images=part_images,
                    )
                    results.append(result)
                    if not result.success:
                        return results
                return results

        with console.status("[bold cyan]Publishing...", spinner="dots"):
            results = asyncio.run(do_publish())

        # Check results
        all_success = all(r.success for r in results)

        if all_success:
            console.print(f"\n[green]✅ Published successfully![/green]")
            if adapted.is_thread:
                console.print(f"[bold]Published {len(results)} posts as a thread[/bold]")
            for i, result in enumerate(results):
                if result.post_url:
                    if len(results) > 1:
                        console.print(f"[dim]Post {i+1}:[/dim] {result.post_url}")
                    else:
                        console.print(f"[bold]URL:[/bold] {result.post_url}")

            # Update content status in KB (mark as published)
            kb.save_content(content, status="published")
            console.print(f"\n[dim]Content status updated to 'published'[/dim]")
        else:
            failed = [r for r in results if not r.success]
            console.print(f"[red]❌ Failed to publish: {failed[0].error}[/red]")
            if len(results) > 1:
                success_count = sum(1 for r in results if r.success)
                console.print(f"[yellow]Partial publish: {success_count}/{len(results)} posts succeeded[/yellow]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


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

    elif platform.lower() in ("xiaohongshu", "xhs"):
        xhs_cookie = os.getenv("XIAOHONGSHU_COOKIE")
        if not xhs_cookie:
            console.print("[red]Error: XIAOHONGSHU_COOKIE not set in .env[/red]")
            console.print("Get your cookie from browser DevTools after logging in to xiaohongshu.com")
            raise typer.Exit(1)
        config.extra = {
            "cookie": xhs_cookie,
            "user_id": os.getenv("XIAOHONGSHU_USER_ID"),
        }

    else:
        console.print(f"[red]Error: Unknown platform '{platform}'[/red]")
        console.print("Available platforms: bluesky, twitter, xiaohongshu")
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
    elif platform.lower() in ("xiaohongshu", "xhs"):
        config.extra = {
            "cookie": os.getenv("XIAOHONGSHU_COOKIE"),
            "user_id": os.getenv("XIAOHONGSHU_USER_ID"),
        }

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
    elif platform.lower() in ("xiaohongshu", "xhs"):
        config.extra = {
            "cookie": os.getenv("XIAOHONGSHU_COOKIE"),
            "user_id": os.getenv("XIAOHONGSHU_USER_ID"),
        }

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


# =============================================================================
# Discovery Commands
# =============================================================================

def get_discovery_agent() -> DiscoveryAgent:
    """Initialize discovery agent with LLM provider from environment."""
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base")
    kb = KnowledgeBase(kb_path)

    try:
        provider = LLMProviderFactory.from_env()
    except Exception as e:
        console.print(f"[red]Error initializing LLM provider: {e}[/red]")
        raise typer.Exit(1)

    return DiscoveryAgent(knowledge_base=kb, llm_provider=provider)


@app.command()
def discover(
    platform: str = typer.Argument("bluesky", help="Platform to discover from (bluesky, twitter)"),
    persona_id: Optional[str] = typer.Option(None, "--persona", "-p", help="Persona ID for targeted discovery"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query (uses persona keywords if not provided)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of posts to analyze"),
):
    """
    Discover trending content and analyze patterns.

    This command fetches trending content, analyzes patterns, and generates
    content ideas based on your persona.

    Example:
        avatarfactory discover bluesky --persona persona_xxx
        avatarfactory discover twitter -q "AI productivity" -n 30
    """
    console.print(Panel.fit(
        f"[bold cyan]Discovery Agent[/bold cyan]\n"
        f"Platform: {platform}\n"
        f"Persona: {persona_id or 'None (general discovery)'}\n"
        f"Query: {query or 'Auto (from persona)'}",
        border_style="cyan",
    ))

    agent = get_discovery_agent()

    async def run_discovery():
        if persona_id:
            return await agent.discover_and_analyze(
                persona_id=persona_id,
                platform=platform,
                query=query,
                limit=limit,
            )
        else:
            # Just fetch trending without full analysis
            from avatarfactory.models.schemas import AgentMessage, TaskType
            return await agent._discover_trending({
                "platform": platform,
                "query": query,
                "limit": limit,
            })

    with console.status("[bold cyan]Discovering and analyzing content...", spinner="dots"):
        result = asyncio.run(run_discovery())

    if result.get("status") != "success":
        console.print(f"[red]Error: {result.get('message')}[/red]")
        raise typer.Exit(1)

    data = result.get("data", {})

    # Display trending content summary
    if "contents" in data:
        console.print(f"\n[green]Found {len(data['contents'])} trending posts[/green]")

        table = Table(title="Top Trending Content")
        table.add_column("Author", style="cyan")
        table.add_column("Content", style="white", max_width=50)
        table.add_column("Engagement", style="green")

        for post in data["contents"][:10]:
            body = post.get("body", "")[:80].replace("\n", " ")
            engagement = f"❤️ {post.get('likes', 0)} 💬 {post.get('comments', 0)}"
            table.add_row(f"@{post.get('author', '?')}", body, engagement)

        console.print(table)

    # Display pattern analysis
    if "pattern_analysis" in data and data["pattern_analysis"]:
        analysis = data["pattern_analysis"]
        console.print("\n[bold]Pattern Analysis[/bold]")

        if analysis.get("trending_topics"):
            console.print(f"[yellow]Trending Topics:[/yellow] {', '.join(analysis['trending_topics'][:5])}")

        if analysis.get("key_insights"):
            console.print("\n[yellow]Key Insights:[/yellow]")
            for insight in analysis["key_insights"][:5]:
                console.print(f"  • {insight}")

    # Display content ideas
    if "ideas" in data and data["ideas"]:
        console.print("\n[bold]Generated Content Ideas[/bold]")

        for i, idea in enumerate(data["ideas"], 1):
            console.print(f"\n[cyan]{i}. {idea.get('topic', 'Untitled')}[/cyan]")
            console.print(f"   [dim]Angle:[/dim] {idea.get('angle', 'N/A')}")
            if idea.get("hook"):
                console.print(f"   [dim]Hook:[/dim] \"{idea['hook']}\"")
            console.print(f"   [dim]Pillar:[/dim] {idea.get('suggested_pillar', 'N/A')} | [dim]Engagement:[/dim] {idea.get('estimated_engagement', 'medium')}")

    # Display persona suggestions
    if "persona_suggestions" in data and data["persona_suggestions"]:
        console.print("\n[bold]Persona Optimization Suggestions[/bold]")
        for suggestion in data["persona_suggestions"]:
            console.print(f"  → {suggestion}")

    console.print(f"\n[dim]{result.get('message', 'Discovery complete.')}[/dim]")


@app.command()
def inspire(
    persona_id: str = typer.Argument(..., help="Persona ID to get inspiration for"),
    platform: str = typer.Option("bluesky", "--platform", "-t", help="Platform to analyze"),
    ideas: int = typer.Option(5, "--ideas", "-n", help="Number of ideas to generate"),
):
    """
    Get content inspiration based on your persona and market trends.

    This is a shortcut for the full discovery workflow focused on idea generation.

    Example:
        avatarfactory inspire persona_xxx
        avatarfactory inspire persona_xxx --platform twitter --ideas 10
    """
    console.print(Panel.fit(
        f"[bold cyan]Getting Inspiration[/bold cyan]\n"
        f"Persona: {persona_id}\n"
        f"Platform: {platform}",
        border_style="cyan",
    ))

    agent = get_discovery_agent()

    async def run_inspiration():
        return await agent.discover_and_analyze(
            persona_id=persona_id,
            platform=platform,
            limit=30,  # Fetch more for better analysis
        )

    with console.status("[bold cyan]Analyzing trends and generating ideas...", spinner="dots"):
        result = asyncio.run(run_inspiration())

    if result.get("status") != "success":
        console.print(f"[red]Error: {result.get('message')}[/red]")
        raise typer.Exit(1)

    data = result.get("data", {})

    console.print(f"\n[green]Analyzed {data.get('trending_count', 0)} trending posts[/green]")

    # Focus on ideas
    if "ideas" in data and data["ideas"]:
        console.print("\n[bold cyan]Content Ideas for You[/bold cyan]")

        for i, idea in enumerate(data["ideas"][:ideas], 1):
            console.print(f"\n{'─' * 60}")
            console.print(f"[bold]{i}. {idea.get('topic', 'Untitled')}[/bold]")
            console.print(f"[yellow]Angle:[/yellow] {idea.get('angle', 'N/A')}")
            if idea.get("hook"):
                console.print(f"[yellow]Hook:[/yellow] \"{idea['hook']}\"")
            console.print(f"[dim]Type: {idea.get('content_type', 'post')} | Pillar: {idea.get('suggested_pillar', 'N/A')}[/dim]")
            if idea.get("reasoning"):
                console.print(f"[dim]Why: {idea['reasoning']}[/dim]")

    # Show suggestions
    if "persona_suggestions" in data and data["persona_suggestions"]:
        console.print(f"\n{'─' * 60}")
        console.print("[bold]Tips to Improve Your Persona[/bold]")
        for suggestion in data["persona_suggestions"]:
            console.print(f"  💡 {suggestion}")


# =============================================================================
# Scheduler Commands
# =============================================================================

@app.command()
def daemon(
    action: str = typer.Argument(..., help="Action: start, stop, status"),
):
    """
    Manage the background scheduler daemon.

    Example:
        avatarfactory daemon start
        avatarfactory daemon status
        avatarfactory daemon stop
    """
    from avatarfactory.scheduler import Scheduler, SchedulerConfig

    config = SchedulerConfig(
        data_dir=os.path.join(
            os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base"),
            "scheduler"
        )
    )
    scheduler = Scheduler(config)

    if action == "start":
        console.print(Panel.fit(
            "[bold cyan]Starting AvatarFactory Daemon[/bold cyan]\n"
            "Press Ctrl+C to stop",
            border_style="cyan",
        ))

        # Show scheduled tasks
        tasks = scheduler.list_tasks()
        if tasks:
            console.print(f"\n[green]Scheduled Tasks ({len(tasks)}):[/green]")
            for task in tasks:
                status = "✓" if task.enabled else "○"
                console.print(f"  {status} {task.name} ({task.schedule})")
        else:
            console.print("\n[yellow]No scheduled tasks. Use 'avatarfactory schedule add' to create tasks.[/yellow]")

        queue = scheduler.get_publish_queue(status="pending")
        if queue:
            console.print(f"\n[green]Publish Queue: {len(queue)} pending[/green]")

        console.print("\n[dim]Daemon running...[/dim]\n")

        try:
            scheduler.start(blocking=True)
        except KeyboardInterrupt:
            console.print("\n[cyan]Daemon stopped.[/cyan]")

    elif action == "status":
        status = scheduler.get_status()

        table = Table(title="Scheduler Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Running", "Yes" if status["running"] else "No")
        table.add_row("Total Tasks", str(status["tasks_count"]))
        table.add_row("Enabled Tasks", str(status["enabled_tasks"]))
        table.add_row("Queue Pending", str(status["queue_pending"]))
        table.add_row("Queue Published", str(status["queue_published"]))

        console.print(table)

        # Show tasks
        tasks = scheduler.list_tasks()
        if tasks:
            console.print("\n[bold]Scheduled Tasks:[/bold]")
            for task in tasks:
                status_icon = "✓" if task.enabled else "○"
                last_run = task.last_run.strftime("%Y-%m-%d %H:%M") if task.last_run else "Never"
                last_status = task.last_status or "N/A"
                console.print(f"  {status_icon} [cyan]{task.name}[/cyan] ({task.schedule})")
                console.print(f"      Last: {last_run} | Status: {last_status} | Runs: {task.run_count}")

    elif action == "stop":
        console.print("[yellow]Note: Daemon runs in foreground. Use Ctrl+C to stop.[/yellow]")

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Available actions: start, status, stop")
        raise typer.Exit(1)


@app.command()
def schedule(
    action: str = typer.Argument(..., help="Action: add, remove, list, enable, disable"),
    task_type: Optional[str] = typer.Option(None, "--type", "-t", help="Task type: discovery, content, publish, report"),
    persona_id: Optional[str] = typer.Option(None, "--persona", "-p", help="Persona ID"),
    platform: Optional[str] = typer.Option(None, "--platform", help="Platform (bluesky, twitter)"),
    cron: Optional[str] = typer.Option(None, "--cron", "-c", help="Cron schedule (e.g., '0 9 * * *')"),
    task_id: Optional[str] = typer.Option(None, "--id", help="Task ID (for remove/enable/disable)"),
):
    """
    Manage scheduled tasks.

    Example:
        avatarfactory schedule list
        avatarfactory schedule add --type discovery --persona persona_xxx --cron "0 9 * * *"
        avatarfactory schedule remove --id task_xxx
        avatarfactory schedule enable --id task_xxx
    """
    from avatarfactory.scheduler import Scheduler, SchedulerConfig
    from avatarfactory.scheduler.engine import ScheduledTask
    import uuid

    config = SchedulerConfig(
        data_dir=os.path.join(
            os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base"),
            "scheduler"
        )
    )
    scheduler = Scheduler(config)

    if action == "list":
        tasks = scheduler.list_tasks()

        if not tasks:
            console.print("[yellow]No scheduled tasks.[/yellow]")
            console.print("Create one with: avatarfactory schedule add --type discovery --persona <id> --cron '0 9 * * *'")
            return

        table = Table(title="Scheduled Tasks")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Schedule", style="green")
        table.add_column("Enabled", style="white")
        table.add_column("Last Run", style="dim")

        for task in tasks:
            last_run = task.last_run.strftime("%m-%d %H:%M") if task.last_run else "-"
            table.add_row(
                task.id,
                task.name,
                task.task_type,
                task.schedule,
                "✓" if task.enabled else "○",
                last_run,
            )

        console.print(table)

    elif action == "add":
        if not task_type:
            console.print("[red]--type required (discovery, content, publish, report)[/red]")
            raise typer.Exit(1)

        if task_type in ("discovery", "content", "report") and not persona_id:
            console.print(f"[red]--persona required for {task_type} tasks[/red]")
            raise typer.Exit(1)

        schedule_cron = cron or {
            "discovery": "0 9 * * *",
            "content": "0 10 * * *",
            "publish": "0 12 * * *",
            "report": "0 18 * * 5",
        }.get(task_type, "0 9 * * *")

        task = ScheduledTask(
            id=f"task_{uuid.uuid4().hex[:8]}",
            name=f"{task_type.capitalize()} - {persona_id or 'all'}",
            task_type=task_type,
            schedule=schedule_cron,
            persona_id=persona_id,
            platform=platform or "bluesky",
        )

        scheduler.add_task(task)
        console.print(f"[green]Created task: {task.name}[/green]")
        console.print(f"  ID: {task.id}")
        console.print(f"  Schedule: {task.schedule}")

    elif action == "remove":
        if not task_id:
            console.print("[red]--id required[/red]")
            raise typer.Exit(1)

        if scheduler.remove_task(task_id):
            console.print(f"[green]Removed task: {task_id}[/green]")
        else:
            console.print(f"[red]Task not found: {task_id}[/red]")

    elif action == "enable":
        if not task_id:
            console.print("[red]--id required[/red]")
            raise typer.Exit(1)

        if scheduler.enable_task(task_id):
            console.print(f"[green]Enabled task: {task_id}[/green]")
        else:
            console.print(f"[red]Task not found: {task_id}[/red]")

    elif action == "disable":
        if not task_id:
            console.print("[red]--id required[/red]")
            raise typer.Exit(1)

        if scheduler.disable_task(task_id):
            console.print(f"[yellow]Disabled task: {task_id}[/yellow]")
        else:
            console.print(f"[red]Task not found: {task_id}[/red]")

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Available: add, remove, list, enable, disable")
        raise typer.Exit(1)


@app.command()
def queue(
    action: str = typer.Argument(..., help="Action: add, remove, list"),
    content_id: Optional[str] = typer.Option(None, "--content", "-c", help="Content ID to queue"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Target platform"),
    schedule_time: Optional[str] = typer.Option(None, "--time", "-t", help="Schedule time (ISO format or 'now')"),
    item_id: Optional[str] = typer.Option(None, "--id", help="Queue item ID (for remove)"),
):
    """
    Manage the publish queue.

    Example:
        avatarfactory queue list
        avatarfactory queue add --content content_xxx --platform bluesky
        avatarfactory queue add --content content_xxx --platform bluesky --time "2024-01-15T10:00:00"
        avatarfactory queue remove --id pub_xxx
    """
    from avatarfactory.scheduler import Scheduler, SchedulerConfig
    from datetime import datetime

    config = SchedulerConfig(
        data_dir=os.path.join(
            os.getenv("AVATARFACTORY_KB_PATH", "./knowledge_base"),
            "scheduler"
        )
    )
    scheduler = Scheduler(config)

    if action == "list":
        queue_items = scheduler.get_publish_queue()

        if not queue_items:
            console.print("[yellow]Publish queue is empty.[/yellow]")
            return

        table = Table(title="Publish Queue")
        table.add_column("ID", style="dim")
        table.add_column("Content", style="cyan")
        table.add_column("Platform", style="yellow")
        table.add_column("Scheduled", style="green")
        table.add_column("Status", style="white")

        for item in queue_items:
            scheduled = item.scheduled_time.strftime("%m-%d %H:%M") if item.scheduled_time else "ASAP"
            status_style = {
                "pending": "yellow",
                "published": "green",
                "failed": "red",
            }.get(item.status, "white")

            table.add_row(
                item.id,
                item.content_id,
                item.platform,
                scheduled,
                f"[{status_style}]{item.status}[/{status_style}]",
            )

        console.print(table)

    elif action == "add":
        if not content_id:
            console.print("[red]--content required[/red]")
            raise typer.Exit(1)

        if not platform:
            console.print("[red]--platform required (bluesky, twitter)[/red]")
            raise typer.Exit(1)

        scheduled_dt = None
        if schedule_time and schedule_time != "now":
            try:
                scheduled_dt = datetime.fromisoformat(schedule_time)
            except ValueError:
                console.print(f"[red]Invalid time format: {schedule_time}[/red]")
                console.print("Use ISO format: 2024-01-15T10:00:00")
                raise typer.Exit(1)

        item = scheduler.queue_publish(
            content_id=content_id,
            platform=platform,
            scheduled_time=scheduled_dt,
        )

        console.print(f"[green]Added to publish queue[/green]")
        console.print(f"  ID: {item.id}")
        console.print(f"  Scheduled: {scheduled_dt or 'ASAP'}")

    elif action == "remove":
        if not item_id:
            console.print("[red]--id required[/red]")
            raise typer.Exit(1)

        if scheduler.remove_from_queue(item_id):
            console.print(f"[green]Removed from queue: {item_id}[/green]")
        else:
            console.print(f"[red]Item not found: {item_id}[/red]")

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Available: add, remove, list")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
