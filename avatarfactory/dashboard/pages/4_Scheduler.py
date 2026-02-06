"""
Scheduler Page - Monitor and manage scheduled tasks.

Displays scheduled tasks, their status, and execution history.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import streamlit as st

from avatarfactory.dashboard.data import DashboardDataProvider
from avatarfactory.dashboard.components.task_timeline import (
    render_task_timeline,
    render_next_runs,
    render_task_stats,
)

st.set_page_config(
    page_title="Scheduler - AvatarFactory",
    page_icon="⏰",
    layout="wide",
)

st.title("⏰ Task Scheduler")
st.markdown("Monitor scheduled tasks and their execution status.")

# Initialize provider
kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
provider = DashboardDataProvider(kb_path)

# Sidebar
with st.sidebar:
    st.markdown("### Actions")

    st.info(
        "**Start scheduler daemon:**\n"
        "```bash\n"
        "avatarfactory daemon start\n"
        "```"
    )

    st.info(
        "**Add a task:**\n"
        "```bash\n"
        "avatarfactory schedule add --type discovery --persona <id>\n"
        "```"
    )

    st.markdown("### Filters")
    show_disabled = st.checkbox("Show disabled tasks", value=True)

    if st.button("🔄 Refresh"):
        st.rerun()

# Get task data
tasks = provider.get_scheduled_tasks()
next_runs = provider.get_next_runs()

# Stats
render_task_stats(tasks)

st.divider()

# Two-column layout
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("### 📋 Scheduled Tasks")

    selected_task = render_task_timeline(tasks, show_disabled=show_disabled)

    if selected_task:
        st.info(
            f"**To run task manually:**\n"
            f"```bash\n"
            f"avatarfactory schedule run --id {selected_task}\n"
            f"```"
        )

with col_right:
    render_next_runs(next_runs)

    st.markdown("---")

    st.markdown("### 📊 Quick Stats")

    # Task type breakdown
    type_counts = {}
    for task in tasks:
        task_type = task.get("task_type", "unknown")
        type_counts[task_type] = type_counts.get(task_type, 0) + 1

    if type_counts:
        for task_type, count in sorted(type_counts.items()):
            st.markdown(f"**{task_type.capitalize()}:** {count}")

    st.markdown("---")

    st.markdown("### 🔧 CLI Commands")

    st.markdown("**List tasks:**")
    st.code("avatarfactory schedule list", language="bash")

    st.markdown("**Check daemon status:**")
    st.code("avatarfactory daemon status", language="bash")

    st.markdown("**View publish queue:**")
    st.code("avatarfactory queue list", language="bash")
