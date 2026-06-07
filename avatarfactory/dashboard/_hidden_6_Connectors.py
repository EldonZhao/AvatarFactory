"""
Connectors Page - Platform connector status and configuration.

Displays the status of all platform connectors and their configuration.
"""

import os
import sys

import streamlit as st
from dotenv import load_dotenv

from avatarfactory.dashboard.data import DashboardDataProvider

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

# Load environment variables from .env file
load_dotenv()

st.set_page_config(
    page_title="Connectors - AvatarFactory",
    page_icon="🔌",
    layout="wide",
)

st.title("🔌 Platform Connectors")
st.markdown("View connector status and configuration requirements.")

# Initialize provider
kb_path = os.getenv("AVATARFACTORY_KB_PATH", "./knowledges")
provider = DashboardDataProvider(kb_path)

# Sidebar
with st.sidebar:
    st.markdown("### Actions")

    st.info("**Test connection:**\n" "```bash\n" "avatarfactory connect bluesky\n" "```")

    st.info("**Fetch trending:**\n" "```bash\n" 'avatarfactory fetch bluesky -q "AI tools"\n' "```")

    if st.button("🔄 Refresh"):
        st.rerun()

# Get connector statuses
connectors = provider.get_connector_statuses()

# Sort: configured first, then unconfigured
connectors = sorted(connectors, key=lambda c: (not c.configured, c.platform))

# Stats
configured = sum(1 for c in connectors if c.configured)
col1, col2 = st.columns(2)
with col1:
    st.metric("Configured", f"{configured}/{len(connectors)}")
with col2:
    st.metric("Total Connectors", len(connectors))

st.divider()

# Platform configurations
platform_info = {
    "bluesky": {
        "name": "Bluesky",
        "icon": "🦋",
        "description": "AT Protocol social network",
        "env_vars": {
            "BLUESKY_USERNAME": "Your Bluesky handle (e.g., user.bsky.social)",
            "BLUESKY_PASSWORD": "Your app password (not main password)",
        },
        "docs_url": "https://bsky.app/settings/app-passwords",
    },
    "twitter": {
        "name": "Twitter/X",
        "icon": "𝕏",
        "description": "Twitter API v2",
        "env_vars": {
            "TWITTER_API_KEY": "API Key from developer portal",
            "TWITTER_API_SECRET": "API Secret from developer portal",
            "TWITTER_ACCESS_TOKEN": "Access token for your account",
        },
        "docs_url": "https://developer.twitter.com/en/portal/dashboard",
    },
    "xiaohongshu": {
        "name": "Xiaohongshu",
        "icon": "📕",
        "description": "Little Red Book (小红书)",
        "env_vars": {
            "XIAOHONGSHU_COOKIE": "Browser cookie from logged-in session",
        },
        "docs_url": None,
    },
    "wecom": {
        "name": "WeChat Work",
        "icon": "💬",
        "description": "Enterprise WeChat webhook notifications (system-level config)",
        "env_vars": {
            "AVATARFACTORY_WEBHOOK_URL": "Webhook robot URL (system-level, shared by all personas)",
        },
        "docs_url": "https://developer.work.weixin.qq.com/document/path/91770",
    },
    "linkedin": {
        "name": "LinkedIn",
        "icon": "💼",
        "description": "LinkedIn OAuth 2.0 for professional content",
        "env_vars": {
            "LINKEDIN_ACCESS_TOKEN": "OAuth 2.0 access token",
            "LINKEDIN_CLIENT_ID": "Client ID from developer portal (optional)",
            "LINKEDIN_CLIENT_SECRET": "Client Secret (optional)",
            "LINKEDIN_ORGANIZATION_ID": "Organization ID for company pages (optional)",
        },
        "docs_url": "https://www.linkedin.com/developers/apps",
    },
    "threads": {
        "name": "Threads",
        "icon": "🧵",
        "description": "Threads (Meta) Graph API",
        "env_vars": {
            "THREADS_ACCESS_TOKEN": "Access token from Meta developer portal",
            "THREADS_USER_ID": "Your Threads user ID",
        },
        "docs_url": "https://developers.facebook.com/docs/threads",
    },
    "instagram": {
        "name": "Instagram",
        "icon": "📸",
        "description": "Instagram Business Graph API",
        "env_vars": {
            "INSTAGRAM_ACCESS_TOKEN": "Access token from Meta developer portal",
            "INSTAGRAM_BUSINESS_ACCOUNT_ID": "Instagram Business Account ID",
        },
        "docs_url": "https://developers.facebook.com/docs/instagram-api",
    },
    "weibo": {
        "name": "Weibo",
        "icon": "🔴",
        "description": "Weibo (微博) OAuth 2.0",
        "env_vars": {
            "WEIBO_ACCESS_TOKEN": "OAuth 2.0 access token",
            "WEIBO_UID": "Your Weibo user ID",
            "WEIBO_APP_KEY": "App key (optional)",
        },
        "docs_url": "https://open.weibo.com/",
    },
    "mastodon": {
        "name": "Mastodon",
        "icon": "🐘",
        "description": "Mastodon/Fediverse - Works with any instance",
        "env_vars": {
            "MASTODON_ACCESS_TOKEN": "Access token from your instance settings",
            "MASTODON_INSTANCE_URL": "Your instance URL (e.g., https://mastodon.social)",
        },
        "docs_url": "https://docs.joinmastodon.org/client/token/",
    },
    "toutiao": {
        "name": "Toutiao",
        "icon": "📰",
        "description": "今日头条/头条号 - Bytedance content platform",
        "env_vars": {
            "TOUTIAO_ACCESS_TOKEN": "OAuth 2.0 access token from Toutiao Open Platform",
        },
        "docs_url": "https://open.mp.toutiao.com/",
    },
}

# Display connector cards
for connector in connectors:
    platform = connector.platform
    info = platform_info.get(platform, {})

    with st.container():
        col1, col2, col3 = st.columns([1, 3, 2])

        with col1:
            icon = info.get("icon", "📱")
            status_color = "#4CAF50" if connector.configured else "#ff9800"
            status_icon = "✅" if connector.configured else "⚠️"

            st.markdown(
                f"""
            <div style="
                text-align: center;
                padding: 20px;
                background: white;
                border-radius: 12px;
                border-left: 4px solid {status_color};
            ">
                <div style="font-size: 48px;">{icon}</div>
                <div style="font-size: 24px; margin-top: 8px;">{status_icon}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(f"### {info.get('name', platform.capitalize())}")
            st.caption(info.get("description", "Platform connector"))

            if connector.configured:
                st.success("✅ Configured and ready")
            else:
                st.warning("⚠️ Not configured")
                st.markdown("**Missing environment variables:**")
                for key in connector.config_keys:
                    desc = info.get("env_vars", {}).get(key, "Required")
                    st.code(f"{key}={desc}")

        with col3:
            st.markdown("#### Quick Actions")

            if connector.configured:
                st.code(f"avatarfactory connect {platform}", language="bash")
                st.code(f"avatarfactory fetch {platform}", language="bash")
            else:
                if info.get("docs_url"):
                    st.markdown(f"[📖 Documentation]({info['docs_url']})")

                st.markdown("**Add to .env:**")
                for key in info.get("env_vars", {}).keys():
                    st.code(f"{key}=your_value")

        st.divider()

# Configuration help
st.markdown("---")
st.markdown("### 📖 Configuration Guide")

with st.expander("How to configure connectors"):
    st.markdown("""
    1. **Create a `.env` file** in your project root (or use environment variables)

    2. **Add the required credentials** for each platform you want to use

    3. **Test the connection:**
       ```bash
       avatarfactory connect <platform>
       ```

    4. **Fetch content:**
       ```bash
       avatarfactory fetch <platform> --query "your topic"
       ```

    **Example .env file:**
    ```
    # Bluesky
    BLUESKY_USERNAME=your.handle.bsky.social
    BLUESKY_PASSWORD=your-app-password

    # Twitter
    TWITTER_API_KEY=your_api_key
    TWITTER_API_SECRET=your_api_secret
    TWITTER_ACCESS_TOKEN=your_access_token

    # LinkedIn
    LINKEDIN_ACCESS_TOKEN=your_access_token

    # Threads
    THREADS_ACCESS_TOKEN=your_access_token
    THREADS_USER_ID=your_user_id

    # Instagram
    INSTAGRAM_ACCESS_TOKEN=your_access_token
    INSTAGRAM_BUSINESS_ACCOUNT_ID=your_account_id

    # Weibo
    WEIBO_ACCESS_TOKEN=your_access_token
    WEIBO_UID=your_user_id

    # Mastodon
    MASTODON_ACCESS_TOKEN=your_access_token
    MASTODON_INSTANCE_URL=https://mastodon.social

    # Notifications (system-level, shared by all personas)
    AVATARFACTORY_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
    ```
    """)
