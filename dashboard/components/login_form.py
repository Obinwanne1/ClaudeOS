"""Login and register form — rendered before dashboard when not authenticated."""
from __future__ import annotations

import os
import requests
import streamlit as st

_API_BASE = "http://localhost:5000/api/v1"


def render_login() -> None:
    """Render centered login/register card. On success populates session state and reruns."""
    from dashboard.components.brand import aurora_hero, get_theme_vars, PRIMARY
    t = get_theme_vars()

    # Centre the form
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        aurora_hero("ClaudeOS", subtitle="AI Operating System", pill="Sign in to continue")
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Sign In", "Register"])

        with tab_login:
            username = st.text_input("Username", key="li_username", placeholder="your username")
            password = st.text_input("Password", type="password", key="li_password")
            if st.button("Sign In", type="primary", use_container_width=True, key="li_btn"):
                _do_login(username.strip(), password)

        with tab_register:
            st.caption("Create a client account for your namespace.")
            r_username  = st.text_input("Username", key="reg_username")
            r_email     = st.text_input("Email (optional)", key="reg_email")
            r_password  = st.text_input("Password", type="password", key="reg_password")
            r_password2 = st.text_input("Confirm password", type="password", key="reg_password2")

            # Fetch client namespaces for the dropdown
            try:
                ns_resp = requests.get(f"{_API_BASE}/health", timeout=2)
                _api_up = ns_resp.ok
            except Exception:
                _api_up = False

            if _api_up:
                try:
                    ns_resp = requests.get(f"{_API_BASE}/namespaces?type=client", timeout=3)
                    ns_list = [n["slug"] for n in ns_resp.json()] if ns_resp.ok else []
                except Exception:
                    ns_list = []
            else:
                ns_list = []

            r_namespace = st.selectbox("Your namespace (client)", ns_list or ["— API offline —"], key="reg_ns")

            if st.button("Create Account", use_container_width=True, key="reg_btn"):
                _do_register(r_username.strip(), r_email.strip(), r_password, r_password2, r_namespace)

        st.markdown(
            f"<div style='text-align:center;font-size:0.75rem;color:{t['TEXT_MUTED']};margin-top:16px;'>"
            "ClaudeOS · Secure access</div>",
            unsafe_allow_html=True,
        )


# ── Internal ─────────────────────────────────────────────────────────────────

def _do_login(username: str, password: str) -> None:
    if not username or not password:
        st.warning("Enter username and password.")
        return
    try:
        r = requests.post(
            f"{_API_BASE}/auth/login",
            json={"username": username, "password": password},
            timeout=5,
        )
    except Exception:
        st.error("Cannot reach API server. Is it running?")
        return

    if r.status_code == 401:
        st.error("Invalid username or password.")
    elif r.status_code == 423:
        secs = r.json().get("retry_after_seconds", 900)
        st.error(f"Account locked. Try again in {secs // 60} min {secs % 60}s.")
    elif r.status_code == 403:
        st.error("Account disabled. Contact your administrator.")
    elif r.status_code == 429:
        st.warning("Too many attempts. Wait a minute and try again.")
    elif r.ok:
        data = r.json()
        user = data["user"]
        st.session_state["jwt_token"]      = data["access_token"]
        st.session_state["refresh_token"]  = data["refresh_token"]
        st.session_state["user_id"]        = user["id"]
        st.session_state["username"]       = user["username"]
        st.session_state["user_role"]      = user["role"]
        st.session_state["user_namespace"] = user.get("namespace")
        st.rerun()
    else:
        st.error(f"Login failed ({r.status_code}).")


def _do_register(username: str, email: str, password: str, password2: str, namespace: str) -> None:
    if not username or not password:
        st.warning("Username and password required.")
        return
    if password != password2:
        st.error("Passwords do not match.")
        return
    if not namespace or namespace == "— API offline —":
        st.warning("Select a valid namespace.")
        return
    try:
        r = requests.post(
            f"{_API_BASE}/auth/register",
            json={"username": username, "email": email or None, "password": password, "namespace": namespace},
            timeout=5,
        )
    except Exception:
        st.error("Cannot reach API server.")
        return

    if r.status_code == 201:
        st.success("Account created! Switch to Sign In to log in.")
    elif r.status_code == 409:
        st.error(r.json().get("error", "Username or namespace already taken."))
    elif r.status_code == 403:
        st.error("Self-registration is disabled. Contact your administrator.")
    elif r.status_code == 422:
        st.error(r.json().get("error", "Validation failed."))
    else:
        st.error(f"Registration failed ({r.status_code}).")
