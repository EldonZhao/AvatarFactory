"""
AvatarFactory Dashboard - Main Application.

A Streamlit-based dashboard for visualizing and managing the AvatarFactory system.
"""

import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from avatarfactory.dashboard.data import DashboardDataProvider

# Page configuration
st.set_page_config(
    page_title="AvatarFactory Dashboard",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 500;
    }
    .status-success {
        background: #e8f5e9;
        color: #2e7d32;
    }
    .status-warning {
        background: #fff3e0;
        color: #ef6c00;
    }
    .status-error {
        background: #ffebee;
        color: #c62828;
    }
</style>
""", unsafe_allow_html=True)


def main() -> None:
    """Main dashboard entry point."""
    # Initialize data provider
    kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
    provider = DashboardDataProvider(kb_path)

    # Store provider in session state for pages
    if "provider" not in st.session_state:
        st.session_state.provider = provider

    # Header
    st.markdown('<h1 class="main-header">🎭 AvatarFactory Dashboard</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">AI-Powered Persona Management for Social Platforms</p>',
        unsafe_allow_html=True
    )

    # Quick stats
    stats = provider.get_storage_stats()
    personas = provider.get_personas()
    tasks = provider.get_scheduled_tasks()
    connectors = provider.get_connector_statuses()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Personas", stats.get("total_personas", 0))
    with col2:
        st.metric("Drafts", stats.get("draft_contents", 0))
    with col3:
        st.metric("Published", stats.get("published_contents", 0))
    with col4:
        enabled_tasks = sum(1 for t in tasks if t.get("enabled"))
        st.metric("Active Tasks", enabled_tasks)
    with col5:
        configured = sum(1 for c in connectors if c.configured)
        st.metric("Connectors", f"{configured}/{len(connectors)}")

    st.divider()

    # Quick overview sections
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("### 👥 Recent Personas")
        if personas:
            for p in personas[:3]:
                platform_str = ", ".join(p.platforms) if p.platforms else "No platforms"
                content_count = p.draft_count + p.published_count

                st.markdown(f"""
                <div style="
                    background: white;
                    padding: 16px;
                    border-radius: 12px;
                    margin-bottom: 12px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="font-size: 16px;">{p.name}</strong>
                            <p style="color: #666; margin: 4px 0 0 0; font-size: 14px;">{p.tagline[:60]}...</p>
                        </div>
                        <div style="text-align: right;">
                            <span style="
                                background: #e3f2fd;
                                color: #1976d2;
                                padding: 4px 12px;
                                border-radius: 16px;
                                font-size: 12px;
                            ">{platform_str}</span>
                            <p style="color: #999; margin: 8px 0 0 0; font-size: 12px;">{content_count} content items</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            if len(personas) > 3:
                st.caption(f"+ {len(personas) - 3} more personas. See Personas page for all.")
        else:
            st.info("No personas yet. Create one using the CLI: `avatarfactory create-persona`")

    with col_right:
        st.markdown("### 🔌 Connector Status")
        for c in connectors:
            status_icon = "✅" if c.configured else "⚠️"
            status_color = "#4CAF50" if c.configured else "#ff9800"
            status_text = "Configured" if c.configured else "Not configured"

            st.markdown(f"""
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                background: white;
                border-radius: 8px;
                margin-bottom: 8px;
            ">
                <span style="font-weight: 500;">{c.platform.capitalize()}</span>
                <span style="color: {status_color};">{status_icon} {status_text}</span>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Navigation hints
    st.markdown("### 📍 Quick Navigation")
    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns(5)

    with nav_col1:
        st.page_link("pages/1_Topology.py", label="System Topology", icon="🗺️")
    with nav_col2:
        st.page_link("pages/2_Personas.py", label="Manage Personas", icon="👥")
    with nav_col3:
        st.page_link("pages/3_Scheduler.py", label="Task Scheduler", icon="⏰")
    with nav_col4:
        st.page_link("pages/4_Content.py", label="Browse Content", icon="📝")
    with nav_col5:
        st.page_link("pages/5_Topics.py", label="Content Ideas", icon="💡")

    # Footer
    st.markdown("---")
    st.markdown(
        '<p style="text-align: center; color: #999; font-size: 12px;">'
        'AvatarFactory Dashboard v1.0 | '
        '<a href="https://github.com/your-repo/avatarfactory">GitHub</a>'
        '</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
