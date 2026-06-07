"""
AvatarFactory CLI - Command-line interface for interacting with AvatarFactory.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from avatarfactory.agents.orchestrator import OrchestratorAgent
from avatarfactory.agents.topic import TopicAgent
from avatarfactory.connectors import ConnectorConfig, get_connector
from avatarfactory.connectors.xiaohongshu import CookieExpiredError
from avatarfactory.core.knowledges_db import get_knowledge_base
from avatarfactory.core.llm_provider import LLMProviderFactory
from avatarfactory.models.schemas import AgentMessage, TaskType

# Load .env file from current directory or project root
load_dotenv()

# Fix Windows console encoding for Unicode/Chinese characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(
    name="avatarfactory",
    help="AvatarFactory - A Persona Factory for social platforms",
    add_completion=False,
)

console = Console(force_terminal=True)


def get_orchestrator() -> OrchestratorAgent:
    """Initialize orchestrator agent with LLM provider from environment"""
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")

    try:
        provider = LLMProviderFactory.from_env()
        if not provider.validate_config():
            provider_type = os.getenv("AVATARFACTORY_LLM_PROVIDER", "anthropic")
            console.print(f"[red]Error: {provider_type} provider not configured correctly[/red]")
            console.print("Please check your .env file and set the required API keys.")
            raise typer.Exit(1)
    except ImportError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error initializing LLM provider: {e}[/red]")
        raise typer.Exit(1)

    kb = get_knowledge_base(kb_path)

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
                    console.print(f"\n[dim]Persona ID: {persona_data.get('id')}[/dim]")

                if "content" in data:
                    content_data = data["content"]
                    console.print(f"\n[dim]Content ID: {content_data.get('id')}[/dim]")

        except KeyboardInterrupt:
            console.print("\n\n[cyan]Goodbye![/cyan]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


@app.command()
def create_persona(
    description: str = typer.Argument(..., help="Describe your desired persona"),
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
            payload={"user_input": f"Create a persona: {description}"},
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
        console.print("\n[bold]Persona Details:[/bold]")
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
        console.print("\n[bold]Content Preview:[/bold]")
        console.print(f"  Title: {content.get('title')}")
        console.print(f"  Platform: {content.get('platform')}")
        console.print(f"  Content ID: {content.get('id')}")

        # Show body preview
        body = content.get("body", "")
        preview = body[:200] + "..." if len(body) > 200 else body
        console.print(f"\n[dim]{preview}[/dim]")


@app.command()
def list_personas():
    """List all personas in the knowledges."""
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = get_knowledge_base(kb_path)

    personas = kb.list_personas()

    if not personas:
        console.print(
            "[yellow]No personas found. Create one with 'avatarfactory create-persona'[/yellow]"
        )
        return

    table = Table(title="Personas")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Tagline", style="yellow")

    for persona_id in personas:
        persona = kb.load_persona(persona_id)
        if persona:
            table.add_row(
                persona_id,
                persona.identity.name,
                (
                    persona.identity.tagline[:50] + "..."
                    if len(persona.identity.tagline) > 50
                    else persona.identity.tagline
                ),
            )

    console.print(table)


@app.command()
def delete_persona(
    persona_id: str = typer.Argument(..., help="Persona ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    keep_content: bool = typer.Option(False, "--keep-content", help="Keep content files"),
):
    """
    Delete a persona and all associated data.

    This will remove:
    - Persona configuration and versions
    - All content created by this persona (unless --keep-content)
    - Discovery data
    - Scheduled tasks for this persona

    Example:
        avatarfactory delete-persona persona_abc123
        avatarfactory delete-persona persona_abc123 --force
        avatarfactory delete-persona persona_abc123 --keep-content
    """
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = get_knowledge_base(kb_path)

    # Check if persona exists
    persona = kb.load_persona(persona_id)
    if not persona:
        console.print(f"[red]Error: Persona {persona_id} not found[/red]")
        raise typer.Exit(1)

    # Show persona info
    console.print("\n[bold]Persona to delete:[/bold]")
    console.print(f"  ID: {persona_id}")
    console.print(f"  Name: {persona.identity.name}")
    console.print(f"  Tagline: {persona.identity.tagline}")

    # Count associated content
    draft_count = len(kb.list_content(persona_id, status="draft"))
    published_count = len(kb.list_content(persona_id, status="published"))
    console.print("\n[bold]Associated data:[/bold]")
    console.print(f"  Drafts: {draft_count}")
    console.print(f"  Published: {published_count}")

    # Confirm deletion
    if not force:
        console.print("\n[yellow]⚠️  This action cannot be undone![/yellow]")
        confirm = typer.confirm("Are you sure you want to delete this persona?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    with console.status("[bold red]Deleting persona...", spinner="dots"):
        # 1. Delete scheduled tasks
        from avatarfactory.scheduler.engine import Scheduler, SchedulerConfig

        scheduler = Scheduler(SchedulerConfig())
        tasks_removed = scheduler.remove_tasks_for_persona(persona_id)

        # 2. Delete persona and content
        result = kb.delete_persona(persona_id, delete_content=not keep_content)

    # Show results
    console.print("\n[bold]Deletion complete:[/bold]")
    console.print(f"  ✅ Persona deleted: {result['persona_deleted']}")
    console.print(f"  ✅ Content files deleted: {result['content_deleted']}")
    console.print(f"  ✅ Discovery data deleted: {result['discovery_deleted']}")
    console.print(f"  ✅ Scheduled tasks removed: {tasks_removed}")

    if result["errors"]:
        console.print("\n[yellow]Warnings:[/yellow]")
        for error in result["errors"]:
            console.print(f"  ⚠️  {error}")

    console.print(f"\n[green]✅ Persona {persona_id} has been deleted[/green]")


@app.command()
def list_content(
    persona_id: Optional[str] = typer.Option(None, "--persona", "-p", help="Filter by persona ID"),
    status: str = typer.Option("draft", "--status", "-s", help="draft or published"),
):
    """List content in the knowledges."""
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = get_knowledge_base(kb_path)

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
        score_str = f"{content.review_score:.0f}" if content.review_score else "N/A"
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
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = get_knowledge_base(kb_path)

    content = kb.load_content(content_id)

    if not content:
        console.print(f"[red]Content not found: {content_id}[/red]")
        raise typer.Exit(1)

    # Get platform info for styling
    platform = (
        content.platform.value if hasattr(content.platform, "value") else str(content.platform)
    )

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
    console.print(
        f"[bold {style['color']}]{style['emoji']} {style['name']} Preview[/bold {style['color']}]"
    )
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
        console.print(
            f"[bold yellow]🖼️ Recommended Images ({len(content.image_prompts)})[/bold yellow]"
        )
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
        score_color = (
            "green"
            if content.review_score >= 80
            else "yellow" if content.review_score >= 60 else "red"
        )
        console.print(
            f"[dim]Review Score: [{score_color}]{content.review_score:.0f}/100[/{score_color}][/dim]"
        )

    if content.review_issues:
        console.print("\n[yellow]Review Notes:[/yellow]")
        for issue in content.review_issues[:3]:
            console.print(f"  • {issue}")

    console.print()


@app.command()
def publish_draft(
    content_id: str = typer.Argument(..., help="Content ID to publish"),
    platform: Optional[str] = typer.Option(
        None, "--platform", "-p", help="Override platform (bluesky, twitter)"
    ),
    images: Optional[str] = typer.Option(
        None, "--images", "-i", help="Comma-separated image paths"
    ),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    force_single: bool = typer.Option(
        False, "--single", "-s", help="Force single post (truncate instead of thread)"
    ),
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

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = get_knowledge_base(kb_path)

    content = kb.load_content(content_id)

    if not content:
        console.print(f"[red]Content not found: {content_id}[/red]")
        raise typer.Exit(1)

    # Determine platform
    target_platform = platform or (
        content.platform.value if hasattr(content.platform, "value") else str(content.platform)
    )

    # Parse images
    image_list = [img.strip() for img in images.split(",")] if images else []

    # Get platform limits and adapt content
    limits = get_platform_limits(target_platform)
    adapter = get_adapter(target_platform)
    adapted = adapter.adapt(content, images=image_list, force_single=force_single)

    # Show preview with adaptation info
    console.print(
        Panel.fit(
            f"[bold]Publishing to {target_platform}[/bold]\n\n"
            f"[cyan]Title:[/cyan] {content.title}\n"
            f"[cyan]Original length:[/cyan] {adapted.original_length} chars\n"
            f"[cyan]Platform limit:[/cyan] {limits.max_text_length} chars/post\n"
            f"[cyan]Adapted:[/cyan] {'Thread with ' + str(len(adapted.parts)) + ' posts' if adapted.is_thread else 'Single post'}"
            + (" [yellow](truncated)[/yellow]" if adapted.truncated else "")
            + "\n"
            f"[cyan]Tags:[/cyan] {', '.join(adapted.tags) if adapted.tags else 'None'}\n"
            f"[cyan]Images:[/cyan] {len(image_list)} provided",
            title=f"Content: {content_id}",
            border_style="cyan",
        )
    )

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
        console.print("\n[bold]Post Preview:[/bold]")
        preview = (
            adapted.parts[0][:300] + "..." if len(adapted.parts[0]) > 300 else adapted.parts[0]
        )
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
        config.extra = {"access_token_secret": os.getenv("TWITTER_ACCESS_TOKEN_SECRET")}
    elif target_platform in ("xiaohongshu", "xhs"):
        xhs_cookie = os.getenv("XIAOHONGSHU_COOKIE")
        if not xhs_cookie:
            console.print("[red]Error: XIAOHONGSHU_COOKIE not set[/red]")
            console.print(
                "Get your cookie from browser DevTools after logging in to xiaohongshu.com"
            )
            raise typer.Exit(1)
        config.extra = {
            "cookie": xhs_cookie,
            "user_id": os.getenv("XIAOHONGSHU_USER_ID"),
            "b1": os.getenv("XIAOHONGSHU_B1"),
        }
    elif target_platform == "mastodon":
        mastodon_token = os.getenv("MASTODON_ACCESS_TOKEN")
        mastodon_instance = os.getenv("MASTODON_INSTANCE_URL")
        if not mastodon_token or not mastodon_instance:
            console.print(
                "[red]Error: MASTODON_ACCESS_TOKEN and MASTODON_INSTANCE_URL not set[/red]"
            )
            raise typer.Exit(1)
        config.access_token = mastodon_token
        config.extra = {"instance_url": mastodon_instance}
    elif target_platform == "instagram":
        instagram_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        instagram_account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
        if not instagram_token or not instagram_account_id:
            console.print(
                "[red]Error: INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID not set[/red]"
            )
            raise typer.Exit(1)
        config.access_token = instagram_token
        config.extra = {"account_id": instagram_account_id}
    elif target_platform == "weibo":
        weibo_token = os.getenv("WEIBO_ACCESS_TOKEN")
        if not weibo_token:
            console.print("[red]Error: WEIBO_ACCESS_TOKEN not set[/red]")
            raise typer.Exit(1)
        config.access_token = weibo_token
    elif target_platform == "linkedin":
        linkedin_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not linkedin_token:
            console.print("[red]Error: LINKEDIN_ACCESS_TOKEN not set[/red]")
            raise typer.Exit(1)
        config.access_token = linkedin_token
        config.extra = {"person_id": os.getenv("LINKEDIN_PERSON_ID")}
    elif target_platform == "threads":
        threads_token = os.getenv("THREADS_ACCESS_TOKEN")
        threads_user_id = os.getenv("THREADS_USER_ID")
        if not threads_token or not threads_user_id:
            console.print("[red]Error: THREADS_ACCESS_TOKEN and THREADS_USER_ID not set[/red]")
            raise typer.Exit(1)
        config.access_token = threads_token
        config.extra = {"user_id": threads_user_id}
    elif target_platform == "toutiao":
        toutiao_token = os.getenv("TOUTIAO_ACCESS_TOKEN")
        if not toutiao_token:
            console.print("[red]Error: TOUTIAO_ACCESS_TOKEN not set[/red]")
            raise typer.Exit(1)
        config.access_token = toutiao_token
    else:
        console.print(f"[red]Error: Unknown platform '{target_platform}'[/red]")
        supported = [
            "bluesky",
            "twitter",
            "xiaohongshu",
            "mastodon",
            "instagram",
            "weibo",
            "linkedin",
            "threads",
            "toutiao",
        ]
        console.print(f"[yellow]Supported platforms: {', '.join(supported)}[/yellow]")
        raise typer.Exit(1)

    try:
        connector = get_connector(target_platform, config)

        async def do_publish():
            await connector.connect()

            # Use publish_thread for threads if connector supports it
            if adapted.is_thread and hasattr(connector, "publish_thread"):
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
            console.print("\n[green]✅ Published successfully![/green]")
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
            console.print("\n[dim]Content status updated to 'published'[/dim]")
        else:
            failed = [r for r in results if not r.success]
            console.print(f"[red]❌ Failed to publish: {failed[0].error}[/red]")
            if len(results) > 1:
                success_count = sum(1 for r in results if r.success)
                console.print(
                    f"[yellow]Partial publish: {success_count}/{len(results)} posts succeeded[/yellow]"
                )
            raise typer.Exit(1)

    except CookieExpiredError as e:
        console.print("[red]❌ Cookie Expired[/red]")
        console.print(str(e))
        # Show refresh instructions for xiaohongshu
        if target_platform in ("xiaohongshu", "xhs"):
            from avatarfactory.connectors.xiaohongshu import XiaohongshuConnector

            console.print(XiaohongshuConnector(ConnectorConfig()).get_cookie_refresh_instructions())
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stats():
    """Show knowledges statistics."""
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = get_knowledge_base(kb_path)

    stats = kb.get_storage_stats()

    table = Table(title="Knowledges Statistics")
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
            console.print(
                "Get your cookie from browser DevTools after logging in to xiaohongshu.com"
            )
            raise typer.Exit(1)
        config.extra = {
            "cookie": xhs_cookie,
            "user_id": os.getenv("XIAOHONGSHU_USER_ID"),
            "b1": os.getenv("XIAOHONGSHU_B1"),
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
            console.print("[yellow]Connected but credentials may have limited permissions[/yellow]")

    except Exception as e:
        console.print(f"[red]Failed to connect: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def fetch(
    platform: str = typer.Argument(
        ..., help="Platform to fetch from (bluesky, twitter, xiaohongshu/xhs)"
    ),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of posts to fetch"),
):
    """
    Fetch trending content from a platform.

    Example:
        avatarfactory fetch bluesky --query "AI tools"
        avatarfactory fetch twitter -q "productivity" -n 20
        avatarfactory fetch xiaohongshu -q "产品经理"
        avatarfactory fetch xhs -n 20
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
            "b1": os.getenv("XIAOHONGSHU_B1"),
        }

    try:
        connector = get_connector(platform, config)

        async def do_fetch():
            await connector.connect()
            return await connector.fetch_trending(query=query, limit=limit)

        with console.status("[bold cyan]Fetching content...", spinner="dots"):
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
    platform: str = typer.Argument(
        ...,
        help="Platform to publish to (bluesky, twitter, xiaohongshu, mastodon, instagram, weibo, linkedin, threads, toutiao)",
    ),
    content: str = typer.Argument(..., help="Content to publish"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated hashtags"),
    title: Optional[str] = typer.Option(
        None, "--title", help="Content title (required for some platforms)"
    ),
):
    """
    Publish content to a platform.

    Example:
        avatarfactory publish bluesky "Hello world!"
        avatarfactory publish twitter "Check this out" --tags "ai,productivity"
        avatarfactory publish mastodon "Hello Fediverse!" --tags "introduction"
        avatarfactory publish linkedin "Professional insight" --title "My Insight"
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
        config.extra = {"access_token_secret": os.getenv("TWITTER_ACCESS_TOKEN_SECRET")}
    elif platform.lower() in ("xiaohongshu", "xhs"):
        config.extra = {
            "cookie": os.getenv("XIAOHONGSHU_COOKIE"),
            "user_id": os.getenv("XIAOHONGSHU_USER_ID"),
            "b1": os.getenv("XIAOHONGSHU_B1"),
        }
    elif platform.lower() == "mastodon":
        config.access_token = os.getenv("MASTODON_ACCESS_TOKEN")
        config.extra = {"instance_url": os.getenv("MASTODON_INSTANCE_URL")}
    elif platform.lower() == "instagram":
        config.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        config.extra = {"account_id": os.getenv("INSTAGRAM_ACCOUNT_ID")}
    elif platform.lower() == "weibo":
        config.access_token = os.getenv("WEIBO_ACCESS_TOKEN")
    elif platform.lower() == "linkedin":
        config.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        config.extra = {"person_id": os.getenv("LINKEDIN_PERSON_ID")}
    elif platform.lower() == "threads":
        config.access_token = os.getenv("THREADS_ACCESS_TOKEN")
        config.extra = {"user_id": os.getenv("THREADS_USER_ID")}
    elif platform.lower() == "toutiao":
        config.access_token = os.getenv("TOUTIAO_ACCESS_TOKEN")
    else:
        console.print(f"[red]Unknown platform: {platform}[/red]")
        supported = [
            "bluesky",
            "twitter",
            "xiaohongshu",
            "mastodon",
            "instagram",
            "weibo",
            "linkedin",
            "threads",
            "toutiao",
        ]
        console.print(f"[yellow]Supported platforms: {', '.join(supported)}[/yellow]")
        raise typer.Exit(1)

    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    try:
        connector = get_connector(platform, config)

        async def do_publish():
            await connector.connect()
            return await connector.publish(content=content, title=title, tags=tag_list)

        with console.status("[bold cyan]Publishing...", spinner="dots"):
            result = asyncio.run(do_publish())

        if result.success:
            console.print("[green]Published successfully![/green]")
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
# Topic Commands
# =============================================================================


def get_topic_agent() -> TopicAgent:
    """Initialize topic agent with LLM provider from environment."""
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = get_knowledge_base(kb_path)

    try:
        provider = LLMProviderFactory.from_env()
    except Exception as e:
        console.print(f"[red]Error initializing LLM provider: {e}[/red]")
        raise typer.Exit(1)

    return TopicAgent(knowledge_base=kb, llm_provider=provider)


@app.command()
def discover(
    platform: str = typer.Argument("bluesky", help="Platform to discover from (bluesky, twitter)"),
    persona_id: Optional[str] = typer.Option(
        None, "--persona", "-p", help="Persona ID for targeted discovery"
    ),
    query: Optional[str] = typer.Option(
        None, "--query", "-q", help="Search query (uses persona keywords if not provided)"
    ),
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
    console.print(
        Panel.fit(
            f"[bold cyan]Topic Agent[/bold cyan]\n"
            f"Platform: {platform}\n"
            f"Persona: {persona_id or 'None (general discovery)'}\n"
            f"Query: {query or 'Auto (from persona)'}",
            border_style="cyan",
        )
    )

    agent = get_topic_agent()

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
            return await agent._discover_trending(
                {
                    "platform": platform,
                    "query": query,
                    "limit": limit,
                }
            )

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
            console.print(
                f"[yellow]Trending Topics:[/yellow] {', '.join(analysis['trending_topics'][:5])}"
            )

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
            console.print(
                f"   [dim]Pillar:[/dim] {idea.get('suggested_pillar', 'N/A')} | [dim]Engagement:[/dim] {idea.get('estimated_engagement', 'medium')}"
            )

    # Display persona suggestions
    if "persona_suggestions" in data and data["persona_suggestions"]:
        console.print("\n[bold]Persona Optimization Suggestions[/bold]")
        for suggestion in data["persona_suggestions"]:
            console.print(f"  → {suggestion}")

    console.print(f"\n[dim]{result.get('message', 'Topic analysis complete.')}[/dim]")


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
    console.print(
        Panel.fit(
            f"[bold cyan]Getting Inspiration[/bold cyan]\n"
            f"Persona: {persona_id}\n"
            f"Platform: {platform}",
            border_style="cyan",
        )
    )

    agent = get_topic_agent()

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
            console.print(
                f"[dim]Type: {idea.get('content_type', 'post')} | Pillar: {idea.get('suggested_pillar', 'N/A')}[/dim]"
            )
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
    background: bool = typer.Option(False, "--background", "-b", help="Run daemon in background"),
):
    """
    Manage the background scheduler daemon.

    Example:
        avatarfactory daemon start              # Run in foreground
        avatarfactory daemon start --background # Run in background
        avatarfactory daemon status
        avatarfactory daemon stop
    """
    import subprocess
    import sys
    from avatarfactory.scheduler import Scheduler, SchedulerConfig

    pid_file = os.path.join(
        os.getenv("AVATARFACTORY_KB_PATH", "./knowledges"), "scheduler", "daemon.pid"
    )

    config = SchedulerConfig(
        data_dir=os.path.join(os.getenv("AVATARFACTORY_KB_PATH", "./knowledges"), "scheduler")
    )
    scheduler = Scheduler(config)

    if action == "start":
        if background:
            # Check if already running
            if os.path.exists(pid_file):
                try:
                    with open(pid_file, "r") as f:
                        old_pid = int(f.read().strip())
                    # Check if process is still running (Windows-compatible)
                    import signal

                    try:
                        os.kill(old_pid, 0)
                        console.print(f"[yellow]Daemon already running (PID: {old_pid})[/yellow]")
                        console.print("Use 'avatarfactory daemon stop' to stop it first.")
                        return
                    except OSError:
                        # Process not running, remove stale PID file
                        os.remove(pid_file)
                except (ValueError, FileNotFoundError):
                    pass

            # Start daemon in background
            console.print("[cyan]Starting daemon in background...[/cyan]")

            # Create a detached subprocess
            if sys.platform == "win32":
                # Windows: use CREATE_NO_WINDOW flag
                DETACHED_PROCESS = 0x00000008
                CREATE_NO_WINDOW = 0x08000000
                proc = subprocess.Popen(
                    [sys.executable, "-m", "avatarfactory.daemon_runner"],
                    creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                )
            else:
                # Unix: use nohup-style double fork
                proc = subprocess.Popen(
                    [sys.executable, "-m", "avatarfactory.daemon_runner"],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                )

            # Save PID
            os.makedirs(os.path.dirname(pid_file), exist_ok=True)
            with open(pid_file, "w") as f:
                f.write(str(proc.pid))

            console.print(f"[green]Daemon started (PID: {proc.pid})[/green]")
            console.print("Use 'avatarfactory daemon status' to check status.")
            console.print("Use 'avatarfactory daemon stop' to stop.")
            return

        # Foreground mode
        console.print(
            Panel.fit(
                "[bold cyan]Starting AvatarFactory Daemon[/bold cyan]\n" "Press Ctrl+C to stop",
                border_style="cyan",
            )
        )

        # Show scheduled tasks
        tasks = scheduler.list_tasks()
        if tasks:
            console.print(f"\n[green]Scheduled Tasks ({len(tasks)}):[/green]")
            for task in tasks:
                status = "✓" if task.enabled else "○"
                console.print(f"  {status} {task.name} ({task.schedule})")
        else:
            console.print(
                "\n[yellow]No scheduled tasks. Use 'avatarfactory schedule add' to create tasks.[/yellow]"
            )

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
                console.print(
                    f"      Last: {last_run} | Status: {last_status} | Runs: {task.run_count}"
                )

    elif action == "stop":
        # Try to stop background daemon
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as f:
                    daemon_pid = int(f.read().strip())

                import signal

                try:
                    if sys.platform == "win32":
                        # Windows: use taskkill
                        subprocess.run(
                            ["taskkill", "/F", "/PID", str(daemon_pid)], capture_output=True
                        )
                    else:
                        os.kill(daemon_pid, signal.SIGTERM)

                    console.print(f"[green]Daemon stopped (PID: {daemon_pid})[/green]")
                except OSError:
                    console.print(
                        f"[yellow]Daemon not running (PID {daemon_pid} not found)[/yellow]"
                    )

                os.remove(pid_file)
            except (ValueError, FileNotFoundError):
                console.print("[yellow]No daemon PID file found[/yellow]")
        else:
            console.print("[yellow]No background daemon running.[/yellow]")
            console.print("For foreground daemon, use Ctrl+C to stop.")

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Available actions: start, status, stop")
        raise typer.Exit(1)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload for development"),
    dashboard: bool = typer.Option(
        False, "--dashboard", "-d", help="Also start the visual dashboard"
    ),
    dashboard_port: int = typer.Option(8501, "--dashboard-port", help="Port for the dashboard"),
):
    """
    Start the AvatarFactory API server.

    Runs the full FastAPI service with integrated scheduler.

    Example:
        avatarfactory serve                    # Start on default port 8000
        avatarfactory serve --port 3000        # Custom port
        avatarfactory serve --reload           # Development mode with auto-reload
        avatarfactory serve --dashboard        # Start with visual dashboard
        avatarfactory serve -d --dashboard-port 8502  # Dashboard on custom port
    """
    from avatarfactory.daemon_runner import run_full_service

    display_host = host if host != "0.0.0.0" else "localhost"

    info_text = (
        f"[bold cyan]AvatarFactory API Server[/bold cyan]\n\n"
        f"Host: {host}\n"
        f"Port: {port}\n"
        f"Reload: {'enabled' if reload else 'disabled'}\n\n"
        f"API Docs: http://{display_host}:{port}/docs\n"
        f"Health: http://{display_host}:{port}/health"
    )

    if dashboard:
        info_text += (
            f"\n\n[bold cyan]Dashboard[/bold cyan]\n" f"URL: http://{display_host}:{dashboard_port}"
        )

    console.print(Panel.fit(info_text, title="Starting Service"))

    run_full_service(
        host=host,
        port=port,
        reload=reload,
        with_dashboard=dashboard,
        dashboard_port=dashboard_port,
    )


@app.command()
def dashboard(
    port: int = typer.Option(8501, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("localhost", "--host", "-h", help="Host to bind to"),
):
    """
    Start the AvatarFactory visual dashboard.

    Launches a Streamlit-based dashboard for:
    - System topology visualization
    - Persona management
    - Content browsing
    - Scheduler monitoring
    - Connector status

    Example:
        avatarfactory dashboard                    # Start on default port 8501
        avatarfactory dashboard --port 8502        # Custom port
        avatarfactory dashboard --host 0.0.0.0     # Accessible from network
    """
    import subprocess
    from pathlib import Path

    dashboard_path = Path(__file__).parent / "dashboard" / "Dashboard.py"

    if not dashboard_path.exists():
        console.print(
            "[red]Dashboard not found. Please ensure the dashboard module is installed.[/red]"
        )
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]AvatarFactory Dashboard[/bold cyan]\n\n"
            f"Host: {host}\n"
            f"Port: {port}\n\n"
            f"Dashboard URL: http://{host if host != '0.0.0.0' else 'localhost'}:{port}\n\n"
            f"[dim]Press Ctrl+C to stop[/dim]",
            title="Starting Dashboard",
            border_style="cyan",
        )
    )

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(dashboard_path),
                "--server.port",
                str(port),
                "--server.address",
                host,
                "--server.headless",
                "true",
            ]
        )
    except KeyboardInterrupt:
        console.print("\n[cyan]Dashboard stopped.[/cyan]")
    except FileNotFoundError:
        console.print(
            "[red]Streamlit not installed. Install with: pip install streamlit streamlit-agraph[/red]"
        )
        raise typer.Exit(1)


@app.command()
def schedule(
    action: str = typer.Argument(..., help="Action: add, remove, list, enable, disable"),
    task_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Task type: discovery, content, publish, report"
    ),
    persona_id: Optional[str] = typer.Option(None, "--persona", "-p", help="Persona ID"),
    platform: Optional[str] = typer.Option(None, "--platform", help="Platform (bluesky, twitter)"),
    cron: Optional[str] = typer.Option(
        None, "--cron", "-c", help="Cron schedule (e.g., '0 9 * * *')"
    ),
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
        data_dir=os.path.join(os.getenv("AVATARFACTORY_KB_PATH", "./knowledges"), "scheduler")
    )
    scheduler = Scheduler(config)

    if action == "list":
        tasks = scheduler.list_tasks()

        if not tasks:
            console.print("[yellow]No scheduled tasks.[/yellow]")
            console.print(
                "Create one with: avatarfactory schedule add --type discovery --persona <id> --cron '0 9 * * *'"
            )
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

        if task_type in ("topic", "discovery", "content", "report") and not persona_id:
            console.print(f"[red]--persona required for {task_type} tasks[/red]")
            raise typer.Exit(1)

        schedule_cron = cron or {
            "topic": "0 9 * * *",
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

    elif action == "run":
        # Manually run a task
        if not task_id:
            console.print("[red]--id required[/red]")
            raise typer.Exit(1)

        task = scheduler.get_task(task_id)
        if not task:
            console.print(f"[red]Task not found: {task_id}[/red]")
            raise typer.Exit(1)

        console.print(f"[cyan]Running task: {task.name}...[/cyan]")

        import asyncio

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(scheduler._run_task_async(task_id))
            finally:
                loop.close()
            console.print("[green]Task completed successfully[/green]")
        except Exception as e:
            console.print(f"[red]Task failed: {e}[/red]")
            raise typer.Exit(1)

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Available: add, remove, list, enable, disable")
        raise typer.Exit(1)


@app.command()
def queue(
    action: str = typer.Argument(..., help="Action: add, remove, list"),
    content_id: Optional[str] = typer.Option(None, "--content", "-c", help="Content ID to queue"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Target platform"),
    schedule_time: Optional[str] = typer.Option(
        None, "--time", "-t", help="Schedule time (ISO format or 'now')"
    ),
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
        data_dir=os.path.join(os.getenv("AVATARFACTORY_KB_PATH", "./knowledges"), "scheduler")
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
            scheduled = (
                item.scheduled_time.strftime("%m-%d %H:%M") if item.scheduled_time else "ASAP"
            )
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

        console.print("[green]Added to publish queue[/green]")
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


# =============================================================================
# Video Generation Commands
# =============================================================================


@app.command()
def video(
    action: str = typer.Argument(..., help="Action: generate, list-voices, list-avatars, info"),
    content_id: Optional[str] = typer.Option(
        None, "--content", "-c", help="Content ID to generate video from"
    ),
    video_type: str = typer.Option(
        "slideshow", "--type", "-t", help="Video type: slideshow or avatar"
    ),
    provider: str = typer.Option(
        "auto", "--provider", "-P", help="TTS provider: auto, azure, edge"
    ),
    voice: str = typer.Option("zh-CN-XiaoxuanNeural", "--voice", "-v", help="Voice ID for TTS"),
    avatar: Optional[str] = typer.Option(
        None, "--avatar", "-a", help="Avatar character (lisa, grace, harry, max)"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    images: Optional[str] = typer.Option(
        None, "--images", "-i", help="Comma-separated image paths for slideshow"
    ),
    locale: Optional[str] = typer.Option(
        None, "--locale", "-l", help="Filter voices by locale (e.g., zh-CN)"
    ),
):
    """
    Generate videos from content using TTS.

    Actions:
      generate      - Generate video from content
      list-voices   - List available TTS voices
      list-avatars  - List available avatar characters
      info          - Show provider information

    Examples:
        avatarfactory video generate --content content_7a86a064
        avatarfactory video generate -c content_xxx --type avatar --avatar lisa
        avatarfactory video generate -c content_xxx --provider edge
        avatarfactory video list-voices --locale zh-CN
        avatarfactory video list-avatars
        avatarfactory video info
    """
    from avatarfactory.video import VideoGenerator, VideoConfig
    from avatarfactory.video.base import VideoType

    if action == "generate":
        if not content_id:
            console.print("[red]--content required for generate action[/red]")
            raise typer.Exit(1)

        kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
        kb = get_knowledge_base(kb_path)

        content = kb.load_content(content_id)
        if not content:
            console.print(f"[red]Content not found: {content_id}[/red]")
            raise typer.Exit(1)

        # Parse images
        image_list = None
        if images:
            image_list = [Path(img.strip()) for img in images.split(",")]

        # Build config
        config = VideoConfig(
            video_type=VideoType.AVATAR if video_type == "avatar" else VideoType.SLIDESHOW,
            voice=voice,
            avatar_character=avatar,
            output_path=Path(output) if output else None,
        )

        console.print(
            Panel.fit(
                f"[bold cyan]Generating Video[/bold cyan]\n\n"
                f"[cyan]Content:[/cyan] {content_id}\n"
                f"[cyan]Type:[/cyan] {video_type}\n"
                f"[cyan]Provider:[/cyan] {provider}\n"
                f"[cyan]Voice:[/cyan] {voice}"
                + (f"\n[cyan]Avatar:[/cyan] {avatar}" if avatar else ""),
                border_style="cyan",
            )
        )

        generator = VideoGenerator(tts_provider=provider)

        # Check provider availability
        info = generator.get_provider_info()
        if not info["tts_available"]:
            console.print("[red]No TTS provider available![/red]")
            console.print("Install edge-tts (free): pip install edge-tts")
            console.print("Or configure Azure: set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION")
            raise typer.Exit(1)

        if video_type == "avatar" and not info["avatar_available"]:
            console.print("[red]Azure Avatar not available![/red]")
            console.print("Configure Azure: set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION")
            console.print("Region must support avatars (westus2, westeurope, southeastasia)")
            raise typer.Exit(1)

        # Get text from content
        text = content.body
        if content.title:
            text = f"{content.title}\n\n{text}"

        async def do_generate():
            return await generator.generate(
                content_id=content_id,
                text=text,
                config=config,
                images=image_list,
            )

        with console.status(f"[bold cyan]Generating {video_type} video...", spinner="dots"):
            result = asyncio.run(do_generate())

        if result.success:
            console.print("\n[green]✅ Video generated successfully![/green]")
            console.print(f"[bold]Video:[/bold] {result.video_path}")
            if result.audio_path:
                console.print(f"[bold]Audio:[/bold] {result.audio_path}")
            console.print(f"[bold]Duration:[/bold] {result.duration_formatted}")
            console.print("\n[dim]Metadata saved to video directory[/dim]")
        else:
            console.print(f"\n[red]❌ Video generation failed: {result.error}[/red]")
            raise typer.Exit(1)

    elif action == "list-voices":
        generator = VideoGenerator(tts_provider=provider)

        async def do_list():
            return await generator.list_voices(
                locale=locale,
                provider=provider if provider != "auto" else None,
            )

        with console.status("[bold cyan]Fetching voices...", spinner="dots"):
            voices = asyncio.run(do_list())

        if not voices:
            console.print("[yellow]No voices found.[/yellow]")
            return

        table = Table(title=f"Available Voices ({len(voices)})")
        table.add_column("Voice ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Gender", style="yellow")
        table.add_column("Locale", style="white")
        table.add_column("Provider", style="dim")

        # Group by locale for better display
        for v in voices[:50]:  # Limit to 50 for readability
            table.add_row(v.id, v.name, v.gender, v.locale, v.provider)

        console.print(table)

        if len(voices) > 50:
            console.print(
                f"\n[dim]Showing 50 of {len(voices)} voices. Use --locale to filter.[/dim]"
            )

        # Show recommended Chinese voices
        console.print("\n[bold]Recommended Chinese Voices:[/bold]")
        console.print("  zh-CN-XiaoxuanNeural  (Female, bright/活泼)")
        console.print("  zh-CN-YunxiNeural     (Male, professional)")
        console.print("  zh-CN-XiaohanNeural   (Female, warm)")
        console.print("  zh-CN-YunyangNeural   (Male, energetic)")

    elif action == "list-avatars":
        generator = VideoGenerator(tts_provider=provider)

        async def do_list():
            return await generator.list_avatars()

        avatars = asyncio.run(do_list())

        if not avatars:
            console.print("[yellow]No avatars available.[/yellow]")
            console.print("Azure Avatar requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION.")
            return

        table = Table(title="Available Avatar Characters")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="white")

        for a in avatars:
            table.add_row(a["id"], a["name"], a["description"])

        console.print(table)

    elif action == "info":
        generator = VideoGenerator(tts_provider=provider)
        info = generator.get_provider_info()

        table = Table(title="Video Generation Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="green")

        table.add_row("Active TTS Provider", info["tts_provider"] or "[red]None[/red]")
        table.add_row(
            "Edge TTS (Free)",
            "[green]Available[/green]" if info["edge_available"] else "[red]Not installed[/red]",
        )
        table.add_row(
            "Azure TTS",
            (
                "[green]Available[/green]"
                if info["azure_available"]
                else "[yellow]Not configured[/yellow]"
            ),
        )
        table.add_row(
            "Azure Avatar",
            (
                "[green]Available[/green]"
                if info["avatar_available"]
                else "[yellow]Not configured[/yellow]"
            ),
        )

        console.print(table)

        if not info["tts_available"]:
            console.print("\n[yellow]To enable video generation:[/yellow]")
            console.print("  1. Install edge-tts (free): pip install edge-tts")
            console.print("  2. Or configure Azure TTS:")
            console.print("     - Set AZURE_SPEECH_KEY=your_key")
            console.print("     - Set AZURE_SPEECH_REGION=eastasia")

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Available: generate, list-voices, list-avatars, info")
        raise typer.Exit(1)


@app.command()
def migrate_storage(
    dry_run: bool = typer.Option(
        True, "--dry-run/--execute", help="Preview changes without modifying files"
    ),
):
    """
    Migrate content and discovery data to new persona-based structure.

    This command migrates:
    - Content from knowledges/content_library/ to knowledges/personas/{id}/content/
    - Discovery from old format to timestamped files

    Example:
        avatarfactory migrate-storage --dry-run    # Preview changes
        avatarfactory migrate-storage --no-dry-run # Execute migration
    """
    import json
    import shutil
    from pathlib import Path
    from datetime import datetime

    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    base_path = Path(kb_path)

    console.print(Panel.fit("Storage Migration Tool", border_style="cyan"))

    if dry_run:
        console.print("[yellow]DRY RUN - No files will be modified[/yellow]\n")

    stats = {
        "content_migrated": 0,
        "discovery_migrated": 0,
        "errors": [],
    }

    # 1. Migrate content from content_library to persona directories
    console.print("[bold]1. Migrating content files...[/bold]")

    for folder in ["drafts", "published"]:
        legacy_dir = base_path / "content_library" / folder
        if not legacy_dir.exists():
            continue

        for file_path in legacy_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                persona_id = data.get("persona_id")
                if not persona_id:
                    console.print(f"  [yellow]Skipping {file_path.name} - no persona_id[/yellow]")
                    continue

                # Build new path
                created_at_str = data.get("created_at", "")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        datetime_str = created_at.strftime("%Y-%m-%d_%H-%M")
                    except Exception:
                        datetime_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
                else:
                    datetime_str = datetime.now().strftime("%Y-%m-%d_%H-%M")

                content_id = data.get("id", "unknown")
                new_filename = f"{datetime_str}_{content_id}.json"
                new_dir = base_path / "personas" / persona_id / "content" / folder
                new_path = new_dir / new_filename

                console.print(
                    f"  {file_path.name} -> personas/{persona_id}/content/{folder}/{new_filename}"
                )

                if not dry_run:
                    new_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, new_path)
                    file_path.unlink()

                stats["content_migrated"] += 1

            except Exception as e:
                stats["errors"].append(f"Content {file_path.name}: {e}")
                console.print(f"  [red]Error: {file_path.name} - {e}[/red]")

    # 2. Migrate discovery files to timestamped format
    console.print("\n[bold]2. Migrating discovery files...[/bold]")

    personas_dir = base_path / "personas"
    if personas_dir.exists():
        for persona_dir in personas_dir.iterdir():
            if not persona_dir.is_dir():
                continue

            discovery_dir = persona_dir / "discovery"
            if not discovery_dir.exists():
                continue

            for file_path in discovery_dir.glob("*.json"):
                # Check if already in new format (has datetime prefix)
                name = file_path.stem
                parts = name.split("_")

                # New format: 2026-02-06_12-00_bluesky (at least 3 parts with date)
                if len(parts) >= 3 and "-" in parts[0] and "-" in parts[1]:
                    continue  # Already migrated

                # Old format: bluesky.json
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Get timestamp from data or use file mtime
                    updated_at = data.get("updated_at") or data.get("created_at")
                    if updated_at:
                        try:
                            dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                        except Exception:
                            dt = datetime.fromtimestamp(file_path.stat().st_mtime)
                    else:
                        dt = datetime.fromtimestamp(file_path.stat().st_mtime)

                    datetime_str = dt.strftime("%Y-%m-%d_%H-%M")
                    platform = name  # Old format uses platform as filename
                    new_filename = f"{datetime_str}_{platform}.json"
                    new_path = discovery_dir / new_filename

                    console.print(f"  {persona_dir.name}/discovery/{name}.json -> {new_filename}")

                    if not dry_run:
                        # Update data with created_at field
                        data["created_at"] = dt.isoformat()
                        if "updated_at" in data:
                            del data["updated_at"]  # Use created_at instead

                        with open(new_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        file_path.unlink()

                    stats["discovery_migrated"] += 1

                except Exception as e:
                    stats["errors"].append(f"Discovery {file_path.name}: {e}")
                    console.print(f"  [red]Error: {file_path.name} - {e}[/red]")

    # Summary
    console.print("\n[bold]Migration Summary:[/bold]")
    console.print(f"  Content files: {stats['content_migrated']}")
    console.print(f"  Discovery files: {stats['discovery_migrated']}")

    if stats["errors"]:
        console.print(f"\n[yellow]Errors ({len(stats['errors'])}):[/yellow]")
        for error in stats["errors"]:
            console.print(f"  ⚠️  {error}")

    if dry_run:
        console.print(
            "\n[yellow]This was a dry run. Use --no-dry-run to execute migration.[/yellow]"
        )
    else:
        console.print("\n[green]✅ Migration complete![/green]")


# =============================================================================
# Recommendation Commands
# =============================================================================


@app.command()
def recommendations(
    limit: int = typer.Option(5, "--limit", "-n", help="Number of recommendations to show"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """
    List recommended personas based on recent trends.

    The system automatically discovers trending topics from social platforms
    and generates persona recommendations daily.

    Example:
        avatarfactory recommendations
        avatarfactory recommendations --limit 10
        avatarfactory recommendations --domain tech
    """
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = get_knowledge_base(kb_path)

    recs = kb.get_recommended_personas(limit=limit, domain=domain)

    if not recs:
        console.print("[yellow]No recommendations found.[/yellow]")
        console.print("\nThe system generates recommendations daily from trending topics.")
        console.print("Run 'avatarfactory scan-trends' to generate recommendations now.")
        return

    table = Table(title=f"Recommended Personas ({len(recs)})")
    table.add_column("ID", style="cyan", max_width=20)
    table.add_column("Name", style="bold")
    table.add_column("Domain", style="green")
    table.add_column("Tagline", max_width=40)
    table.add_column("Relevance", style="yellow", justify="right")
    table.add_column("Potential", style="magenta", justify="right")

    for rec in recs:
        table.add_row(
            rec.id,
            rec.name,
            rec.domain,
            rec.tagline[:37] + "..." if len(rec.tagline) > 40 else rec.tagline,
            f"{rec.relevance_score:.0f}",
            f"{rec.potential_score:.0f}",
        )

    console.print(table)
    console.print(
        "\n[dim]Use 'avatarfactory adopt <ID>' to create a persona from a recommendation.[/dim]"
    )


@app.command()
def adopt(
    recommendation_id: str = typer.Argument(..., help="Recommendation ID to adopt"),
):
    """
    Create a persona from a recommendation.

    Example:
        avatarfactory adopt rec_persona_abc123
    """
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    kb = get_knowledge_base(kb_path)

    # Load recommendation
    rec = kb.get_recommendation(recommendation_id)
    if not rec:
        console.print(f"[red]Recommendation {recommendation_id} not found.[/red]")
        console.print("Use 'avatarfactory recommendations' to see available recommendations.")
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"Adopting recommendation: {rec.name}\n"
            f"Domain: {rec.domain}\n"
            f"Tagline: {rec.tagline}",
            border_style="cyan",
        )
    )

    # Build description from recommendation
    description = (
        f"Create a {rec.domain} persona: {rec.name}. "
        f"Positioning: {rec.tagline}. "
        f"Target audience: {rec.target_audience}. "
        f"Expertise areas: {', '.join(rec.expertise)}. "
        f"Content pillars: {', '.join(rec.content_pillars)}. "
        f"Tone: {rec.suggested_tone}."
    )

    orchestrator = get_orchestrator()

    with console.status("[bold cyan]Creating persona from recommendation...", spinner="dots"):
        message = AgentMessage(
            sender="user",
            receiver="orchestrator",
            task_type=TaskType.CHAT,
            payload={"user_input": description},
            context={},
        )

        result = asyncio.run(orchestrator.process(message))

    if result.get("status") == "success":
        data = result.get("data", {})
        persona = data.get("persona", {})

        # Mark recommendation as adopted
        kb.mark_recommendation_adopted(recommendation_id, persona.get("id", ""))

        console.print("[green]✅ Persona created successfully![/green]")
        console.print(f"  ID: {persona.get('id')}")
        console.print(f"  Name: {persona['identity'].get('name')}")
        console.print(f"  Tagline: {persona['identity'].get('tagline')}")
        console.print(f"\n[dim]Based on recommendation: {rec.name}[/dim]")
    else:
        console.print(f"[red]Error: {result.get('message', 'Unknown error')}[/red]")
        raise typer.Exit(1)


@app.command(name="scan-trends")
def scan_trends(
    platforms: Optional[str] = typer.Option(
        "bluesky",
        "--platforms",
        "-p",
        help="Comma-separated platforms to scan (bluesky,twitter,xiaohongshu)",
    ),
    generate_recs: bool = typer.Option(
        True,
        "--generate-recommendations/--no-recommendations",
        help="Generate persona recommendations after scanning",
    ),
):
    """
    Scan trending topics from social platforms and generate recommendations.

    This is typically run automatically by the scheduler, but can be
    triggered manually to get fresh recommendations.

    Example:
        avatarfactory scan-trends
        avatarfactory scan-trends --platforms bluesky,twitter
        avatarfactory scan-trends --no-recommendations
    """
    from avatarfactory.scheduler.tasks import (
        run_trend_scan_task,
        run_persona_recommendation_task,
    )
    from avatarfactory.scheduler.engine import ScheduledTask

    platform_list = [p.strip() for p in platforms.split(",")]
    console.print(
        Panel.fit(f"Scanning trends from: {', '.join(platform_list)}", border_style="cyan")
    )

    # Create a mock task for the runner
    scan_task = ScheduledTask(
        id="manual_trend_scan",
        name="Manual Trend Scan",
        task_type="trend_scan",
        schedule="manual",
        extra_params={"platforms": platform_list, "limit": 30},
    )

    with console.status("[bold cyan]Scanning trending topics...", spinner="dots"):
        result = asyncio.run(run_trend_scan_task(scan_task))

    if result.get("success"):
        console.print(f"[green]✅ Scanned {result.get('platforms_scanned', 0)} platform(s)[/green]")
        console.print(f"   Snapshots saved: {result.get('snapshots_saved', 0)}")

        # Show per-platform results
        for platform, data in result.get("results", {}).items():
            if data.get("success"):
                console.print(
                    f"   • {platform}: {data.get('post_count', 0)} posts, "
                    f"{data.get('topics_count', 0)} topics"
                )
            else:
                console.print(
                    f"   • {platform}: [red]Failed - {data.get('error', 'Unknown')}[/red]"
                )

        # Generate recommendations if requested
        if generate_recs:
            console.print("\n[bold cyan]Generating persona recommendations...[/bold cyan]")

            rec_task = ScheduledTask(
                id="manual_persona_recommendation",
                name="Manual Persona Recommendation",
                task_type="persona_recommendation",
                schedule="manual",
                extra_params={"count": 3},
            )

            with console.status("[bold cyan]Analyzing trends...", spinner="dots"):
                rec_result = asyncio.run(run_persona_recommendation_task(rec_task))

            if rec_result.get("success"):
                recs = rec_result.get("recommendations", [])
                console.print(f"[green]✅ Generated {len(recs)} recommendation(s)[/green]")
                for rec in recs:
                    console.print(f"   • {rec.get('name')} ({rec.get('domain')})")
                console.print("\n[dim]Use 'avatarfactory recommendations' to view details.[/dim]")
            else:
                console.print(
                    f"[yellow]⚠️ Recommendation generation: {rec_result.get('error', 'Unknown')}[/yellow]"
                )
    else:
        console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
        raise typer.Exit(1)


# =============================================================================
# Database Migration Commands
# =============================================================================


@app.command()
def migrate_db(
    kb_path: str = typer.Option(
        "./knowledges", "--kb-path", "-k", help="Path to knowledges directory for migration"
    ),
    db_url: Optional[str] = typer.Option(
        None, "--db-url", "-d", help="Database URL (default: sqlite:///knowledges.db)"
    ),
    drop_existing: bool = typer.Option(
        False, "--drop", "-D", help="Drop existing tables before migration"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be migrated without actually migrating"
    ),
):
    """
    Migrate file-based storage to SQLite/PostgreSQL database.

    This command migrates all data from the file-based knowledges directory
    to a relational database for better performance and querying.

    Example:
        avatarfactory migrate-db
        avatarfactory migrate-db --kb-path ./knowledges
        avatarfactory migrate-db --db-url postgresql+asyncpg://user:pass@localhost/db
        avatarfactory migrate-db --drop --dry-run
    """
    from avatarfactory.core.database.migrate import run_migration

    console.print(
        Panel.fit(
            "[bold cyan]Database Migration Tool[/bold cyan]\n\n"
            f"Source: {kb_path}\n"
            f"Database: {db_url or 'sqlite:///knowledges.db (default)'}\n"
            f"Drop existing: {'Yes' if drop_existing else 'No'}",
            border_style="cyan",
        )
    )

    if dry_run:
        console.print("[yellow]DRY RUN - No actual migration will occur[/yellow]\n")
        console.print("Would migrate from:")
        console.print(f"  • Knowledges: {kb_path}")
        console.print(f"  • To database: {db_url or 'sqlite:///knowledges.db'}")

        # Check if source exists
        from pathlib import Path

        kb = Path(kb_path)
        if not kb.exists():
            console.print(f"\n[red]Error: Knowledges path not found: {kb_path}[/red]")
            raise typer.Exit(1)

        # Count potential items
        personas_count = (
            len(list((kb / "personas").glob("persona_*.yaml"))) if (kb / "personas").exists() else 0
        )
        content_count = len(list(kb.rglob("content_*.json")))
        discovery_count = len(list(kb.rglob("discovery_*.json")))
        tasks_count = 1 if (kb / "scheduler" / "tasks.yaml").exists() else 0

        console.print("\nWould migrate:")
        console.print(f"  • {personas_count} personas")
        console.print(f"  • {content_count} contents")
        console.print(f"  • {discovery_count} discoveries")
        console.print(f"  • {tasks_count} task config(s)")
        console.print("\n[yellow]Use without --dry-run to execute migration.[/yellow]")
        return

    # Set environment variable if db_url provided
    if db_url:
        os.environ["AVATARFACTORY_DB_URL"] = db_url

    with console.status("[bold cyan]Migrating data to database...", spinner="dots"):
        report = run_migration(
            kb_path=kb_path,
            drop_existing=drop_existing,
        )

    # Display results
    console.print("\n[bold]Migration Report[/bold]")

    table = Table()
    table.add_column("Entity", style="cyan")
    table.add_column("Migrated", style="green", justify="right")
    table.add_column("Errors", style="red", justify="right")

    table.add_row("Personas", str(report.personas_migrated), str(report.personas_errors))
    table.add_row("Contents", str(report.contents_migrated), str(report.contents_errors))
    table.add_row("Discoveries", str(report.discoveries_migrated), str(report.discoveries_errors))
    table.add_row("Scheduled Tasks", str(report.tasks_migrated), str(report.tasks_errors))
    table.add_row("Trend Snapshots", str(report.trends_migrated), str(report.trends_errors))
    table.add_row(
        "Recommendations", str(report.recommendations_migrated), str(report.recommendations_errors)
    )

    console.print(table)

    total_migrated = (
        report.personas_migrated
        + report.contents_migrated
        + report.discoveries_migrated
        + report.tasks_migrated
        + report.trends_migrated
        + report.recommendations_migrated
    )
    total_errors = (
        report.personas_errors
        + report.contents_errors
        + report.discoveries_errors
        + report.tasks_errors
        + report.trends_errors
        + report.recommendations_errors
    )

    if total_errors > 0:
        console.print(f"\n[yellow]⚠️ Migration completed with {total_errors} error(s)[/yellow]")
        if report.error_details:
            console.print("\n[bold]Error Details:[/bold]")
            for error in report.error_details[:10]:  # Show first 10 errors
                console.print(f"  • {error}")
            if len(report.error_details) > 10:
                console.print(f"  ... and {len(report.error_details) - 10} more errors")
    else:
        console.print("\n[green]✅ Migration completed successfully![/green]")
        console.print(f"   Total records migrated: {total_migrated}")


if __name__ == "__main__":
    app()
