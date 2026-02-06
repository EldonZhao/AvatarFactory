"""
Topology Page - Interactive system visualization.

Displays an interactive graph showing the relationships between
personas, agents, connectors, and scheduled tasks.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import streamlit as st

from avatarfactory.dashboard.data import DashboardDataProvider
from avatarfactory.dashboard.components.topology_graph import build_topology_graph, AGRAPH_AVAILABLE

st.set_page_config(
    page_title="Topology - AvatarFactory",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ System Topology")
st.markdown("Interactive visualization of the AvatarFactory system architecture.")

# Initialize provider
kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
provider = DashboardDataProvider(kb_path)

# Check if streamlit-agraph is available
if not AGRAPH_AVAILABLE:
    st.warning(
        "📦 **streamlit-agraph not installed**\n\n"
        "Install it with: `pip install streamlit-agraph`\n\n"
        "The topology graph requires this package for interactive visualization."
    )

    # Show text-based topology instead
    st.markdown("### 📊 System Overview (Text)")

    topology = provider.get_topology_data()

    st.markdown("#### Agents")
    agents = [n for n in topology["nodes"] if n["type"] == "agent"]
    for agent in agents:
        st.write(f"  - 🔮 **{agent['label']}**")

    st.markdown("#### Personas")
    personas = [n for n in topology["nodes"] if n["type"] == "persona"]
    for persona in personas:
        st.write(f"  - 💎 **{persona['label']}**")
        meta = persona.get("metadata", {})
        if meta:
            st.caption(f"    Drafts: {meta.get('draft', 0)} | Published: {meta.get('published', 0)}")

    st.markdown("#### Connectors")
    connectors = [n for n in topology["nodes"] if n["type"] == "connector"]
    for conn in connectors:
        status = "✅" if conn["color"] != "#CCCCCC" else "⚠️"
        st.write(f"  - {status} **{conn['label']}**")

    st.markdown("#### Scheduled Tasks")
    tasks = [n for n in topology["nodes"] if n["type"] == "task"]
    for task in tasks:
        status = "✅" if task["color"] != "#CCCCCC" else "⏸️"
        st.write(f"  - {status} **{task['label']}**")

else:
    # Sidebar controls
    with st.sidebar:
        st.markdown("### Graph Settings")
        physics_enabled = st.checkbox("Enable physics simulation", value=True)
        graph_height = st.slider("Graph height", 400, 800, 600)

        st.markdown("### Legend")
        st.markdown("""
        - 💎 **Diamond** = Persona
        - 📦 **Box** = Agent
        - 🔺 **Triangle** = Connector
        - ⭐ **Star** = Task
        - 🔘 Grayed = Disabled/Not configured
        """)

        st.markdown("### Refresh")
        if st.button("🔄 Refresh Data"):
            st.rerun()

    # Get topology data
    topology = provider.get_topology_data()

    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    node_counts = {}
    for node in topology["nodes"]:
        node_type = node["type"]
        node_counts[node_type] = node_counts.get(node_type, 0) + 1

    with col1:
        st.metric("Personas", node_counts.get("persona", 0))
    with col2:
        st.metric("Agents", node_counts.get("agent", 0))
    with col3:
        st.metric("Connectors", node_counts.get("connector", 0))
    with col4:
        st.metric("Tasks", node_counts.get("task", 0))

    st.divider()

    # Render graph
    selected = build_topology_graph(
        nodes=topology["nodes"],
        edges=topology["edges"],
        height=graph_height,
        physics_enabled=physics_enabled,
    )

    # Show selected node info
    if selected:
        st.markdown("---")
        st.markdown(f"### Selected: `{selected}`")

        # Find node details
        node = next((n for n in topology["nodes"] if n["id"] == selected), None)
        if node:
            st.write(f"**Type:** {node['type'].capitalize()}")
            st.write(f"**Label:** {node['label']}")
            if node.get("metadata"):
                st.write("**Details:**")
                st.json(node["metadata"])

            # Show connected nodes
            connected = [e["target"] for e in topology["edges"] if e["source"] == selected]
            connected += [e["source"] for e in topology["edges"] if e["target"] == selected]
            if connected:
                st.write(f"**Connected to:** {', '.join(connected)}")
