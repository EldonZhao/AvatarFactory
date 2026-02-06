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

    with st.expander("➕ Setup Tasks for Persona", expanded=False):
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

            task_platforms = st.multiselect(
                "Platforms",
                ["bluesky", "xiaohongshu", "twitter"],
                default=["bluesky"],
                key="task_platforms_select"
            )

            st.markdown("**Schedule Settings**")

            # Discovery schedule options
            discovery_schedule_opts = {
                "Every 6 hours": "0 */6 * * *",
                "Every 12 hours": "0 */12 * * *",
                "Daily at 9 AM": "0 9 * * *",
                "Twice daily (9 AM, 6 PM)": "0 9,18 * * *",
            }
            discovery_schedule_label = st.selectbox(
                "Discovery Schedule",
                list(discovery_schedule_opts.keys()),
                key="discovery_schedule_select",
                help="How often to scan for trending topics"
            )
            discovery_schedule = discovery_schedule_opts[discovery_schedule_label]

            # Content generation schedule options
            content_schedule_opts = {
                "Daily at 10 AM": "0 10 * * *",
                "Daily at 9 AM": "0 9 * * *",
                "Twice daily (10 AM, 4 PM)": "0 10,16 * * *",
                "Every 8 hours": "0 */8 * * *",
            }
            content_schedule_label = st.selectbox(
                "Content Generation Schedule",
                list(content_schedule_opts.keys()),
                key="content_schedule_select",
                help="When to generate content suggestions"
            )
            content_schedule = content_schedule_opts[content_schedule_label]

            st.caption("This will create discovery and content generation tasks for the selected platforms.")

            if st.button("Setup Tasks", key="create_task_btn", type="primary"):
                if task_platforms:
                    with st.spinner("Setting up tasks..."):
                        try:
                            with httpx.Client(timeout=30) as client:
                                response = client.post(
                                    f"{api_url}/scheduler/tasks/{task_persona_id}/setup",
                                    json={
                                        "platforms": task_platforms,
                                        "discovery_schedule": discovery_schedule,
                                        "content_schedule": content_schedule,
                                    }
                                )
                                if response.status_code == 200:
                                    data = response.json()
                                    st.success(f"Created {data.get('tasks_created', 0)} task(s)!")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {response.status_code} - {response.text}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                else:
                    st.warning("Please select at least one platform")
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
