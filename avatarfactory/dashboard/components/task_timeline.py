"""
Task timeline component for dashboard.

Renders scheduled tasks and their execution history.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st


def render_task_timeline(
    tasks: List[Dict[str, Any]],
    show_disabled: bool = True,
) -> Optional[str]:
    """
    Render a timeline of scheduled tasks.

    Args:
        tasks: List of task dictionaries
        show_disabled: Whether to show disabled tasks

    Returns:
        Task ID if an action was taken, None otherwise
    """
    if not tasks:
        st.info("No scheduled tasks. Create one from the CLI.")
        return None

    selected_task = None

    # Filter tasks
    if not show_disabled:
        tasks = [t for t in tasks if t.get("enabled")]

    # Group by type
    task_types = {}
    for task in tasks:
        task_type = task.get("task_type", "unknown")
        if task_type not in task_types:
            task_types[task_type] = []
        task_types[task_type].append(task)

    # Type icons
    type_icons = {
        "discovery": "🔍",
        "content": "📝",
        "publish": "📤",
        "report": "📊",
    }

    for task_type, type_tasks in task_types.items():
        icon = type_icons.get(task_type, "📌")
        st.markdown(f"### {icon} {task_type.capitalize()} Tasks")

        for task in type_tasks:
            task_id = task["id"]
            enabled = task.get("enabled", True)
            last_run = task.get("last_run")
            last_status = task.get("last_status", "never")
            run_count = task.get("run_count", 0)

            # Status indicator
            if not enabled:
                status_color = "#999999"
                status_icon = "⏸️"
            elif last_status == "success":
                status_color = "#4CAF50"
                status_icon = "✅"
            elif last_status == "failed":
                status_color = "#f44336"
                status_icon = "❌"
            else:
                status_color = "#2196F3"
                status_icon = "⏳"

            # Format last run time
            if last_run:
                try:
                    dt = datetime.fromisoformat(last_run)
                    last_run_str = dt.strftime("%m/%d %H:%M")
                except Exception:
                    last_run_str = last_run
            else:
                last_run_str = "Never"

            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                with col1:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="color: {status_color}; font-size: 18px;">{status_icon}</span>
                        <span style="font-weight: 500;">{task.get('name', task_id)}</span>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <span style="
                        background: #f0f0f0;
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-family: monospace;
                    ">{task.get('schedule', 'N/A')}</span>
                    """, unsafe_allow_html=True)

                with col3:
                    st.caption(f"Last: {last_run_str} ({run_count} runs)")

                with col4:
                    if st.button("▶️", key=f"run_{task_id}", help="Run now"):
                        selected_task = task_id

            st.divider()

    return selected_task


def render_next_runs(next_runs: List[Dict[str, Any]]) -> None:
    """
    Render upcoming scheduled runs.

    Args:
        next_runs: List of next run information
    """
    if not next_runs:
        st.info("No upcoming runs scheduled.")
        return

    st.markdown("### ⏰ Upcoming Runs")

    for run in next_runs[:5]:
        task_id = run.get("task_id", "unknown")
        next_run = run.get("next_run", "N/A")
        task_name = run.get("task_name", task_id)

        st.markdown(f"""
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: #f8f9fa;
            border-radius: 8px;
            margin-bottom: 8px;
        ">
            <span>{task_name}</span>
            <span style="
                background: #e3f2fd;
                color: #1976d2;
                padding: 4px 12px;
                border-radius: 16px;
                font-size: 12px;
            ">{next_run}</span>
        </div>
        """, unsafe_allow_html=True)


def render_task_stats(tasks: List[Dict[str, Any]]) -> None:
    """
    Render task statistics.

    Args:
        tasks: List of task dictionaries
    """
    total = len(tasks)
    enabled = sum(1 for t in tasks if t.get("enabled"))
    success = sum(1 for t in tasks if t.get("last_status") == "success")
    failed = sum(1 for t in tasks if t.get("last_status") == "failed")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Tasks", total)
    with col2:
        st.metric("Enabled", enabled)
    with col3:
        st.metric("Last Success", success)
    with col4:
        st.metric("Last Failed", failed)
