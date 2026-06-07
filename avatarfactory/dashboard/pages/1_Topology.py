"""
Topology Page - System architecture visualization.

Displays a hierarchical view showing:
- Personas and their configurations
- Scheduled tasks (SubAgents) per persona
- Data flow: source connectors -> processing -> target connectors
"""

import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

import streamlit as st

from avatarfactory.dashboard.data import DashboardDataProvider
from avatarfactory.dashboard.components.topology_graph import build_topology_graph, AGRAPH_AVAILABLE

st.set_page_config(
    page_title="Topology - AvatarFactory",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ System Topology")
st.markdown("Hierarchical view of personas, agents, and data flows.")

# Initialize provider
kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
provider = DashboardDataProvider(kb_path)

# Sidebar
with st.sidebar:
    st.markdown("### View Options")
    show_disabled_tasks = st.checkbox("Show disabled tasks", value=False)
    show_unconfigured = st.checkbox("Show unconfigured connectors", value=True)

    if st.button("🔄 Refresh"):
        st.rerun()

# Get data
personas = provider.get_personas()
tasks = provider.get_scheduled_tasks()
connectors = provider.get_connector_statuses()

# Filter connectors if needed
if not show_unconfigured:
    connectors = [c for c in connectors if c.configured]

# Quick stats
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Personas", len(personas))
with col2:
    enabled_tasks = sum(1 for t in tasks if t.get("enabled"))
    st.metric("Active Tasks", enabled_tasks)
with col3:
    configured = sum(1 for c in connectors if c.configured)
    st.metric("Connectors Ready", configured)
with col4:
    total_content = sum(p.draft_count + p.published_count for p in personas)
    st.metric("Total Content", total_content)

st.divider()

# Task type definitions for data flow
TASK_DATA_FLOWS = {
    "topic": {
        "name": "Topic",
        "icon": "🔍",
        "description": "Fetch trending content from platforms",
        "source": "Platform",  # From platform
        "target": "KB",  # To knowledges
        "flow": "Platform → Topic Agent → Knowledges",
    },
    "discovery": {
        "name": "Topic (legacy)",
        "icon": "🔍",
        "description": "Fetch trending content from platforms",
        "source": "Platform",
        "target": "KB",
        "flow": "Platform → Topic Agent → Knowledges",
    },
    "content": {
        "name": "Content Generation",
        "icon": "📝",
        "description": "Generate content based on persona and trends",
        "source": "KB",  # From knowledges (trends)
        "target": "KB",  # To knowledges (drafts)
        "flow": "Knowledges → Content Agent → Drafts",
    },
    "publish": {
        "name": "Publishing",
        "icon": "📤",
        "description": "Publish approved content to platforms",
        "source": "KB",  # From knowledges (drafts)
        "target": "Platform",  # To platform
        "flow": "Drafts → Review Agent → Platform",
    },
    "report": {
        "name": "Reporting",
        "icon": "📊",
        "description": "Generate and send performance reports",
        "source": "KB",
        "target": "Notification",
        "flow": "Analytics → Report Agent → Notification",
    },
}

# Connector icons
CONNECTOR_ICONS = {
    "bluesky": "🦋",
    "twitter": "𝕏",
    "xiaohongshu": "📕",
    "wecom": "💬",
}

# ============================================================================
# Hierarchical View
# ============================================================================

if not personas:
    st.info(
        "No personas found. Create one to see the system topology.\n\n"
        "```bash\n"
        'avatarfactory create-persona "your persona description"\n'
        "```"
    )
else:
    # Show each persona with its tasks and data flows
    for persona in personas:
        # Persona header
        with st.expander(f"👤 **{persona.name}** - {persona.tagline[:50]}...", expanded=True):
            # Persona info row
            info_col1, info_col2, info_col3 = st.columns(3)

            with info_col1:
                st.markdown(
                    f"**Tagline:** {persona.tagline[:50] if persona.tagline else 'None'}..."
                )

            with info_col2:
                st.markdown(
                    f"**Content:** {persona.draft_count} drafts, {persona.published_count} published"
                )

            with info_col3:
                st.markdown(f"**Version:** {persona.version}")

            st.markdown("---")

            # Get tasks for this persona
            persona_tasks = [t for t in tasks if t.get("persona_id") == persona.id]

            if not show_disabled_tasks:
                persona_tasks = [t for t in persona_tasks if t.get("enabled")]

            if persona_tasks:
                st.markdown("#### 🔄 Scheduled Tasks (SubAgents)")

                for task in persona_tasks:
                    task_type = task.get("task_type", "unknown")
                    task_info = TASK_DATA_FLOWS.get(task_type, {})
                    task_icon = task_info.get("icon", "📌")
                    task_name = task_info.get("name", task_type.capitalize())
                    data_flow = task_info.get("flow", "N/A")

                    # Status styling
                    enabled = task.get("enabled", True)
                    last_status = task.get("last_status", "never")

                    # Platform info
                    task_platform = task.get("platform", "")
                    platform_icon = CONNECTOR_ICONS.get(task_platform, "") if task_platform else ""
                    platform_display = f"{platform_icon} {task_platform}" if task_platform else ""

                    # Schedule display
                    schedule = task.get("schedule", "N/A")
                    run_count = task.get("run_count", 0)

                    # Render task card using Streamlit native components
                    with st.container():
                        tcol1, tcol2 = st.columns([4, 1])
                        with tcol1:
                            st.markdown(f"**{task_icon} {task_name}** {platform_display}")
                        with tcol2:
                            if not enabled:
                                st.caption("⬜ DISABLED")
                            elif last_status == "success":
                                st.caption("✅ SUCCESS")
                            elif last_status == "failed":
                                st.caption("❌ FAILED")
                            else:
                                st.caption("🔵 PENDING")

                        st.caption(f"⏰ Schedule: `{schedule}` | 🔢 Runs: {run_count}")
                        st.info(f"**Data Flow:** {data_flow}")
                        st.markdown("---")

            else:
                st.caption("No scheduled tasks for this persona.")
                st.markdown(
                    "Add a task: `avatarfactory schedule add --type discovery "
                    f"--persona {persona.id} --cron '0 9 * * *'`"
                )

            # Show connector data flow diagram
            st.markdown("---")
            st.markdown("#### 📊 Data Flow Overview")

            # Get discovery platforms from tasks (source) vs persona platforms (target)
            discovery_platforms = set()
            for task in persona_tasks:
                if task.get("task_type") == "discovery" and task.get("platform"):
                    discovery_platforms.add(task.get("platform"))

            # If no discovery tasks, default to bluesky as common source
            if not discovery_platforms:
                discovery_platforms = {"bluesky"}

            # Build flow diagram
            flow_cols = st.columns([1, 1, 1, 1, 1])

            with flow_cols[0]:
                st.markdown("**📥 Sources**")
                for p in discovery_platforms:
                    icon = CONNECTOR_ICONS.get(p, "📱")
                    configured = any(c.platform == p and c.configured for c in connectors)
                    status = "✅" if configured else "⚠️"
                    st.markdown(f"{icon} {p} {status}")

            with flow_cols[1]:
                st.markdown("**→**")
                st.markdown("")
                st.markdown("🔍 Discovery")

            with flow_cols[2]:
                st.markdown("**📦 Processing**")
                st.markdown("📝 Content Agent")
                st.markdown("⭐ Review Agent")

            with flow_cols[3]:
                st.markdown("**→**")
                st.markdown("")
                st.markdown("📤 Publish")

            with flow_cols[4]:
                st.markdown("**📤 Targets**")
                # Get target platforms from content tasks
                content_platforms = set()
                for task in persona_tasks:
                    if task.get("task_type") == "content" and task.get("platform"):
                        content_platforms.add(task.get("platform"))

                # Use platforms from content tasks
                target_platforms = content_platforms

                for p in target_platforms:
                    icon = CONNECTOR_ICONS.get(p, "📱")
                    configured = any(c.platform == p and c.configured for c in connectors)
                    status = "✅" if configured else "⚠️"
                    st.markdown(f"{icon} {p} {status}")
                # Also show notification connector
                wecom_configured = any(c.platform == "wecom" and c.configured for c in connectors)
                st.markdown(f"💬 WeChat Work {'✅' if wecom_configured else '⚠️'}")

st.divider()

# ============================================================================
# Connectors Overview
# ============================================================================

st.markdown("### 🔌 Connectors Status")

# Sort: configured first
sorted_connectors = sorted(connectors, key=lambda c: (not c.configured, c.platform))

conn_cols = st.columns(len(sorted_connectors) if sorted_connectors else 1)

for i, conn in enumerate(sorted_connectors):
    with conn_cols[i]:
        icon = CONNECTOR_ICONS.get(conn.platform, "📱")
        status_color = "#4CAF50" if conn.configured else "#ff9800"
        status_text = "Ready" if conn.configured else "Not configured"

        st.markdown(
            f"""
        <div style="
            text-align: center;
            padding: 16px;
            background: white;
            border-radius: 8px;
            border: 2px solid {status_color};
        ">
            <div style="font-size: 32px;">{icon}</div>
            <div style="font-weight: 600; margin: 8px 0;">{conn.platform.capitalize()}</div>
            <div style="color: {status_color}; font-size: 12px;">{status_text}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

# ============================================================================
# Interactive Graph (Optional)
# ============================================================================

if AGRAPH_AVAILABLE:
    st.divider()

    with st.expander("📈 Interactive Graph View (Advanced)", expanded=False):
        st.markdown("Click on nodes to see details. Drag to rearrange.")

        # Get topology data
        topology = provider.get_topology_data()

        # Graph settings
        col1, col2 = st.columns(2)
        with col1:
            physics_enabled = st.checkbox("Enable physics", value=True)
        with col2:
            graph_height = st.slider("Height", 400, 800, 500)

        # Render graph
        selected = build_topology_graph(
            nodes=topology["nodes"],
            edges=topology["edges"],
            height=graph_height,
            physics_enabled=physics_enabled,
        )

        if selected:
            node = next((n for n in topology["nodes"] if n["id"] == selected), None)
            if node:
                st.info(f"Selected: **{node['label']}** ({node['type']})")
