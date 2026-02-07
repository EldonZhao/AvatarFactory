"""
Content Page - Browse and preview generated content.

Displays content items with their scores and metadata.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import streamlit as st
import httpx

from avatarfactory.dashboard.data import DashboardDataProvider

st.set_page_config(
    page_title="Content - AvatarFactory",
    page_icon="📝",
    layout="wide",
)

st.title("📝 Content Library")
st.markdown("Browse and preview all generated content.")

# Initialize provider
kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
api_url = os.getenv("AVATARFACTORY_SERVICE_URL", "http://localhost:8000")
provider = DashboardDataProvider(kb_path)

# Sidebar filters
with st.sidebar:
    st.markdown("### Generate Content")

    with st.expander("✨ New Content", expanded=False):
        # Get personas for selection
        personas = provider.get_personas()
        persona_options = {}
        for p in personas:
            persona_options[f"{p.name} ({p.id[:12]}...)"] = p.id

        if persona_options:
            gen_persona_label = st.selectbox(
                "Persona",
                list(persona_options.keys()),
                key="gen_persona_select"
            )
            gen_persona_id = persona_options[gen_persona_label]

            gen_topic = st.text_input(
                "Topic",
                placeholder="e.g., AI productivity tools comparison",
                key="gen_topic"
            )

            gen_platform = st.selectbox(
                "Platform",
                ["xiaohongshu", "bluesky", "twitter"],
                key="gen_platform"
            )

            gen_variants = st.slider("Variants", 1, 3, 1, key="gen_variants")

            if st.button("Generate", key="generate_btn", type="primary"):
                if gen_topic:
                    with st.spinner("Generating content..."):
                        try:
                            with httpx.Client(timeout=180) as client:
                                response = client.post(
                                    f"{api_url}/content/generate",
                                    json={
                                        "topic": gen_topic,
                                        "persona_id": gen_persona_id,
                                        "platform": gen_platform,
                                        "variants": gen_variants
                                    }
                                )
                                if response.status_code == 200:
                                    data = response.json()
                                    st.success(f"Generated {len(data.get('content_ids', []))} content(s)!")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {response.status_code}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                else:
                    st.warning("Please enter a topic")
        else:
            st.info("Create a persona first")

    st.markdown("---")
    st.markdown("### Filters")

    status_filter = st.radio(
        "Status",
        ["draft", "published"],
        index=0,
        horizontal=True,
    )

    personas = provider.get_personas()
    # Create persona options with readable names
    persona_options = {"All": None}
    for p in personas:
        persona_options[f"{p.name} ({p.id[:12]}...)"] = p.id

    # Use key parameter to track selection changes
    persona_filter_label = st.selectbox(
        "Persona",
        list(persona_options.keys()),
        key="persona_filter_select"
    )
    selected_persona = persona_options[persona_filter_label]

    limit = st.slider("Max items", 10, 100, 50, key="content_limit_slider")

    if st.button("🔄 Refresh", key="refresh_content"):
        st.rerun()

    st.markdown("---")
    st.markdown("### Bulk Actions")

    # Initialize bulk delete confirmation state
    if "bulk_delete_confirm" not in st.session_state:
        st.session_state.bulk_delete_confirm = False

    if st.session_state.bulk_delete_confirm:
        selected_count = len(st.session_state.get("selected_contents", []))
        st.warning(f"⚠️ Delete {selected_count} selected content(s)?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ Yes, Delete", key="confirm_bulk_delete", type="primary"):
                if "selected_contents" in st.session_state and st.session_state.selected_contents:
                    deleted_count = 0
                    for content_id in st.session_state.selected_contents:
                        if provider.delete_content(content_id):
                            deleted_count += 1
                    st.success(f"Deleted {deleted_count} content(s)")
                    st.session_state.selected_contents = []
                    st.session_state.bulk_delete_confirm = False
                    st.rerun()
        with col_no:
            if st.button("❌ Cancel", key="cancel_bulk_delete"):
                st.session_state.bulk_delete_confirm = False
                st.rerun()
    else:
        if st.button("🗑️ Delete Selected", key="delete_selected_content_btn", type="secondary"):
            if "selected_contents" in st.session_state and st.session_state.selected_contents:
                st.session_state.bulk_delete_confirm = True
                st.rerun()
            else:
                st.warning("No items selected")

# Initialize session state for selections
if "selected_contents" not in st.session_state:
    st.session_state.selected_contents = []

# Get content
contents = provider.get_content_list(
    persona_id=selected_persona,
    status=status_filter,
    limit=limit,
)

# Stats
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Items", len(contents))
with col2:
    avg_score = sum(c.get("review_score", 0) or 0 for c in contents) / max(len(contents), 1)
    st.metric("Avg Score", f"{avg_score:.1f}")
with col3:
    platforms = set(c.get("platform", "unknown") for c in contents)
    st.metric("Platforms", len(platforms))

st.divider()

# Build persona ID to name mapping
persona_name_map = {p.id: p.name for p in personas}

# Session state for selected content
if "selected_content_id" not in st.session_state:
    st.session_state.selected_content_id = None

# Content detail view - show FIRST if selected
if st.session_state.selected_content_id:
    content_details = provider.get_content_details(st.session_state.selected_content_id)

    if content_details:
        st.markdown("## 📄 Content Preview")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"### {content_details.get('title', 'Untitled')}")

            # Metadata
            detail_platform = content_details.get("platform", "unknown")
            created_at = content_details.get("created_at", "Unknown")
            pillar = content_details.get("pillar", "N/A")

            st.markdown(f"""
            <div style="
                display: flex;
                gap: 16px;
                margin-bottom: 16px;
                color: #666;
                font-size: 14px;
            ">
                <span>📱 {detail_platform}</span>
                <span>📌 {pillar}</span>
                <span>📅 {created_at[:10] if created_at else 'N/A'}</span>
            </div>
            """, unsafe_allow_html=True)

            # Body
            st.markdown("#### Content Body")
            body = content_details.get("body", "No content")
            st.markdown(body)

            # Tags
            tags = content_details.get("tags", [])
            if tags:
                st.markdown("#### Tags")
                st.write(" ".join(f"`#{tag}`" for tag in tags))

            # Image prompts
            image_prompts = content_details.get("image_prompts", [])
            if image_prompts:
                st.markdown("#### 🖼️ Image Prompts")
                for i, prompt in enumerate(image_prompts, 1):
                    st.info(f"**Image {i}:** {prompt}")

        with col2:
            # Clear session state to close detail view
            if st.button("✖️ Close", key="close_detail"):
                st.session_state.selected_content_id = None
                st.rerun()

            st.markdown("---")

            # Review score
            detail_score = content_details.get("review_score")
            if detail_score is not None:
                st.metric("Review Score", f"{detail_score}/100")

            issues = content_details.get("review_issues", [])
            if issues:
                st.markdown("**Issues:**")
                for issue in issues[:5]:
                    st.caption(f"⚠️ {issue}")

            st.markdown("---")

            # Delete button for single content with confirmation
            if "single_delete_confirm" not in st.session_state:
                st.session_state.single_delete_confirm = False

            if st.session_state.single_delete_confirm:
                st.warning("⚠️ Delete this content?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Yes", key="confirm_single_delete", type="primary"):
                        if provider.delete_content(st.session_state.selected_content_id):
                            st.success("Deleted!")
                            st.session_state.selected_content_id = None
                            st.session_state.single_delete_confirm = False
                            st.rerun()
                        else:
                            st.error("Failed to delete")
                with col_no:
                    if st.button("❌ No", key="cancel_single_delete"):
                        st.session_state.single_delete_confirm = False
                        st.rerun()
            else:
                if st.button("🗑️ Delete", key="delete_this_content", type="secondary"):
                    st.session_state.single_delete_confirm = True
                    st.rerun()

        st.divider()
    else:
        st.error(f"Content not found: {st.session_state.selected_content_id}")
        if st.button("← Back to list", key="back_to_list"):
            st.session_state.selected_content_id = None
            st.rerun()
        st.divider()

# Content list
if not contents:
    st.info(
        f"No {status_filter} content found.\n\n"
        "Generate content using the sidebar or CLI."
    )
else:
    st.markdown("### Content List")

    # Platform emoji mapping
    platform_emojis = {
        "xiaohongshu": "📕",
        "bluesky": "🦋",
        "twitter": "𝕏",
    }

    # Create a table view
    for content in contents:
        content_id = content["id"]
        title = content.get("title", "Untitled")
        if len(title) > 50:
            title = title[:50] + "..."

        persona_id = content.get("persona_id", "Unknown")
        persona_name = persona_name_map.get(persona_id, persona_id[:12] + "..." if persona_id else "Unknown")
        platform = content.get("platform", "unknown")
        emoji = platform_emojis.get(platform, "📱")
        pillar = content.get("pillar", "N/A")
        score = content.get("review_score")

        with st.container():
            col1, col2, col3, col4 = st.columns([4, 2, 1, 1])

            with col1:
                st.markdown(f"**{title}**")
                st.caption(f"{emoji} {platform} | {persona_name} | {pillar[:15] if pillar else 'N/A'}")

            with col2:
                if score is not None:
                    if score >= 80:
                        st.success(f"{score}/100")
                    elif score >= 60:
                        st.warning(f"{score}/100")
                    else:
                        st.error(f"{score}/100")
                else:
                    st.caption("Not reviewed")

            with col3:
                # Checkbox for selection
                is_selected = content_id in st.session_state.selected_contents
                if st.checkbox("Select", value=is_selected, key=f"sel_{content_id}", label_visibility="collapsed"):
                    if content_id not in st.session_state.selected_contents:
                        st.session_state.selected_contents.append(content_id)
                elif content_id in st.session_state.selected_contents:
                    st.session_state.selected_contents.remove(content_id)

            with col4:
                if st.button("👁️", key=f"view_{content_id}", help="View details"):
                    st.session_state.selected_content_id = content_id
                    st.rerun()

        st.divider()

    # Show selection count
    if st.session_state.selected_contents:
        st.info(f"Selected {len(st.session_state.selected_contents)} item(s) for deletion")
