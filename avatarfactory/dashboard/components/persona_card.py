"""
Persona card component for dashboard.

Renders a visual card displaying persona information.
"""

from typing import Any, Dict, List, Optional

import streamlit as st


def render_persona_card(
    persona_id: str,
    name: str,
    tagline: str,
    platforms: List[str],
    version: str,
    draft_count: int = 0,
    published_count: int = 0,
    created_at: Optional[str] = None,
    notification_enabled: bool = False,
    notification_type: str = "",
    show_actions: bool = True,
) -> Optional[str]:
    """
    Render a persona card with information and actions.

    Args:
        persona_id: Unique persona identifier
        name: Persona name
        tagline: One-line description
        platforms: List of target platforms
        version: Persona version
        draft_count: Number of draft content items
        published_count: Number of published content items
        created_at: Creation timestamp
        notification_enabled: Whether notifications are enabled
        notification_type: Type of notification connector
        show_actions: Whether to show action buttons

    Returns:
        Action selected ("view", "edit", "delete") or None
    """
    action = None

    # Platform emoji mapping
    platform_emojis = {
        "xiaohongshu": "📕",
        "bluesky": "🦋",
        "twitter": "𝕏",
        "zhihu": "知",
        "douyin": "🎵",
    }

    # Notification type emoji mapping
    notification_emojis = {
        "wecom": "💬",
        "slack": "💼",
        "discord": "🎮",
        "telegram": "📨",
        "feishu": "🪶",
    }

    platform_badges = " ".join(
        platform_emojis.get(p.lower(), "📱") + " " + p
        for p in platforms
    )

    # Build notification badge
    if notification_enabled and notification_type:
        notif_emoji = notification_emojis.get(notification_type, "🔔")
        notification_badge = f'<span style="background: #e8f5e9; color: #2e7d32; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 8px;">{notif_emoji} {notification_type}</span>'
    else:
        notification_badge = '<span style="background: #f5f5f5; color: #999; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 8px;">🔕 notifications off</span>'

    with st.container():
        st.markdown(f"""
        <div style="
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        ">
            <h3 style="margin: 0 0 8px 0; color: #1a1a1a;">{name}</h3>
            <p style="color: #666; margin: 0 0 12px 0; font-size: 14px;">{tagline}</p>
            <div style="margin-bottom: 12px;">
                <span style="
                    background: #e3f2fd;
                    color: #1976d2;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    margin-right: 8px;
                ">{version}</span>
                <span style="font-size: 13px;">{platform_badges}</span>
                {notification_badge}
            </div>
            <div style="display: flex; gap: 16px; font-size: 13px; color: #666;">
                <span>📝 {draft_count} drafts</span>
                <span>✅ {published_count} published</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if show_actions:
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("👁️ View", key=f"view_{persona_id}", use_container_width=True):
                    action = "view"
            with col2:
                if st.button("📝 Content", key=f"content_{persona_id}", use_container_width=True):
                    action = "content"
            with col3:
                if st.button("🗑️ Delete", key=f"delete_{persona_id}", use_container_width=True):
                    action = "delete"

    return action


def render_persona_details(persona: Dict[str, Any]) -> None:
    """
    Render full persona details in an expanded view.

    Args:
        persona: Full persona dictionary
    """
    st.subheader(f"📋 {persona.get('identity', {}).get('name', 'Unknown')}")

    # Identity
    st.markdown("#### Identity")
    identity = persona.get("identity", {})
    st.write(f"**Tagline:** {identity.get('tagline', 'N/A')}")
    st.write(f"**Expertise:** {', '.join(identity.get('expertise', []))}")

    # Target Audience
    st.markdown("#### Target Audience")
    audience = persona.get("target_audience", {})
    st.write(f"**Primary:** {audience.get('primary', 'N/A')}")
    if audience.get("pain_points"):
        st.write("**Pain Points:**")
        for point in audience["pain_points"]:
            st.write(f"  - {point}")
    if audience.get("goals"):
        st.write("**Goals:**")
        for goal in audience["goals"]:
            st.write(f"  - {goal}")

    # Voice Style
    st.markdown("#### Voice Style")
    voice = persona.get("voice_style", {})
    st.write(f"**Tone:** {voice.get('tone', 'N/A')}")
    st.write(f"**Emoji Usage:** {voice.get('emoji_usage', 'moderate')}")
    if voice.get("language_patterns"):
        st.write("**Language Patterns:**")
        for pattern in voice["language_patterns"]:
            st.write(f"  - {pattern}")

    # Content Pillars
    st.markdown("#### Content Pillars")
    pillars = persona.get("content_pillars", [])
    for pillar in pillars:
        with st.expander(f"📌 {pillar.get('name', 'Unnamed')}"):
            st.write(pillar.get("description", "No description"))
            st.write(f"**Frequency:** {pillar.get('frequency', 'weekly')}")
            if pillar.get("examples"):
                st.write("**Examples:**")
                for ex in pillar["examples"]:
                    st.write(f"  - {ex}")

    # Boundaries
    st.markdown("#### Boundaries")
    boundaries = persona.get("boundaries", {})
    if boundaries.get("avoid"):
        st.write("**Avoid:**")
        for item in boundaries["avoid"]:
            st.write(f"  - ❌ {item}")
    if boundaries.get("compliance"):
        st.write("**Compliance:**")
        for item in boundaries["compliance"]:
            st.write(f"  - ✅ {item}")
