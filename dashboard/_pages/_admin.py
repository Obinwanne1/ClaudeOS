"""Admin page — user management, API keys, audit log, sessions, security."""
import requests as _req
import streamlit as st
from dashboard.components.brand import aurora_hero, badge

_API_BASE = "http://localhost:5000/api/v1"


def _auth_headers() -> dict:
    token = st.session_state.get("jwt_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def render(api_get, api_post, bulk_delete=None):
    if st.session_state.get("user_role") != "admin":
        st.error("Admin access only.")
        return

    aurora_hero("Admin Panel", subtitle="Users · API Keys · Audit · Security", pill="Admin")

    tab_users, tab_keys, tab_audit, tab_sessions, tab_security = st.tabs([
        "Users", "API Keys", "Audit Log", "Sessions", "Security"
    ])

    with tab_users:
        _render_users(api_get, api_post)

    with tab_keys:
        _render_api_keys(api_get, api_post)

    with tab_audit:
        _render_audit(api_get)

    with tab_sessions:
        _render_sessions(api_get, api_post)

    with tab_security:
        _render_security(api_get, api_post)


# ── Users ─────────────────────────────────────────────────────────────────────

def _render_users(api_get, api_post):
    st.subheader("User Accounts")

    users = api_get("/admin/users") or []

    if users:
        rows = []
        for u in users:
            rows.append({
                "Username":   u.get("username", ""),
                "Role":       u.get("role", ""),
                "Namespace":  u.get("namespace") or "—",
                "Active":     "✅" if u.get("is_active") else "❌",
                "Pwd Change": "⚠️ Required" if u.get("must_change_password") else "✅ Set",
                "Locked":     "🔒" if u.get("locked_until") else "—",
                "Last Login": (u.get("last_login_at") or "Never")[:16],
                "Created":    (u.get("created_at") or "")[:10],
            })
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No users yet.")

    st.markdown("---")

    if users:
        user_names = [u["username"] for u in users]
        sel_usernames = st.multiselect("Select user(s) for actions", user_names, key="admin_sel_users")

        if len(sel_usernames) >= 2:
            # ── Bulk actions ──
            sel_users = [u for u in users if u["username"] in sel_usernames]
            sel_uids  = [u["id"] for u in sel_users]
            st.caption(f"{len(sel_usernames)} users selected")
            if st.button(f"Deactivate {len(sel_usernames)} users", key="bulk_deact_users"):
                st.session_state["bulk_confirm_users"] = True
            if st.session_state.get("bulk_confirm_users"):
                st.warning(f"Deactivate {len(sel_usernames)} accounts? This cannot be undone.")
                c1, c2 = st.columns(2)
                if c1.button("Yes, deactivate all", key="bulk_users_yes"):
                    _req.delete(
                        f"{_API_BASE}/admin/users/bulk",
                        json={"ids": sel_uids},
                        headers=_auth_headers(), timeout=10,
                    )
                    st.session_state.pop("bulk_confirm_users", None)
                    st.success("Deactivated.")
                    st.rerun()
                if c2.button("Cancel", key="bulk_users_cancel"):
                    st.session_state.pop("bulk_confirm_users", None)
                    st.rerun()

        elif len(sel_usernames) == 1:
            # ── Single-user actions ──
            sel_user = next((u for u in users if u["username"] == sel_usernames[0]), None)
            if sel_user:
                uid = sel_user["id"]
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Unlock account", key=f"unlock_{uid}", use_container_width=True):
                        r = api_post(f"/admin/users/{uid}/unlock", {})
                        st.success("Unlocked." if r else "Failed.")
                        st.rerun()
                with col2:
                    if sel_user.get("is_active"):
                        if st.button("Deactivate", key=f"deact_{uid}", use_container_width=True):
                            _req.delete(
                                f"{_API_BASE}/admin/users/{uid}",
                                headers=_auth_headers(), timeout=5,
                            )
                            st.success("Deactivated.")
                            st.rerun()
                    else:
                        if st.button("Reactivate", key=f"react_{uid}", use_container_width=True):
                            api_post(f"/admin/users/{uid}", {"is_active": True}, method="PATCH")
                            st.success("Reactivated.")
                            st.rerun()
                with col3:
                    with st.expander("Reset password"):
                        new_pw = st.text_input("New password", type="password", key=f"rpw_{uid}")
                        if st.button("Reset", key=f"rset_{uid}"):
                            r = api_post(f"/admin/users/{uid}/reset-password", {"new_password": new_pw})
                            st.success("Password reset." if r else "Failed (check strength).")

    st.markdown("---")

    with st.expander("➕ Create User"):
        _create_user_form(api_get, api_post)


def _create_user_form(api_get, api_post):
    st.caption(
        "Password rules: **min 10 chars · uppercase · lowercase · digit**. "
        "User will be forced to change password on first login."
    )
    col1, col2 = st.columns(2)
    with col1:
        new_username = st.text_input("Username", key="nu_username")
        new_email    = st.text_input("Email (optional)", key="nu_email")
        new_role     = st.selectbox("Role", ["operator", "viewer", "client", "admin"], key="nu_role")
    with col2:
        new_password  = st.text_input("Temporary password", type="password", key="nu_pw",
                                      help="Min 10 chars · upper + lower + digit")
        new_password2 = st.text_input("Confirm password", type="password", key="nu_pw2")
        ns_data = api_get("/namespaces") or []
        ns_opts = ["(none)"] + [n["slug"] for n in ns_data]
        new_ns  = st.selectbox("Namespace", ns_opts, key="nu_ns")

    if st.button("Create User", type="primary", use_container_width=True, key="nu_btn"):
        if not new_username or not new_password:
            st.warning("Username and password required.")
        elif new_password != new_password2:
            st.error("Passwords do not match.")
        else:
            payload = {
                "username": new_username, "password": new_password,
                "role": new_role, "email": new_email or None,
                "namespace": None if new_ns == "(none)" else new_ns,
                "must_change_password": True,
            }
            try:
                r = _req.post(
                    f"{_API_BASE}/admin/users",
                    json=payload, headers=_auth_headers(), timeout=5,
                )
                if r.status_code == 201:
                    st.success(f"User `{new_username}` created. They must change password on first login.")
                    st.rerun()
                else:
                    st.error(f"Failed: {r.json().get('error', f'HTTP {r.status_code}')}")
            except Exception as e:
                st.error(f"Cannot reach API: {e}")


# ── API Keys ──────────────────────────────────────────────────────────────────

def _render_api_keys(api_get, api_post):
    st.subheader("API Keys")

    keys = api_get("/admin/api-keys") or []
    if keys:
        rows = [{
            "ID":          k["id"][:8] + "...",
            "Name":        k.get("name", ""),
            "Namespace":   k.get("namespace", "global"),
            "Permissions": ", ".join(k.get("permissions") if isinstance(k.get("permissions"), list) else ["?"]),
            "Last Used":   (k.get("last_used") or "Never")[:16],
            "Created":     (k.get("created_at") or "")[:10],
        } for k in keys]
        st.dataframe(rows, use_container_width=True)

        key_ids    = [k["id"] for k in keys]
        key_labels = [f"{k['name']} ({k['id'][:8]})" for k in keys]

        sel_labels = st.multiselect("Select key(s) to revoke", key_labels, key="sel_keys_revoke")
        if sel_labels:
            sel_indices = [key_labels.index(l) for l in sel_labels]
            sel_key_ids = [key_ids[i] for i in sel_indices]
            verb = f"Revoke {len(sel_labels)} key(s)"
            if st.button(verb, key="revoke_keys_btn"):
                st.session_state["bulk_confirm_keys"] = True
            if st.session_state.get("bulk_confirm_keys"):
                st.warning(f"Permanently revoke {len(sel_labels)} key(s)?")
                c1, c2 = st.columns(2)
                if c1.button("Yes, revoke all", key="bulk_keys_yes"):
                    _req.delete(
                        f"{_API_BASE}/admin/api-keys/bulk",
                        json={"ids": sel_key_ids},
                        headers=_auth_headers(), timeout=10,
                    )
                    st.session_state.pop("bulk_confirm_keys", None)
                    st.success("Revoked.")
                    st.rerun()
                if c2.button("Cancel", key="bulk_keys_cancel"):
                    st.session_state.pop("bulk_confirm_keys", None)
                    st.rerun()
    else:
        st.info("No API keys.")

    st.markdown("---")
    with st.expander("➕ Create API Key"):
        _create_key_form(api_get, api_post)


def _create_key_form(api_get, api_post):
    key_name = st.text_input("Key name", key="nk_name", placeholder="e.g. my-script")
    ns_data  = api_get("/namespaces") or []
    ns_opts  = [n["slug"] for n in ns_data] or ["global"]
    key_ns   = st.selectbox("Namespace", ns_opts, key="nk_ns")
    perms    = st.multiselect("Permissions", ["read", "write"], default=["read", "write"], key="nk_perms")

    if st.button("Generate Key", type="primary", use_container_width=True, key="nk_btn"):
        r = api_post("/admin/api-keys", {"name": key_name, "namespace": key_ns, "permissions": perms})
        if r and r.get("raw_key"):
            st.success("Key created. Copy it now — it won't be shown again.")
            st.code(r["raw_key"])
        else:
            st.error("Create failed.")


# ── Audit Log ─────────────────────────────────────────────────────────────────

def _render_audit(api_get):
    st.subheader("Auth Audit Log")

    col1, col2 = st.columns(2)
    with col1:
        event_types = ["", "login_success", "login_failure", "logout", "user_created",
                       "user_deactivated", "lockout_triggered", "password_change",
                       "password_reset", "api_key_created", "api_key_revoked",
                       "token_refresh", "register", "session_revoked"]
        et_filter = st.selectbox("Filter event type", event_types, key="audit_et")
    with col2:
        un_filter = st.text_input("Filter username", key="audit_un", placeholder="(any)")

    url = "/admin/audit?limit=100"
    if et_filter:
        url += f"&event_type={et_filter}"
    if un_filter.strip():
        url += f"&username={un_filter.strip()}"

    events = api_get(url) or []
    if events:
        rows = [{
            "Time":      (e.get("created_at") or "")[:16],
            "Event":     e.get("event_type", ""),
            "Username":  e.get("username") or "—",
            "IP":        e.get("ip_address") or "—",
            "Namespace": e.get("namespace") or "—",
        } for e in events]
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No events found.")


# ── Sessions ──────────────────────────────────────────────────────────────────

def _render_sessions(api_get, api_post):
    st.subheader("Active Sessions")

    sessions = api_get("/admin/sessions") or []
    if sessions:
        rows = [{
            "ID":        s["id"][:8] + "...",
            "User":      s.get("username", ""),
            "IP":        s.get("ip_address") or "—",
            "Created":   (s.get("created_at") or "")[:16],
            "Last Used": (s.get("last_used_at") or "")[:16],
            "Expires":   (s.get("expires_at") or "")[:16],
        } for s in sessions]
        st.dataframe(rows, use_container_width=True)

        sess_labels = [
            f"{s.get('username','')} — {s['id'][:8]} ({s.get('ip_address') or 'no IP'})"
            for s in sessions
        ]
        sel_sess_labels = st.multiselect("Select session(s) to revoke", sess_labels, key="sel_sess_multi")
        if sel_sess_labels:
            sel_indices = [sess_labels.index(l) for l in sel_sess_labels]
            sel_sess_ids = [sessions[i]["id"] for i in sel_indices]
            verb = f"Revoke {len(sel_sess_labels)} session(s)"
            if st.button(verb, key="revoke_sess_btn"):
                st.session_state["bulk_confirm_sess"] = True
            if st.session_state.get("bulk_confirm_sess"):
                st.warning(f"Revoke {len(sel_sess_labels)} session(s)?")
                c1, c2 = st.columns(2)
                if c1.button("Yes, revoke all", key="bulk_sess_yes"):
                    _req.delete(
                        f"{_API_BASE}/admin/sessions/bulk",
                        json={"ids": sel_sess_ids},
                        headers=_auth_headers(), timeout=10,
                    )
                    st.session_state.pop("bulk_confirm_sess", None)
                    st.success("Revoked.")
                    st.rerun()
                if c2.button("Cancel", key="bulk_sess_cancel"):
                    st.session_state.pop("bulk_confirm_sess", None)
                    st.rerun()
    else:
        st.info("No active sessions.")


# ── Security Settings ─────────────────────────────────────────────────────────

def _render_security(api_get, api_post):
    st.subheader("Security Settings")

    cfg = api_get("/admin/security-settings") or {}

    max_attempts   = st.slider("Max failed login attempts before lockout", 3, 10,
                                int(cfg.get("max_failed_attempts", 5)), key="sec_max")
    lockout_mins   = st.selectbox("Lockout duration (minutes)", [5, 10, 15, 30, 60],
                                   index=[5,10,15,30,60].index(int(cfg.get("lockout_minutes", 15)))
                                         if int(cfg.get("lockout_minutes", 15)) in [5,10,15,30,60] else 2,
                                   key="sec_lock")
    token_mins     = st.selectbox("Access token lifetime (minutes)", [15, 30, 60, 120],
                                   index=[15,30,60,120].index(int(cfg.get("access_token_minutes", 60)))
                                         if int(cfg.get("access_token_minutes", 60)) in [15,30,60,120] else 2,
                                   key="sec_tok")
    refresh_days   = st.selectbox("Refresh token lifetime (days)", [1, 7, 14, 30],
                                   index=[1,7,14,30].index(int(cfg.get("refresh_token_days", 7)))
                                         if int(cfg.get("refresh_token_days", 7)) in [1,7,14,30] else 1,
                                   key="sec_ref")
    allow_register = st.toggle("Allow client self-registration", value=cfg.get("allow_self_register", "1") == "1",
                                key="sec_reg")

    if st.button("Save Security Settings", type="primary", use_container_width=True, key="sec_save"):
        r = api_post("/admin/security-settings", {
            "max_failed_attempts": max_attempts,
            "lockout_minutes":     lockout_mins,
            "access_token_minutes": token_mins,
            "refresh_token_days":  refresh_days,
            "allow_self_register": "1" if allow_register else "0",
        }, method="PATCH")
        if r:
            st.success("Settings saved.")
        else:
            st.error("Save failed.")
