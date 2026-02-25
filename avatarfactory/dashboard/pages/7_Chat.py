"""
Chat Page - Interactive chat with AI assistant.

Provides a chat interface for interacting with the AvatarFactory AI,
with integrated Evolution suggestions management.
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

if "evolution_refresh" not in st.session_state:
    st.session_state.evolution_refresh = 0

# Track pending message to send (for quick commands)
if "pending_message" not in st.session_state:
    st.session_state.pending_message = None


def send_chat_message(message: str) -> str:
    """Send a message to the chat API and return the response."""
    try:
        with httpx.Client(timeout=180) as client:
            response = client.post(
                f"{api_url}/chat",
                json={
                    "message": message,
                    "persona_id": st.session_state.chat_persona_id
                }
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "No response")
            else:
                return f"Error: {response.status_code} - {response.text}"
    except httpx.TimeoutException:
        return "Request timed out. The operation may still be processing. Please check back later."
    except httpx.ConnectError:
        return "Connection error: Could not connect to API server. Please ensure the service is running."
    except Exception as e:
        return f"Error: {str(e)}"


def fetch_pending_suggestions(persona_id: str) -> list:
    """Fetch pending evolution suggestions for a persona."""
    if not persona_id:
        return []
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"{api_url}/personas/{persona_id}/evolution/suggestions",
                params={"status": "pending"}
            )
            if response.status_code == 200:
                return response.json().get("suggestions", [])
    except Exception:
        pass
    return []


def approve_suggestion(persona_id: str, suggestion_id: str) -> bool:
    """Approve an evolution suggestion."""
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{api_url}/personas/{persona_id}/evolution/suggestions/{suggestion_id}/review",
                json={"approved": True}
            )
            return response.status_code == 200
    except Exception:
        return False


def reject_suggestion(persona_id: str, suggestion_id: str, reason: str = None) -> bool:
    """Reject an evolution suggestion."""
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{api_url}/personas/{persona_id}/evolution/suggestions/{suggestion_id}/review",
                json={"approved": False, "rejection_reason": reason}
            )
            return response.status_code == 200
    except Exception:
        return False


def get_persona_version(persona_id: str) -> str:
    """Get current persona version."""
    if not persona_id:
        return ""
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{api_url}/personas/{persona_id}")
            if response.status_code == 200:
                return response.json().get("version", "")
    except Exception:
        pass
    return ""


# Sidebar - Persona selection and Evolution
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

    # Handle no personas case
    if not personas:
        st.warning("No personas found. Please create a persona first.")
        st.session_state.chat_persona_id = None
    else:
        # Build persona options without None option
        persona_options = {}
        for p in personas:
            persona_options[f"{p.get('name', 'Unknown')} ({p.get('id', '')[:12]}...)"] = p.get("id")

        # Get current selection index
        current_labels = list(persona_options.keys())
        current_index = 0
        if st.session_state.chat_persona_id:
            for i, pid in enumerate(persona_options.values()):
                if pid == st.session_state.chat_persona_id:
                    current_index = i
                    break

        selected_label = st.selectbox(
            "Active Persona",
            current_labels,
            index=current_index,
            key="chat_persona_select"
        )
        st.session_state.chat_persona_id = persona_options[selected_label]

    if st.button("🗑️ Clear Chat", key="clear_chat"):
        st.session_state.chat_messages = []
        st.rerun()

    # Evolution Section
    if st.session_state.chat_persona_id:
        st.divider()
        st.markdown("### 🔄 Evolution")

        # Show current version
        version = get_persona_version(st.session_state.chat_persona_id)
        if version:
            st.caption(f"Current version: **{version}**")

        # Fetch pending suggestions
        pending = fetch_pending_suggestions(st.session_state.chat_persona_id)

        if pending:
            st.warning(f"📋 **{len(pending)}** pending suggestion(s)")

            for idx, suggestion in enumerate(pending[:5]):  # Show max 5
                sug_id = suggestion.get("id", "")
                severity = suggestion.get("severity", "moderate")
                area = suggestion.get("area", "unknown")
                sug_text = suggestion.get("suggestion", "")
                confidence = suggestion.get("confidence", 0)

                # Severity badge color
                severity_colors = {
                    "minor": "🟢",
                    "moderate": "🟡",
                    "major": "🔴"
                }
                badge = severity_colors.get(severity, "⚪")

                with st.expander(f"{badge} [{severity}] {area}", expanded=(idx == 0)):
                    st.markdown(f"**{sug_text}**")

                    # Show rationale if available
                    rationale = suggestion.get("rationale", "")
                    if rationale:
                        st.caption(f"💡 {rationale}")

                    # Confidence bar
                    st.progress(confidence, text=f"Confidence: {confidence:.0%}")

                    # Action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Approve", key=f"approve_{sug_id}", use_container_width=True):
                            if approve_suggestion(st.session_state.chat_persona_id, sug_id):
                                st.success("Applied!")
                                st.session_state.evolution_refresh += 1
                                st.rerun()
                            else:
                                st.error("Failed")
                    with col2:
                        if st.button("❌ Reject", key=f"reject_{sug_id}", use_container_width=True):
                            if reject_suggestion(st.session_state.chat_persona_id, sug_id):
                                st.info("Rejected")
                                st.session_state.evolution_refresh += 1
                                st.rerun()
                            else:
                                st.error("Failed")

            if len(pending) > 5:
                st.caption(f"... and {len(pending) - 5} more")

        else:
            st.success("✨ No pending suggestions")

        # Quick evolution actions
        st.caption("Quick Actions")
        if st.button("🔍 Analyze Feedback", key="analyze_feedback", use_container_width=True):
            with st.spinner("Analyzing..."):
                try:
                    with httpx.Client(timeout=60) as client:
                        response = client.post(
                            f"{api_url}/personas/{st.session_state.chat_persona_id}/evolution/analyze",
                            params={"period": "7d"}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            count = data.get("suggestions_count", 0)
                            st.success(f"Generated {count} suggestion(s)")
                            st.session_state.evolution_refresh += 1
                            st.rerun()
                        else:
                            st.error("Analysis failed")
                except Exception as e:
                    st.error(f"Error: {e}")


# Display chat messages
for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Quick actions - only show when persona is selected
if st.session_state.chat_persona_id:
    st.markdown("##### Quick Commands")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📝 Generate", key="quick_generate", use_container_width=True):
            st.session_state.pending_message = "Generate content for my persona"

    with col2:
        if st.button("🔍 Trends", key="quick_discover", use_container_width=True):
            st.session_state.pending_message = "Discover trending topics"

    with col3:
        if st.button("📊 Stats", key="quick_stats", use_container_width=True):
            st.session_state.pending_message = "Show my content statistics"

    with col4:
        if st.button("🔄 Evolve", key="quick_suggestions", use_container_width=True):
            st.session_state.pending_message = "Show pending evolution suggestions"

# Process pending message from quick commands
if st.session_state.pending_message:
    pending_msg = st.session_state.pending_message
    st.session_state.pending_message = None

    # Add user message to history
    st.session_state.chat_messages.append({"role": "user", "content": pending_msg})

    # Display user message
    with st.chat_message("user"):
        st.markdown(pending_msg)

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            assistant_message = send_chat_message(pending_msg)

        st.markdown(assistant_message)
        st.session_state.chat_messages.append({"role": "assistant", "content": assistant_message})

# Chat input (fixed at bottom by Streamlit)
if not st.session_state.chat_persona_id:
    st.info("Please create a persona first to start chatting.")
elif prompt := st.chat_input("Type your message..."):
    # Add user message to history
    st.session_state.chat_messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            assistant_message = send_chat_message(prompt)

        st.markdown(assistant_message)
        st.session_state.chat_messages.append({"role": "assistant", "content": assistant_message})

    # Check if evolution suggestions were generated (refresh sidebar)
    if any(keyword in prompt.lower() for keyword in ["更", "改", "调整", "优化", "casual", "formal", "shorter", "longer"]):
        st.session_state.evolution_refresh += 1
