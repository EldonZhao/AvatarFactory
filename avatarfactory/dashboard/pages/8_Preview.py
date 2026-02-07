"""
Content Preview Page - View and manage individual content items.

Dedicated page for viewing content with proper Markdown rendering.
Access via: /Preview?id=content_xxx
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import streamlit as st

from avatarfactory.dashboard.data import DashboardDataProvider

st.set_page_config(
    page_title="Content Preview - AvatarFactory",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",  # Hide sidebar by default
)

# Hide sidebar completely with CSS
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    [data-testid="stSidebarNav"] {
        display: none;
    }
    .stDeployButton {
        display: none;
    }
    #MainMenu {
        display: none;
    }
    header {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize provider
kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
provider = DashboardDataProvider(kb_path)

# Get content_id from query params
query_params = st.query_params
content_id = query_params.get("id", None)

if not content_id:
    st.title("📄 Content Preview")
    st.warning("No content specified.")
    st.info("This page requires a content ID. Access via notification links or Dashboard.")
    st.stop()

# Load content details
content = provider.get_content_details(content_id)

if not content:
    st.title("📄 Content Preview")
    st.error(f"Content not found: `{content_id}`")
    st.stop()

# Get persona info
personas = provider.get_personas()
persona_map = {p.id: p for p in personas}
persona_id = content.get("persona_id")
persona = persona_map.get(persona_id)
persona_name = persona.name if persona else "Unknown"

# Page header
title = content.get("title", "Untitled")
st.title(f"📄 {title}")

# Metadata bar
platform = content.get("platform", "unknown")
created_at = content.get("created_at", "")
pillar = content.get("pillar", "")
review_score = content.get("review_score")

platform_emojis = {
    "xiaohongshu": "📕",
    "bluesky": "🦋",
    "twitter": "𝕏",
}
platform_emoji = platform_emojis.get(platform, "📱")

# Create metadata columns
meta_cols = st.columns([2, 2, 2, 2, 2])
with meta_cols[0]:
    st.markdown(f"**👤 Persona**")
    st.caption(persona_name)
with meta_cols[1]:
    st.markdown(f"**{platform_emoji} Platform**")
    st.caption(platform.capitalize() if platform else "N/A")
with meta_cols[2]:
    st.markdown(f"**📌 Pillar**")
    st.caption(pillar if pillar else "N/A")
with meta_cols[3]:
    st.markdown(f"**📅 Created**")
    st.caption(created_at[:10] if created_at else "N/A")
with meta_cols[4]:
    if review_score is not None:
        if review_score >= 80:
            st.markdown(f"**✅ Score**")
            st.success(f"{review_score:.0f}/100")
        elif review_score >= 60:
            st.markdown(f"**⚠️ Score**")
            st.warning(f"{review_score:.0f}/100")
        else:
            st.markdown(f"**❌ Score**")
            st.error(f"{review_score:.0f}/100")
    else:
        st.markdown(f"**📊 Score**")
        st.caption("Not reviewed")

st.divider()

# Main content area - two columns
col_main, col_side = st.columns([3, 1])

with col_main:
    # Content body with Markdown rendering
    st.markdown("### 📝 Content Body")

    body = content.get("body", "")

    if body:
        # Render in a styled container
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #f5f7fa 0%, #f8f9fc 100%);
                border: 1px solid #e1e4e8;
                border-radius: 12px;
                padding: 24px;
                margin: 16px 0;
                line-height: 1.8;
                font-size: 16px;
            ">
            """,
            unsafe_allow_html=True
        )

        # Render the actual Markdown content
        st.markdown(body)

        st.markdown("</div>", unsafe_allow_html=True)

        # Word/character count
        char_count = len(body)
        word_count = len(body.split())
        st.caption(f"📊 {char_count} characters | ~{word_count} words")
    else:
        st.info("No content body available.")

    # Tags
    tags = content.get("tags", [])
    if tags:
        st.markdown("### 🏷️ Tags")
        tag_html = " ".join(
            f'<span style="background: #e3f2fd; color: #1976d2; padding: 4px 12px; '
            f'border-radius: 16px; margin-right: 8px; font-size: 14px;">#{tag}</span>'
            for tag in tags
        )
        st.markdown(tag_html, unsafe_allow_html=True)

    # Image prompts
    image_prompts = content.get("image_prompts", [])
    if image_prompts:
        st.markdown("### 🖼️ Image Prompts")
        for i, prompt in enumerate(image_prompts, 1):
            with st.expander(f"Image {i}", expanded=True):
                st.markdown(
                    f"""
                    <div style="
                        background: #fff3e0;
                        border-left: 4px solid #ff9800;
                        padding: 16px;
                        border-radius: 0 8px 8px 0;
                        font-style: italic;
                    ">
                    {prompt}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

with col_side:
    # Actions
    st.markdown("### ⚡ Actions")

    if st.button("📋 Copy Content", key="copy_content", use_container_width=True):
        # Streamlit doesn't have native clipboard, show in text area
        st.text_area("Copy this content:", body, height=150, key="copy_area")

    st.markdown("---")

    # Review details
    if review_score is not None:
        st.markdown("### 📊 Review Details")

        # Score breakdown visualization
        st.progress(review_score / 100)

        review_issues = content.get("review_issues", [])
        if review_issues:
            st.markdown("**Issues Found:**")
            for issue in review_issues[:5]:
                st.markdown(
                    f"""
                    <div style="
                        background: #fff8e1;
                        border-left: 3px solid #ffc107;
                        padding: 8px 12px;
                        margin: 4px 0;
                        border-radius: 0 4px 4px 0;
                        font-size: 13px;
                    ">
                    ⚠️ {issue}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.success("No issues found!")

# Footer with content ID
st.divider()
st.caption(f"Content ID: `{content_id}`")
