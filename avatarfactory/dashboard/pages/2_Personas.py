"""
Personas Page - Manage and view personas.

Displays all personas with their details and content counts.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import streamlit as st
import httpx

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
api_url = os.getenv("AVATARFACTORY_SERVICE_URL", "http://localhost:8000")
provider = DashboardDataProvider(kb_path)

# Sidebar
with st.sidebar:
    st.markdown("### Create Persona")

    with st.expander("➕ New Persona", expanded=False):
        persona_description = st.text_area(
            "Description",
            placeholder="e.g., AI tools reviewer for product managers, focusing on practical insights",
            height=100,
            key="new_persona_desc"
        )

        persona_platforms = st.multiselect(
            "Platforms",
            ["xiaohongshu", "bluesky", "twitter"],
            default=["xiaohongshu"],
            key="new_persona_platforms"
        )

        st.markdown("**Notification Settings**")

        notification_enabled = st.checkbox(
            "Enable notifications",
            value=True,
            key="new_persona_notif_enabled"
        )

        notification_type = st.selectbox(
            "Notification Type",
            ["wecom", "slack", "discord", "feishu"],
            key="new_persona_notif_type",
            disabled=not notification_enabled
        )

        notify_on_content = st.checkbox(
            "Notify on content generation",
            value=True,
            key="new_persona_notify_content",
            disabled=not notification_enabled
        )

        notify_on_review = st.checkbox(
            "Notify on review completion",
            value=True,
            key="new_persona_notify_review",
            disabled=not notification_enabled
        )

        notify_on_discovery = st.checkbox(
            "Notify on discovery completion",
            value=True,
            key="new_persona_notify_discovery",
            disabled=not notification_enabled
        )

        if st.button("Create Persona", key="create_persona_btn", type="primary"):
            if persona_description:
                with st.spinner("Creating persona..."):
                    try:
                        with httpx.Client(timeout=120) as client:
                            response = client.post(
                                f"{api_url}/personas",
                                json={
                                    "description": persona_description,
                                    "platforms": persona_platforms,
                                    "notification": {
                                        "enabled": notification_enabled,
                                        "connector_type": notification_type if notification_enabled else "wecom",
                                        "notify_on_content": notify_on_content if notification_enabled else False,
                                        "notify_on_review": notify_on_review if notification_enabled else False,
                                        "notify_on_discovery": notify_on_discovery if notification_enabled else False
                                    }
                                }
                            )
                            if response.status_code == 200:
                                data = response.json()
                                st.success(f"Created: {data.get('name', 'New Persona')}")
                                st.rerun()
                            else:
                                st.error(f"Error: {response.status_code}")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")
            else:
                st.warning("Please enter a description")

    st.markdown("---")
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
                        notification_enabled=persona.notification_enabled,
                        notification_type=persona.notification_type,
                    )

                    if action == "view":
                        st.session_state.selected_persona = persona.id
                    elif action == "content":
                        st.switch_page("pages/3_Content.py")
                    elif action == "delete":
                        # Confirm deletion
                        if f"confirm_delete_{persona.id}" not in st.session_state:
                            st.session_state[f"confirm_delete_{persona.id}"] = False

                        if st.session_state[f"confirm_delete_{persona.id}"]:
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("✅ Yes, Delete", key=f"yes_delete_{persona.id}"):
                                    try:
                                        with httpx.Client(timeout=30) as client:
                                            response = client.delete(f"{api_url}/personas/{persona.id}")
                                            if response.status_code == 200:
                                                st.success("Deleted!")
                                                st.session_state[f"confirm_delete_{persona.id}"] = False
                                                st.rerun()
                                            else:
                                                st.error(f"Error: {response.status_code}")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                            with col_no:
                                if st.button("❌ Cancel", key=f"cancel_delete_{persona.id}"):
                                    st.session_state[f"confirm_delete_{persona.id}"] = False
                                    st.rerun()
                        else:
                            st.session_state[f"confirm_delete_{persona.id}"] = True
                            st.rerun()

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

            # Generate content button
            if st.button("📝 Generate Content", key="quick_generate_content"):
                st.switch_page("pages/3_Content.py")

            # View content button
            if st.button("📋 View Content", key="quick_view_content"):
                st.switch_page("pages/3_Content.py")
