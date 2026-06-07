"""
Topology graph component using streamlit-agraph.

Builds an interactive network visualization of the AvatarFactory system.
"""

from typing import Any, Dict, List, Optional

try:
    from streamlit_agraph import agraph, Node, Edge, Config

    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False


def build_topology_graph(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    height: int = 600,
    physics_enabled: bool = True,
) -> Optional[str]:
    """
    Build and render an interactive topology graph.

    Args:
        nodes: List of node dictionaries with id, label, type, size, color
        edges: List of edge dictionaries with source, target, label
        height: Graph height in pixels
        physics_enabled: Whether to enable physics simulation

    Returns:
        Selected node ID if a node was clicked, None otherwise
    """
    if not AGRAPH_AVAILABLE:
        return None

    # Build agraph nodes
    agraph_nodes = []
    for node in nodes:
        # Icon based on node type
        shape = "dot"
        if node.get("type") == "persona":
            shape = "diamond"
        elif node.get("type") == "agent":
            shape = "box"
        elif node.get("type") == "connector":
            shape = "triangle"
        elif node.get("type") == "task":
            shape = "star"

        agraph_nodes.append(
            Node(
                id=node["id"],
                label=node["label"],
                size=node.get("size", 25),
                color=node.get("color", "#4A90D9"),
                shape=shape,
                title=f"{node.get('type', 'unknown').capitalize()}: {node['label']}",
            )
        )

    # Build agraph edges
    agraph_edges = []
    for edge in edges:
        agraph_edges.append(
            Edge(
                source=edge["source"],
                target=edge["target"],
                label=edge.get("label", ""),
                color=edge.get("color", "#888888"),
            )
        )

    # Configuration
    config = Config(
        width="100%",
        height=height,
        directed=True,
        physics=physics_enabled,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=False,
        node={
            "labelProperty": "label",
            "renderLabel": True,
        },
        link={
            "labelProperty": "label",
            "renderLabel": True,
        },
    )

    # Render graph and return selected node
    return agraph(
        nodes=agraph_nodes,
        edges=agraph_edges,
        config=config,
    )


def get_node_legend() -> Dict[str, str]:
    """Get legend for node types and their colors."""
    return {
        "Persona": "#4A90D9 (Diamond)",
        "Agent": "#7B68EE (Box)",
        "Connector": "#50C878 (Triangle)",
        "Task": "#FFB347 (Star)",
    }
