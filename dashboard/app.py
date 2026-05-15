"""ClaudeOS Control Center — Streamlit entry point."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="ClaudeOS",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from dashboard.components.brand import inject, sidebar_logo, theme_toggle, PRIMARY, TEXT_MUTED
inject()

import os
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

API_BASE = "http://localhost:5000/api/v1"
_API_KEY = os.environ.get("CLAUDEOS_DEV_API_KEY", "")
_HEADERS = {"X-API-Key": _API_KEY} if _API_KEY else {}


def api_get(path: str, timeout: int = 3) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}{path}", headers=_HEADERS, timeout=timeout)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


_READ_ONLY_PREFIXES = (
    "/health",
    "/system/status",
    "/system/stats",
    "/agents",
    "/agents/runs",
    "/memory/namespaces",
)


@st.cache_data(ttl=30)
def _cached_api_get(path: str, timeout: int = 3) -> dict | None:
    return api_get(path, timeout=timeout)


def api_get_cached(path: str, timeout: int = 3) -> dict | None:
    """api_get with 30-second cache for known read-only endpoints."""
    if any(path == p or path.startswith(p) for p in _READ_ONLY_PREFIXES):
        return _cached_api_get(path, timeout)
    return api_get(path, timeout)


def api_post(path: str, data: dict, timeout: int = 5, method: str = "POST") -> dict | None:
    try:
        fn = {"POST": requests.post, "PATCH": requests.patch, "PUT": requests.put}.get(method, requests.post)
        r = fn(f"{API_BASE}{path}", json=data, headers=_HEADERS, timeout=timeout)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


# Sidebar
sidebar_logo()
st.sidebar.markdown("---")

pages = {
    "Overview": "🖥️",
    "Agents": "🤖",
    "Memory": "🧠",
    "Workflows": "⚙️",
    "Projects": "📁",
    "Outputs": "📄",
    "Settings": "🔧",
}

page = st.sidebar.radio(
    "Navigation",
    list(pages.keys()),
    format_func=lambda p: f"{pages[p]}  {p}",
    label_visibility="collapsed",
)

theme_toggle()
st.sidebar.markdown("---")

health = api_get_cached("/health")
if health and health.get("status") == "ok":
    st.sidebar.markdown(f'<div style="color:#5a9e56;font-size:0.8rem;">● API online · v{health.get("version","?")}</div>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<div style="color:#ef4444;font-size:0.8rem;">● API offline</div>', unsafe_allow_html=True)

st.sidebar.markdown(f'<div style="color:{TEXT_MUTED};font-size:0.75rem;margin-top:4px;">{datetime.now().strftime("%a %d %b · %H:%M")}</div>', unsafe_allow_html=True)

# ─── Route to pages ─────────────────────────────────────────────────────────

if page == "Overview":
    from dashboard._pages._overview import render
    render(api_get_cached, api_post)
elif page == "Agents":
    from dashboard._pages._agents import render
    render(api_get, api_post)
elif page == "Memory":
    from dashboard._pages._memory import render
    render(api_get, api_post)
elif page == "Workflows":
    from dashboard._pages._workflows import render
    render(api_get, api_post)
elif page == "Projects":
    from dashboard._pages._projects import render
    render(api_get, api_post)
elif page == "Outputs":
    from dashboard._pages._outputs import render
    render(api_get, api_post)
elif page == "Settings":
    from dashboard._pages._settings import render
    render(api_get, api_post)
