"""ClaudeOS Control Center — Streamlit entry point."""
import sys
import os
import logging
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")

import jwt as _jwt
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

_FLASK_PORT = os.environ.get("FLASK_PORT", "5000")
API_BASE = f"http://localhost:{_FLASK_PORT}/api/v1"
logger = logging.getLogger("claudeos.dashboard")

_SESSION_PARAM = "_s"  # URL query param key for session persistence


def _restore_session_from_url() -> bool:
    """On page refresh, restore session from URL session_key → Flask session store."""
    sk = st.query_params.get(_SESSION_PARAM)
    if not sk:
        return False
    try:
        r = requests.get(f"{API_BASE}/auth/session/{sk}", timeout=3)
        if r.ok:
            data = r.json()
            st.session_state["jwt_token"]            = data["access_token"]
            st.session_state["refresh_token"]        = data["refresh_token"]
            st.session_state["username"]             = data["username"]
            st.session_state["user_role"]            = data["user_role"]
            st.session_state["user_namespace"]       = data.get("user_namespace") or None
            st.session_state["must_change_password"] = data.get("must_change_password", False)
            return True
        # Expired / invalid key — purge from URL so login page shows cleanly
        try:
            del st.query_params[_SESSION_PARAM]
        except Exception:
            pass
    except Exception as e:
        logger.debug("Session restore failed: %s", e)
    return False


# ── Session restore (page refresh) ───────────────────────────────────────────
if not st.session_state.get("jwt_token"):
    _restore_session_from_url()

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

def _get_headers() -> dict:
    token = st.session_state.get("jwt_token", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    # Fallback for dev/script access (no JWT in session)
    key = os.environ.get("CLAUDEOS_DEV_API_KEY", "")
    return {"X-API-Key": key} if key else {}


def _maybe_refresh_token() -> None:
    """Silently refresh the access token if it expires within 5 minutes.
    Throttled to run at most once per 60 seconds to avoid JWT decode on every rerender.
    """
    import time as _time
    now = _time.time()
    if now - st.session_state.get("_refresh_checked_at", 0) < 60:
        return
    st.session_state["_refresh_checked_at"] = now

    token = st.session_state.get("jwt_token", "")
    refresh = st.session_state.get("refresh_token", "")
    if not token or not refresh:
        return
    try:
        payload = _jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp", 0)
        if exp - now < 300:  # < 5 minutes to expiry
            r = requests.post(
                f"{API_BASE}/auth/refresh",
                json={"refresh_token": refresh},
                timeout=3,
            )
            if r.ok:
                st.session_state["jwt_token"] = r.json()["access_token"]
    except Exception as e:
        logger.debug("Token refresh skipped: %s", e)


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
    except Exception as e:
        logger.warning("api_get %s failed: %s", path, e)
    return None


_READ_ONLY_PREFIXES = (
    "/health",
    "/system/status",
    "/system/stats",
    "/system/events",
    "/agents",
    "/memory/namespaces",
    "/outputs/stats",
    "/namespaces",
)
# NOTE: /agents/runs intentionally excluded — user-scoped, must never be cached cross-user


@st.cache_data(ttl=30)
def _cached_api_get(path: str, token: str = "", timeout: int = 3) -> dict | None:
    return api_get(path, timeout=timeout)


def api_get_cached(path: str, timeout: int = 3) -> dict | None:
    """api_get with 30-second TTL cache scoped per user token.
    /agents/runs is explicitly excluded — user-scoped data must not be cached cross-user.
    """
    base = path.split("?")[0]
    if base == "/agents/runs" or base.startswith("/agents/runs/"):
        return api_get(path, timeout)
    if any(path == p or path.startswith(p) for p in _READ_ONLY_PREFIXES):
        tok = st.session_state.get("jwt_token", "")
        return _cached_api_get(path, token=tok, timeout=timeout)
    return api_get(path, timeout)


def bulk_delete(path: str, ids: list, timeout: int = 10) -> dict | None:
    """DELETE with JSON body {"ids": [...]} for bulk endpoints."""
    try:
        r = requests.delete(
            f"{API_BASE}{path}",
            json={"ids": ids},
            headers=_get_headers(),
            timeout=timeout,
        )
        if r.status_code == 401:
            _handle_401()
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def api_post(path: str, data: dict, timeout: int = 5, method: str = "POST") -> dict | None:
    try:
        fn = {"POST": requests.post, "PATCH": requests.patch, "PUT": requests.put}.get(method, requests.post)
        r = fn(f"{API_BASE}{path}", json=data, headers=_get_headers(), timeout=timeout)
        if r.status_code == 401:
            _handle_401()
        if r.ok:
            return r.json()
    except Exception as e:
        logger.warning("api_post %s failed: %s", path, e)
    return None


# ── Sidebar ───────────────────────────────────────────────────────────────────
sidebar_logo()
st.sidebar.markdown("---")

role = st.session_state.get("user_role", "viewer")
username = st.session_state.get("username", "")

# Role-based page visibility
pages = {
    "Overview":       "🖥️",
    "Agents":         "🤖",
    "Memory":         "🧠",
    "Workflows":      "⚙️",
    "Projects":       "📁",
    "Outputs":        "📄",
    "Tickets":        "🎫",
    "Observability":  "🔭",
    "Settings":       "🔧",
}

if role == "admin":
    pages["Admin"] = "🛡️"

if role in ("client", "viewer"):
    pages.pop("Settings", None)
    pages.pop("Workflows", None)
    pages.pop("Observability", None)

if role == "staff":
    pages.pop("Memory", None)
    pages.pop("Workflows", None)
    pages.pop("Projects", None)
    pages.pop("Settings", None)
    pages.pop("Admin", None)
    pages.pop("Observability", None)

# Ticket badge — fetch before radio so count shows in nav label (cached 30s)
_ticket_stats = _cached_api_get(
    "/tickets?status=open&limit=1",
    token=st.session_state.get("jwt_token", ""),
    timeout=3,
)
_open_ticket_count = (_ticket_stats.get("count", 0) if isinstance(_ticket_stats, dict) else 0)

_page_list = list(pages.keys())
_saved_page = st.session_state.get("nav_page")
_page_index = _page_list.index(_saved_page) if _saved_page in _page_list else 0
page = st.sidebar.radio(
    "Navigation",
    _page_list,
    index=_page_index,
    key="nav_page",
    format_func=lambda p: (
        f"{pages[p]}  {p} ({_open_ticket_count})" if p == "Tickets" and _open_ticket_count
        else f"{pages[p]}  {p}"
    ),
    label_visibility="collapsed",
)

st.sidebar.markdown("---")

# User info + logout
_tv = get_theme_vars()
_user_ns = st.session_state.get("user_namespace")
st.sidebar.markdown(f"**{username}** ({role})")
if _user_ns and role in ("client", "viewer"):
    st.sidebar.markdown(
        f'<div style="font-size:0.78rem;color:{PRIMARY};margin:-6px 0 4px;">🏢 {_user_ns}</div>',
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
    # Delete server-side session so the URL key becomes invalid
    _sk = st.query_params.get(_SESSION_PARAM)
    if _sk:
        try:
            requests.delete(f"{API_BASE}/auth/session/{_sk}", timeout=2)
        except Exception:
            pass
        try:
            del st.query_params[_SESSION_PARAM]
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
# Lazy imports — only load the selected page module, not all 9 at once.
# Saves ~2.7s on login page cold load and avoids importing heavy page deps early.
import importlib

_PAGE_MODULES = {
    "Overview":      "dashboard._pages._overview",
    "Agents":        "dashboard._pages._agents",
    "Memory":        "dashboard._pages._memory",
    "Workflows":     "dashboard._pages._workflows",
    "Projects":      "dashboard._pages._projects",
    "Outputs":       "dashboard._pages._outputs",
    "Tickets":       "dashboard._pages._tickets",
    "Observability": "dashboard._pages._observability",
    "Settings":      "dashboard._pages._settings",
    "Admin":         "dashboard._pages._admin",
}

_PAGE_GETTERS = {
    "Overview":      api_get_cached,
    "Agents":        api_get,
    "Memory":        api_get,
    "Workflows":     api_get,
    "Projects":      api_get,
    "Outputs":       api_get_cached,
    "Tickets":       api_get,
    "Observability": api_get,
    "Settings":      api_get,
    "Admin":         api_get,
}

_mod = importlib.import_module(_PAGE_MODULES[page])
_mod.render(_PAGE_GETTERS[page], api_post, bulk_delete)
