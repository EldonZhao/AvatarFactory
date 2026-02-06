"""
Topics Page - View and manage discovered topics/ideas.

Displays trending topics and ideas from discovery scans.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import streamlit as st

from avatarfactory.dashboard.data import DashboardDataProvider

st.set_page_config(
    page_title="Topics - AvatarFactory",
    page_icon="💡",
    layout="wide",
)

st.title("💡 Discovered Topics")
st.markdown("View and manage topics discovered from platform scans.")

# Initialize provider
kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
provider = DashboardDataProvider(kb_path)

# Get personas for filtering
personas_list = provider.get_personas()

# Sidebar filters
with st.sidebar:
    st.markdown("### Filters")

    # Persona filter
    persona_options = {"All": None}
    for p in personas_list:
        persona_options[f"{p.name} ({p.id[:12]}...)"] = p.id

    persona_filter_label = st.selectbox(
        "Persona",
        list(persona_options.keys()),
        key="topic_persona_filter"
    )
    selected_persona = persona_options[persona_filter_label]

    # Platform filter
    platform_filter = st.selectbox(
        "Platform",
        ["All", "bluesky", "xiaohongshu", "twitter"],
        key="topic_platform_filter"
    )
    selected_platform = None if platform_filter == "All" else platform_filter

    limit = st.slider("Max items", 10, 100, 50, key="topic_limit_slider")

    if st.button("🔄 Refresh"):
        st.rerun()

    st.markdown("---")
    st.markdown("### Bulk Actions")

    if st.button("🗑️ Delete Selected", key="delete_selected_btn", type="secondary"):
        if "selected_discoveries" in st.session_state and st.session_state.selected_discoveries:
            deleted_count = 0
            for item in st.session_state.selected_discoveries:
                if provider.delete_discovery(item["persona_id"], item["filename"]):
                    deleted_count += 1
            st.success(f"Deleted {deleted_count} discovery record(s)")
            st.session_state.selected_discoveries = []
            st.rerun()
        else:
            st.warning("No items selected")

# Initialize session state for selections
if "selected_discoveries" not in st.session_state:
    st.session_state.selected_discoveries = []

if "selected_discovery_detail" not in st.session_state:
    st.session_state.selected_discovery_detail = None

# Get discovery history
discoveries = provider.get_discovery_history(
    persona_id=selected_persona,
    platform=selected_platform,
    limit=limit,
)

# Stats
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Discoveries", len(discoveries))
with col2:
    platforms = set(d.get("platform", "unknown") for d in discoveries)
    st.metric("Platforms", len(platforms))
with col3:
    total_ideas = sum(len(d.get("ideas", [])) for d in discoveries)
    st.metric("Total Ideas", total_ideas)

st.divider()

# Detail view - show FIRST if selected
if st.session_state.selected_discovery_detail:
    detail = st.session_state.selected_discovery_detail

    st.markdown("## 📊 Discovery Details")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"### {detail.get('platform', 'Unknown').capitalize()} Discovery")
        st.markdown(f"**Date:** {detail.get('created_at', 'N/A')[:16]}")
        st.markdown(f"**Persona:** {detail.get('persona_name', detail.get('persona_id', 'Unknown'))}")

        # Trending patterns
        patterns = detail.get("patterns", [])
        if patterns:
            st.markdown("#### 📈 Trending Patterns")
            for i, pattern in enumerate(patterns[:10], 1):
                if isinstance(pattern, dict):
                    st.markdown(f"{i}. **{pattern.get('topic', pattern.get('pattern', 'N/A'))}** - {pattern.get('description', '')}")
                else:
                    st.markdown(f"{i}. {pattern}")

        # Ideas
        ideas = detail.get("ideas", [])
        if ideas:
            st.markdown("#### 💡 Generated Ideas")
            for i, idea in enumerate(ideas[:10], 1):
                if isinstance(idea, dict):
                    st.info(f"**{idea.get('title', f'Idea {i}')}**\n\n{idea.get('description', idea.get('content', ''))}")
                else:
                    st.info(f"**Idea {i}:** {idea}")

        # Raw data
        with st.expander("📄 Raw Data"):
            st.json(detail)

    with col2:
        if st.button("✖️ Close", key="close_discovery_detail"):
            st.session_state.selected_discovery_detail = None
            st.rerun()

        st.markdown("---")

        # Delete button
        if st.button("🗑️ Delete", key="delete_this_discovery", type="secondary"):
            filename = detail.get("_filename")
            persona_id = detail.get("persona_id")
            if filename and persona_id:
                if provider.delete_discovery(persona_id, filename):
                    st.success("Deleted!")
                    st.session_state.selected_discovery_detail = None
                    st.rerun()
                else:
                    st.error("Failed to delete")

    st.divider()

# Discovery list
if not discoveries:
    st.info(
        "No discovery results found.\n\n"
        "Run discovery to find trending topics:\n"
        "```bash\n"
        "avatarfactory discover --platform bluesky --limit 30\n"
        "```"
    )
else:
    # Platform emoji mapping
    platform_emojis = {
        "xiaohongshu": "📕",
        "bluesky": "🦋",
        "twitter": "𝕏",
    }

    # Build persona name map
    persona_name_map = {p.id: p.name for p in personas_list}

    st.markdown("### 📋 Discovery History")

    for discovery in discoveries:
        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([0.5, 2, 2, 1, 1, 1])

            with col1:
                # Checkbox for selection
                filename = discovery.get("_filename", "")
                persona_id = discovery.get("persona_id", "")
                is_selected = any(
                    s["filename"] == filename and s["persona_id"] == persona_id
                    for s in st.session_state.selected_discoveries
                )

                if st.checkbox(
                    "",
                    value=is_selected,
                    key=f"select_{persona_id}_{filename}",
                    label_visibility="collapsed"
                ):
                    if not is_selected:
                        st.session_state.selected_discoveries.append({
                            "filename": filename,
                            "persona_id": persona_id,
                        })
                else:
                    st.session_state.selected_discoveries = [
                        s for s in st.session_state.selected_discoveries
                        if not (s["filename"] == filename and s["persona_id"] == persona_id)
                    ]

            with col2:
                platform = discovery.get("platform", "unknown")
                emoji = platform_emojis.get(platform, "📱")
                created = discovery.get("created_at", "")[:16]
                st.markdown(f"{emoji} **{platform}** - {created}")

            with col3:
                persona_name = persona_name_map.get(persona_id, persona_id[:12] + "...")
                st.caption(f"👤 {persona_name}")

            with col4:
                patterns_count = len(discovery.get("patterns", []))
                st.caption(f"📈 {patterns_count} patterns")

            with col5:
                ideas_count = len(discovery.get("ideas", []))
                st.caption(f"💡 {ideas_count} ideas")

            with col6:
                if st.button("👁️", key=f"view_{persona_id}_{filename}", help="View details"):
                    # Load full details
                    detail = provider.get_discovery_details(persona_id, filename)
                    if detail:
                        detail["persona_id"] = persona_id
                        detail["persona_name"] = persona_name_map.get(persona_id, persona_id)
                        st.session_state.selected_discovery_detail = detail
                        st.rerun()

            st.divider()

    # Show selection count
    if st.session_state.selected_discoveries:
        st.info(f"Selected {len(st.session_state.selected_discoveries)} item(s) for deletion")
