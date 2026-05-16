"""ClaudeOS Control Center — Streamlit entry point."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="ClaudeOS",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="auto",
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
    "/system/events",
    "/agents",
    "/agents/runs",
    "/memory/namespaces",
    "/outputs/stats",
    "/namespaces",
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

# ─── Page dispatch (imports at module level — not per-render) ────────────────
from dashboard._pages._overview  import render as _render_overview
from dashboard._pages._agents    import render as _render_agents
from dashboard._pages._memory    import render as _render_memory
from dashboard._pages._workflows import render as _render_workflows
from dashboard._pages._projects  import render as _render_projects
from dashboard._pages._outputs   import render as _render_outputs
from dashboard._pages._settings  import render as _render_settings

_PAGE_DISPATCH = {
    "Overview":  (_render_overview,  api_get_cached),
    "Agents":    (_render_agents,    api_get),
    "Memory":    (_render_memory,    api_get),
    "Workflows": (_render_workflows, api_get),
    "Projects":  (_render_projects,  api_get),
    "Outputs":   (_render_outputs,   api_get_cached),
    "Settings":  (_render_settings,  api_get),
}

_render_fn, _getter = _PAGE_DISPATCH[page]
_render_fn(_getter, api_post)
