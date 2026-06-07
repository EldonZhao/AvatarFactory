"""
Topics Page - View discovered content ideas.

Displays content ideas from discovery scans, grouped by persona.
"""

import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

import streamlit as st

from avatarfactory.dashboard.data import DashboardDataProvider

st.set_page_config(
    page_title="Topics - AvatarFactory",
    page_icon="💡",
    layout="wide",
)

st.title("💡 Content Ideas")
st.markdown("Browse content ideas discovered from platform scans.")

# Initialize provider
kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
provider = DashboardDataProvider(kb_path)

# Get personas
personas_list = provider.get_personas()

# Sidebar filters
with st.sidebar:
    st.markdown("### Filters")

    # Persona filter
    persona_options = {"All Personas": None}
    for p in personas_list:
        persona_options[f"{p.name} ({p.id[:12]}...)"] = p.id

    persona_filter_label = st.selectbox(
        "Persona", list(persona_options.keys()), key="topic_persona_filter"
    )
    selected_persona = persona_options[persona_filter_label]

    # Platform filter
    platform_filter = st.selectbox(
        "Platform", ["All", "bluesky", "xiaohongshu", "twitter"], key="topic_platform_filter"
    )
    selected_platform = None if platform_filter == "All" else platform_filter

    # Limit per persona
    discoveries_per_persona = st.slider(
        "Discoveries per persona",
        1,
        10,
        5,
        key="discoveries_per_persona",
        help="Number of recent discoveries to show per persona",
    )

    if st.button("🔄 Refresh"):
        st.rerun()

# Build persona name map
persona_name_map = {p.id: p.name for p in personas_list}

# Platform emoji mapping
platform_emojis = {
    "xiaohongshu": "📕",
    "bluesky": "🦋",
    "twitter": "𝕏",
}

# Engagement badge colors
engagement_colors = {
    "high": "🔥",
    "medium": "⭐",
    "low": "💭",
}


def get_content_ideas(discovery: dict) -> list:
    """Extract content ideas from discovery data."""
    # Try report.content_ideas first, then fall back to ideas
    report = discovery.get("report", {})
    if report and report.get("content_ideas"):
        return report.get("content_ideas", [])
    return discovery.get("ideas", [])


def render_idea_card(idea: dict):
    """Render a single idea card."""
    platform = idea["platform"]
    emoji = platform_emojis.get(platform, "📱")
    engagement = idea["engagement"]
    engagement_icon = engagement_colors.get(engagement, "💭")

    with st.container():
        # Header row
        col1, col2 = st.columns([5, 1])

        with col1:
            st.markdown(f"**{idea['topic']}**")
            st.caption(
                f"{emoji} {platform} | "
                f"📌 {idea['pillar'][:20] if idea['pillar'] else 'N/A'} | "
                f"📅 {idea['discovery_date']}"
            )

        with col2:
            st.markdown(f"{engagement_icon} {engagement}")

        # Hook
        if idea["hook"]:
            st.info(f"🎣 {idea['hook']}")

        # Details in expander
        with st.expander("More details"):
            if idea["angle"]:
                st.markdown(f"**Angle:** {idea['angle']}")
            if idea["reasoning"]:
                st.markdown(f"**Why:** {idea['reasoning']}")
            st.markdown(f"**Content Type:** `{idea['content_type']}`")

        st.divider()


# Collect all ideas grouped by persona
all_ideas = []

# Get personas to iterate
if selected_persona:
    persona_ids = [selected_persona]
else:
    persona_ids = [p.id for p in personas_list]

for persona_id in persona_ids:
    # Get recent discoveries for this persona (limited)
    discoveries = provider.kb.list_discovery_history(
        persona_id, platform=selected_platform, limit=discoveries_per_persona
    )

    persona_name = persona_name_map.get(persona_id, persona_id[:12] + "...")

    for discovery in discoveries:
        ideas = get_content_ideas(discovery)
        platform = discovery.get("platform", "unknown")
        created_at = discovery.get("created_at", "")[:10]

        for idea in ideas:
            all_ideas.append(
                {
                    "persona_id": persona_id,
                    "persona_name": persona_name,
                    "platform": platform,
                    "discovery_date": created_at,
                    "topic": idea.get("topic", "Untitled"),
                    "hook": idea.get("hook", ""),
                    "angle": idea.get("angle", ""),
                    "content_type": idea.get("content_type", "post"),
                    "pillar": idea.get("suggested_pillar", ""),
                    "engagement": idea.get("estimated_engagement", "medium"),
                    "reasoning": idea.get("reasoning", ""),
                }
            )

# Stats
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Ideas", len(all_ideas))
with col2:
    st.metric("Personas", len(persona_ids))
with col3:
    platforms_found = set(i["platform"] for i in all_ideas)
    st.metric("Platforms", len(platforms_found))

st.divider()

# Display ideas
if not all_ideas:
    st.info(
        "No content ideas found.\n\n"
        "Run discovery to generate content ideas:\n"
        "```bash\n"
        "avatarfactory discover --platform bluesky --limit 30\n"
        "```"
    )
else:
    # Group by persona if showing all
    if not selected_persona:
        # Show ideas grouped by persona
        for persona_id in persona_ids:
            persona_ideas = [i for i in all_ideas if i["persona_id"] == persona_id]
            if not persona_ideas:
                continue

            persona_name = persona_name_map.get(persona_id, persona_id[:12])

            with st.expander(f"👤 **{persona_name}** ({len(persona_ideas)} ideas)", expanded=True):
                for idea in persona_ideas:
                    render_idea_card(idea)
    else:
        # Show flat list for single persona
        st.markdown(
            f"### Ideas for {persona_name_map.get(selected_persona, selected_persona[:12])}"
        )
        for idea in all_ideas:
            render_idea_card(idea)
