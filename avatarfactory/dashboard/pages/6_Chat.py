"""
Chat Page - Interactive chat with AI assistant.

Provides a chat interface for interacting with the AvatarFactory AI.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import streamlit as st
import httpx

st.set_page_config(
    page_title="Chat - AvatarFactory",
    page_icon="💬",
    layout="wide",
)

st.title("💬 Chat")
st.markdown("Chat with the AvatarFactory AI assistant.")

# Get API URL
api_url = os.getenv("AVATARFACTORY_SERVICE_URL", "http://localhost:8000")

# Initialize chat history
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "chat_persona_id" not in st.session_state:
    st.session_state.chat_persona_id = None

# Sidebar - Persona selection
with st.sidebar:
    st.markdown("### Settings")

    # Fetch personas for selection
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{api_url}/personas")
            if response.status_code == 200:
                personas_data = response.json()
                personas = personas_data.get("personas", [])
            else:
                personas = []
    except Exception:
        personas = []

    persona_options = {"None (General)": None}
    for p in personas:
        persona_options[f"{p.get('name', 'Unknown')} ({p.get('id', '')[:12]}...)"] = p.get("id")

    selected_label = st.selectbox(
        "Active Persona",
        list(persona_options.keys()),
        key="chat_persona_select"
    )
    st.session_state.chat_persona_id = persona_options[selected_label]

    if st.button("🗑️ Clear Chat", key="clear_chat"):
        st.session_state.chat_messages = []
        st.rerun()

# Display chat messages
for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message..."):
    # Add user message to history
    st.session_state.chat_messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                with httpx.Client(timeout=60) as client:
                    response = client.post(
                        f"{api_url}/chat",
                        json={
                            "message": prompt,
                            "persona_id": st.session_state.chat_persona_id
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        assistant_message = data.get("response", "No response")
                    else:
                        assistant_message = f"Error: {response.status_code} - {response.text}"
            except Exception as e:
                assistant_message = f"Connection error: {str(e)}"

        st.markdown(assistant_message)
        st.session_state.chat_messages.append({"role": "assistant", "content": assistant_message})

# Quick actions
st.divider()
st.markdown("### Quick Commands")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📝 Generate Content", key="quick_generate"):
        st.session_state.chat_messages.append({"role": "user", "content": "Generate content for my persona"})
        st.rerun()

with col2:
    if st.button("🔍 Discover Trends", key="quick_discover"):
        st.session_state.chat_messages.append({"role": "user", "content": "Discover trending topics"})
        st.rerun()

with col3:
    if st.button("📊 Show Stats", key="quick_stats"):
        st.session_state.chat_messages.append({"role": "user", "content": "Show my content statistics"})
        st.rerun()
