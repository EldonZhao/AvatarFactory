"""
Scheduler Page - Monitor and manage scheduled tasks.

Displays scheduled tasks, their status, and execution history.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import streamlit as st
import httpx

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
api_url = os.getenv("AVATARFACTORY_SERVICE_URL", "http://localhost:8000")
provider = DashboardDataProvider(kb_path)

# Get personas for task creation
personas_list = provider.get_personas()

# Sidebar
with st.sidebar:
    st.markdown("### Create Task")

    with st.expander("➕ New Task", expanded=False):
        if personas_list:
            persona_opts = {}
            for p in personas_list:
                persona_opts[f"{p.name} ({p.id[:12]}...)"] = p.id

            task_persona_label = st.selectbox(
                "Persona",
                list(persona_opts.keys()),
                key="task_persona_select"
            )
            task_persona_id = persona_opts[task_persona_label]

            task_type = st.selectbox(
                "Task Type",
                ["discovery", "content_generation"],
                key="task_type_select"
            )

            task_schedule = st.selectbox(
                "Schedule",
                ["0 */3 * * *", "0 9 * * *", "0 9,18 * * *", "0 * * * *"],
                format_func=lambda x: {
                    "0 */3 * * *": "Every 3 hours",
                    "0 9 * * *": "Daily at 9am",
                    "0 9,18 * * *": "Twice daily (9am, 6pm)",
                    "0 * * * *": "Every hour"
                }.get(x, x),
                key="task_schedule_select"
            )

            task_platform = st.selectbox(
                "Platform",
                ["bluesky", "xiaohongshu", "twitter"],
                key="task_platform_select"
            )

            if st.button("Create Task", key="create_task_btn", type="primary"):
                with st.spinner("Creating task..."):
                    try:
                        with httpx.Client(timeout=30) as client:
                            response = client.post(
                                f"{api_url}/scheduler/tasks",
                                json={
                                    "persona_id": task_persona_id,
                                    "task_type": task_type,
                                    "schedule": task_schedule,
                                    "platform": task_platform,
                                    "enabled": True
                                }
                            )
                            if response.status_code == 200:
                                st.success("Task created!")
                                st.rerun()
                            else:
                                st.error(f"Error: {response.status_code}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        else:
            st.info("Create a persona first")

    st.markdown("---")
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
