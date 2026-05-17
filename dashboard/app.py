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

from dashboard.components.brand import inject, sidebar_logo, theme_toggle, PRIMARY, get_theme_vars
inject()
theme_toggle()  # available on all pages including login

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not st.session_state.get("jwt_token"):
    from dashboard.components.login_form import render_login
    render_login()
    st.stop()

# ── Force password change gate ────────────────────────────────────────────────
if st.session_state.get("must_change_password"):
    from dashboard.components.login_form import render_change_password
    render_change_password()
    st.stop()

import os
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

API_BASE = "http://localhost:5000/api/v1"


def _get_headers() -> dict:
    token = st.session_state.get("jwt_token", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    # Fallback for dev/script access (no JWT in session)
    key = os.environ.get("CLAUDEOS_DEV_API_KEY", "")
    return {"X-API-Key": key} if key else {}


def _maybe_refresh_token() -> None:
    """Silently refresh the access token if it expires within 5 minutes."""
    import time as _time
    token = st.session_state.get("jwt_token", "")
    refresh = st.session_state.get("refresh_token", "")
    if not token or not refresh:
        return
    try:
        import jwt as _jwt
        payload = _jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp", 0)
        if exp - _time.time() < 300:  # < 5 minutes
            r = requests.post(
                f"{API_BASE}/auth/refresh",
                json={"refresh_token": refresh},
                timeout=3,
            )
            if r.ok:
                st.session_state["jwt_token"] = r.json()["access_token"]
    except Exception:
        pass


_maybe_refresh_token()


def _handle_401() -> None:
    st.session_state.clear()
    st.rerun()


def api_get(path: str, timeout: int = 3) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}{path}", headers=_get_headers(), timeout=timeout)
        if r.status_code == 401:
            _handle_401()
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
        r = fn(f"{API_BASE}{path}", json=data, headers=_get_headers(), timeout=timeout)
        if r.status_code == 401:
            _handle_401()
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


# ── Sidebar ───────────────────────────────────────────────────────────────────
sidebar_logo()
st.sidebar.markdown("---")

role = st.session_state.get("user_role", "viewer")
username = st.session_state.get("username", "")

# Role-based page visibility
pages = {
    "Overview":  "🖥️",
    "Agents":    "🤖",
    "Memory":    "🧠",
    "Workflows": "⚙️",
    "Projects":  "📁",
    "Outputs":   "📄",
    "Settings":  "🔧",
}

if role == "admin":
    pages["Admin"] = "🛡️"

if role in ("client", "viewer"):
    pages.pop("Settings", None)
    pages.pop("Workflows", None)

page = st.sidebar.radio(
    "Navigation",
    list(pages.keys()),
    format_func=lambda p: f"{pages[p]}  {p}",
    label_visibility="collapsed",
)

st.sidebar.markdown("---")

# User info + logout
_tv = get_theme_vars()
st.sidebar.markdown(
    f'<div style="font-size:0.8rem;margin-bottom:4px;color:{_tv["TEXT"]};">'
    f'<strong style="color:{_tv["TEXT"]};">{username}</strong>'
    f' <span style="color:{_tv["TEXT_MUTED"]};">({role})</span></div>',
    unsafe_allow_html=True,
)
if st.sidebar.button("Logout", use_container_width=True):
    try:
        requests.post(
            f"{API_BASE}/auth/logout",
            json={"refresh_token": st.session_state.get("refresh_token", "")},
            headers=_get_headers(),
            timeout=3,
        )
    except Exception:
        pass
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")

health = api_get_cached("/health")
if health and health.get("status") == "ok":
    st.sidebar.markdown(f'<div style="color:#5a9e56;font-size:0.8rem;">● API online · v{health.get("version","?")}</div>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<div style="color:#ef4444;font-size:0.8rem;">● API offline</div>', unsafe_allow_html=True)

st.sidebar.markdown(f'<div style="color:{_tv["TEXT_MUTED"]};font-size:0.75rem;margin-top:4px;">{datetime.now().strftime("%a %d %b · %H:%M")}</div>', unsafe_allow_html=True)

# ── Page dispatch ─────────────────────────────────────────────────────────────
from dashboard._pages._overview  import render as _render_overview
from dashboard._pages._agents    import render as _render_agents
from dashboard._pages._memory    import render as _render_memory
from dashboard._pages._workflows import render as _render_workflows
from dashboard._pages._projects  import render as _render_projects
from dashboard._pages._outputs   import render as _render_outputs
from dashboard._pages._settings  import render as _render_settings
from dashboard._pages._admin     import render as _render_admin

_PAGE_DISPATCH = {
    "Overview":  (_render_overview,  api_get_cached),
    "Agents":    (_render_agents,    api_get),
    "Memory":    (_render_memory,    api_get),
    "Workflows": (_render_workflows, api_get),
    "Projects":  (_render_projects,  api_get),
    "Outputs":   (_render_outputs,   api_get_cached),
    "Settings":  (_render_settings,  api_get),
    "Admin":     (_render_admin,     api_get),
}

_render_fn, _getter = _PAGE_DISPATCH[page]
_render_fn(_getter, api_post)
