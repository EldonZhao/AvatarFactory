"""
Content Page - Browse and preview generated content.

Displays content items with their scores and metadata.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import streamlit as st

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
provider = DashboardDataProvider(kb_path)

# Sidebar filters
with st.sidebar:
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

    persona_filter_label = st.selectbox("Persona", list(persona_options.keys()))
    selected_persona = persona_options[persona_filter_label]

    limit = st.slider("Max items", 10, 100, 50)

    if st.button("🔄 Refresh"):
        st.rerun()

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
if "selected_content" not in st.session_state:
    st.session_state.selected_content = None

# Content list
if not contents:
    st.info(
        f"No {status_filter} content found.\n\n"
        "Generate content using the CLI:\n"
        "```bash\n"
        "avatarfactory generate \"your topic here\"\n"
        "```"
    )
else:
    # Platform emoji mapping
    platform_emojis = {
        "xiaohongshu": "📕",
        "bluesky": "🦋",
        "twitter": "𝕏",
    }

    # Create a table view
    for content in contents:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])

            with col1:
                title = content.get("title", "Untitled")
                if len(title) > 50:
                    title = title[:50] + "..."
                st.markdown(f"**{title}**")

            with col2:
                persona_id = content.get("persona_id", "Unknown")
                persona_name = persona_name_map.get(persona_id, persona_id[:12] + "...")
                platform = content.get("platform", "unknown")
                emoji = platform_emojis.get(platform, "📱")
                st.caption(f"{emoji} {platform} | {persona_name}")

            with col3:
                pillar = content.get("pillar", "N/A")
                st.caption(pillar[:15] if pillar else "N/A")

            with col4:
                score = content.get("review_score")
                if score is not None:
                    if score >= 80:
                        st.success(f"{score}/100")
                    elif score >= 60:
                        st.warning(f"{score}/100")
                    else:
                        st.error(f"{score}/100")
                else:
                    st.caption("N/A")

            with col5:
                if st.button("👁️", key=f"view_{content['id']}", help="View details"):
                    st.session_state.selected_content = content["id"]
                    st.rerun()

            st.divider()

# Content detail view
if st.session_state.selected_content:
    content_details = provider.get_content_details(st.session_state.selected_content)

    if content_details:
        st.markdown("---")
        st.markdown("## 📄 Content Preview")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"### {content_details.get('title', 'Untitled')}")

            # Metadata
            platform = content_details.get("platform", "unknown")
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
                <span>📱 {platform}</span>
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
            if st.button("✖️ Close"):
                st.session_state.selected_content = None
                st.rerun()

            st.markdown("---")

            # Review score
            score = content_details.get("review_score")
            if score is not None:
                st.metric("Review Score", f"{score}/100")

            issues = content_details.get("review_issues", [])
            if issues:
                st.markdown("**Issues:**")
                for issue in issues[:5]:
                    st.caption(f"⚠️ {issue}")

            st.markdown("---")
            st.markdown("### Actions")

            content_id = st.session_state.selected_content
            st.code(f"avatarfactory show-content {content_id}", language="bash")
            st.code(f"avatarfactory publish-draft {content_id}", language="bash")
