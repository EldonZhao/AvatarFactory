"""
Personas Page - Manage and view personas.

Displays all personas with their details and content counts.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import streamlit as st

from avatarfactory.dashboard.data import DashboardDataProvider
from avatarfactory.dashboard.components.persona_card import render_persona_card, render_persona_details

st.set_page_config(
    page_title="Personas - AvatarFactory",
    page_icon="👥",
    layout="wide",
)

st.title("👥 Personas")
st.markdown("Manage and view all your social media personas.")

# Initialize provider
kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
provider = DashboardDataProvider(kb_path)

# Sidebar
with st.sidebar:
    st.markdown("### Actions")
    st.info(
        "**Create a new persona:**\n\n"
        "```bash\n"
        "avatarfactory create-persona \"description\"\n"
        "```"
    )

    st.markdown("### Filters")
    platform_filter = st.multiselect(
        "Filter by platform",
        ["xiaohongshu", "bluesky", "twitter", "zhihu", "douyin"],
        default=[]
    )

    if st.button("🔄 Refresh"):
        st.rerun()

# Get personas
personas = provider.get_personas()

# Apply filters
if platform_filter:
    personas = [
        p for p in personas
        if any(plat in p.platforms for plat in platform_filter)
    ]

# Session state for selected persona
if "selected_persona" not in st.session_state:
    st.session_state.selected_persona = None

# Stats
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Personas", len(personas))
with col2:
    total_drafts = sum(p.draft_count for p in personas)
    st.metric("Total Drafts", total_drafts)
with col3:
    total_published = sum(p.published_count for p in personas)
    st.metric("Total Published", total_published)

st.divider()

# Show personas
if not personas:
    st.info(
        "No personas found.\n\n"
        "Create your first persona using the CLI:\n"
        "```bash\n"
        "avatarfactory create-persona \"AI tools reviewer for product managers\"\n"
        "```"
    )
else:
    # Two-column layout for cards
    for i in range(0, len(personas), 2):
        cols = st.columns(2)

        for j, col in enumerate(cols):
            if i + j < len(personas):
                persona = personas[i + j]
                with col:
                    action = render_persona_card(
                        persona_id=persona.id,
                        name=persona.name,
                        tagline=persona.tagline,
                        platforms=persona.platforms,
                        version=persona.version,
                        draft_count=persona.draft_count,
                        published_count=persona.published_count,
                        created_at=persona.created_at.isoformat() if persona.created_at else None,
                    )

                    if action == "view":
                        st.session_state.selected_persona = persona.id
                    elif action == "content":
                        st.switch_page("pages/3_Content.py")
                    elif action == "delete":
                        st.warning(
                            f"To delete persona **{persona.name}**, use the CLI:\n"
                            f"```bash\n"
                            f"avatarfactory delete-persona {persona.id}\n"
                            f"```"
                        )

# Show selected persona details
if st.session_state.selected_persona:
    st.divider()
    persona_details = provider.get_persona_details(st.session_state.selected_persona)
    if persona_details:
        col1, col2 = st.columns([3, 1])
        with col1:
            render_persona_details(persona_details)
        with col2:
            if st.button("✖️ Close Details"):
                st.session_state.selected_persona = None
                st.rerun()

            st.markdown("---")
            st.markdown("### Quick Actions")

            st.markdown(
                f"**Generate content:**\n"
                f"```bash\n"
                f"avatarfactory generate \"topic\" -p {st.session_state.selected_persona}\n"
                f"```"
            )

            st.markdown(
                f"**Discover trends:**\n"
                f"```bash\n"
                f"avatarfactory discover bluesky -p {st.session_state.selected_persona}\n"
                f"```"
            )
