"""Tickets page — create, browse, and manage support tickets."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import streamlit as st

PRIORITY_ICONS = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢"}
PRIORITY_LABELS = {1: "Critical", 2: "High", 3: "Medium", 4: "Low"}
STATUS_ICONS = {
    "open": "🔵",
    "in_progress": "🟠",
    "resolved": "🟢",
    "closed": "⚫",
}
CATEGORIES = ["bug", "billing", "access", "feature", "other"]
SLA_TIERS = ["P1", "P2", "P3", "P4"]
SLA_LABELS = {"P1": "P1 Critical (4h)", "P2": "P2 High (8h)", "P3": "P3 Medium (24h)", "P4": "P4 Low (72h)"}
SLA_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 72}


def _sla_overdue(ticket: dict) -> bool:
    due = ticket.get("sla_due_at")
    status = ticket.get("status", "")
    if not due or status in ("resolved", "closed"):
        return False
    try:
        due_dt = datetime.strptime(due[:19], "%Y-%m-%d %H:%M:%S")
        return datetime.utcnow() > due_dt
    except Exception:
        return False


def render(api_get, api_post):
    st.title("Tickets")
    role = st.session_state.get("user_role", "viewer")

    if role in ("client", "viewer"):
        _render_client_view(api_get, api_post)
    elif role == "staff":
        _render_staff_view(api_get, api_post)
    else:
        _render_admin_view(api_get, api_post)


# ── Client view ────────────────────────────────────────────────────────────────

def _render_client_view(api_get, api_post):
    tab_list, tab_new = st.tabs(["My Tickets", "New Ticket"])

    with tab_list:
        tickets = api_get("/tickets") or []
        if not tickets:
            st.info("No tickets yet. Create one in the 'New Ticket' tab.")
        else:
            st.caption(f"{len(tickets)} tickets")
            for t in tickets:
                _render_ticket_card(t, api_get, api_post, can_edit_desc=True)

    with tab_new:
        _render_create_form(api_post, namespace=st.session_state.get("user_namespace"))


# ── Staff view ─────────────────────────────────────────────────────────────────

def _render_staff_view(api_get, api_post):
    tab_assigned, tab_new = st.tabs(["Assigned to Me", "New Ticket"])

    with tab_assigned:
        tickets = api_get("/tickets?assigned_to=me") or []
        if not tickets:
            st.info("No tickets assigned to you.")
        else:
            st.caption(f"{len(tickets)} assigned tickets")
            for t in tickets:
                _render_ticket_card(t, api_get, api_post, staff_controls=True)

    with tab_new:
        _render_create_form(api_post)


# ── Admin / Operator view ──────────────────────────────────────────────────────

def _render_admin_view(api_get, api_post):
    tab_all, tab_new, tab_stats = st.tabs(["All Tickets", "New Ticket", "Stats"])

    with tab_all:
        _render_admin_ticket_list(api_get, api_post)

    with tab_new:
        ns_data = api_get("/namespaces") or []
        ns_options = [n["slug"] for n in ns_data] if ns_data else []
        _render_create_form(api_post, ns_options=ns_options)

    with tab_stats:
        _render_stats(api_get)


def _render_admin_ticket_list(api_get, api_post):
    # Parallel fetch: tickets + assignable staff
    results: dict = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(api_get, "/tickets"): "tickets",
            ex.submit(api_get, "/tickets/assignable-staff"): "staff",
            ex.submit(api_get, "/namespaces"): "namespaces",
        }
        for f in as_completed(futures):
            results[futures[f]] = f.result()

    all_tickets = results.get("tickets") or []
    staff_list = results.get("staff") or []
    ns_data = results.get("namespaces") or []

    staff_names = [s["username"] for s in staff_list]
    ns_slugs = [n["slug"] for n in ns_data]

    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        f_status = st.selectbox("Status", ["all"] + list(STATUS_ICONS.keys()), key="tk_f_status")
    with col2:
        f_priority = st.selectbox("Priority", ["all", "1-Critical", "2-High", "3-Medium", "4-Low"], key="tk_f_priority")
    with col3:
        f_ns = st.selectbox("Namespace", ["all"] + ns_slugs, key="tk_f_ns")
    with col4:
        f_assigned = st.selectbox("Assigned to", ["all"] + staff_names, key="tk_f_assigned")

    # Apply client-side filters
    tickets = all_tickets
    if f_status != "all":
        tickets = [t for t in tickets if t["status"] == f_status]
    if f_priority != "all":
        p = int(f_priority[0])
        tickets = [t for t in tickets if t["priority"] == p]
    if f_ns != "all":
        tickets = [t for t in tickets if t["namespace"] == f_ns]
    if f_assigned != "all":
        tickets = [t for t in tickets if t["assigned_to"] == f_assigned]

    overdue = [t for t in tickets if _sla_overdue(t)]
    if overdue:
        st.warning(f"⚠️ {len(overdue)} ticket(s) past SLA deadline")

    st.caption(f"{len(tickets)} tickets")
    for t in tickets:
        _render_ticket_card(t, api_get, api_post, admin_controls=True, staff_names=staff_names)


# ── Shared card ────────────────────────────────────────────────────────────────

def _render_ticket_card(
    t: dict,
    api_get,
    api_post,
    *,
    can_edit_desc: bool = False,
    staff_controls: bool = False,
    admin_controls: bool = False,
    staff_names: list | None = None,
):
    tid = t["id"]
    prio = t.get("priority", 3)
    status = t.get("status", "open")
    sla_tier = t.get("sla_tier") or ""
    sla_due = (t.get("sla_due_at") or "")[:16]
    overdue = _sla_overdue(t)
    overdue_tag = " ⚠️ OVERDUE" if overdue else ""

    header = (
        f"{PRIORITY_ICONS.get(prio,'•')} **{t.get('title','?')}**"
        f"  ·  {STATUS_ICONS.get(status,'?')} `{status}`"
        f"  ·  `{t.get('namespace','')}`"
        f"  ·  {(t.get('created_at') or '')[:10]}"
        f"{overdue_tag}"
    )

    with st.expander(header):
        st.markdown(f"**Description:** {t.get('description','')}")
        meta_cols = st.columns(4)
        meta_cols[0].markdown(f"**Category:** `{t.get('category','?')}`")
        meta_cols[1].markdown(f"**Priority:** {PRIORITY_ICONS.get(prio,'')} {PRIORITY_LABELS.get(prio,'?')}")
        meta_cols[2].markdown(f"**SLA:** `{sla_tier or '—'}`")
        meta_cols[3].markdown(f"**Due:** `{sla_due or '—'}`")

        assigned = t.get("assigned_to") or "—"
        st.markdown(f"**Assigned to:** `{assigned}`")

        if t.get("resolution"):
            st.success(f"**Resolution:** {t['resolution']}")

        st.markdown("---")

        # ── Admin controls ──
        if admin_controls:
            _render_admin_controls(tid, t, api_post, staff_names or [])
            st.markdown("---")

        # ── Staff controls ──
        if staff_controls:
            _render_staff_controls(tid, t, api_post)
            st.markdown("---")

        # ── Client edit description ──
        if can_edit_desc and status == "open":
            with st.expander("Edit description"):
                new_desc = st.text_area("Description", value=t.get("description", ""), key=f"edit_desc_{tid}")
                if st.button("Save", key=f"save_desc_{tid}"):
                    res = api_post(f"/tickets/{tid}", {"description": new_desc}, method="PATCH")
                    if res:
                        st.success("Updated.")
                        st.rerun()

        # ── Comment thread ──
        _render_comments(tid, api_get, api_post)


def _render_admin_controls(ticket_id: str, t: dict, api_post, staff_names: list):
    col1, col2, col3 = st.columns(3)

    with col1:
        new_status = st.selectbox(
            "Status",
            list(STATUS_ICONS.keys()),
            index=list(STATUS_ICONS.keys()).index(t.get("status", "open")),
            key=f"adm_status_{ticket_id}",
        )
        new_cat = st.selectbox(
            "Category",
            CATEGORIES,
            index=CATEGORIES.index(t.get("category", "other")),
            key=f"adm_cat_{ticket_id}",
        )

    with col2:
        sla_options = ["— None —"] + SLA_TIERS
        current_sla = t.get("sla_tier") or "— None —"
        if current_sla not in sla_options:
            current_sla = "— None —"
        new_sla = st.selectbox(
            "SLA Tier",
            sla_options,
            index=sla_options.index(current_sla),
            key=f"adm_sla_{ticket_id}",
        )
        if new_sla and new_sla != "— None —":
            st.caption(f"Due in {SLA_HOURS[new_sla]}h from now")

        prio_options = [1, 2, 3, 4]
        prio_labels = [f"{PRIORITY_ICONS[p]} {PRIORITY_LABELS[p]}" for p in prio_options]
        current_prio_idx = prio_options.index(t.get("priority", 3))
        new_prio_label = st.selectbox("Priority", prio_labels, index=current_prio_idx, key=f"adm_prio_{ticket_id}")
        new_prio = prio_options[prio_labels.index(new_prio_label)]

    with col3:
        assign_options = ["— Unassigned —"] + staff_names
        current_assigned = t.get("assigned_to") or "— Unassigned —"
        if current_assigned not in assign_options:
            assign_options.append(current_assigned)
        new_assigned = st.selectbox(
            "Assign to",
            assign_options,
            index=assign_options.index(current_assigned),
            key=f"adm_assign_{ticket_id}",
        )

    new_resolution = st.text_area(
        "Resolution notes", value=t.get("resolution") or "", key=f"adm_res_{ticket_id}"
    )

    if st.button("Update Ticket", key=f"adm_update_{ticket_id}", use_container_width=True):
        payload: dict = {
            "status": new_status,
            "category": new_cat,
            "priority": new_prio,
            "assigned_to": None if new_assigned == "— Unassigned —" else new_assigned,
            "resolution": new_resolution or None,
        }
        if new_sla and new_sla != "— None —":
            payload["sla_tier"] = new_sla
        elif not t.get("sla_tier"):
            pass  # leave as is
        res = api_post(f"/tickets/{ticket_id}", payload, method="PATCH")
        if res:
            st.success("Ticket updated.")
            st.rerun()
        else:
            st.error("Update failed.")

    role = st.session_state.get("user_role")
    if role == "admin":
        if st.button("🗑 Delete Ticket", key=f"adm_del_{ticket_id}"):
            st.session_state[f"confirm_del_tk_{ticket_id}"] = True
        if st.session_state.get(f"confirm_del_tk_{ticket_id}"):
            st.warning("Permanently delete this ticket and all comments?")
            c1, c2 = st.columns(2)
            if c1.button("Yes, delete", key=f"yes_del_tk_{ticket_id}"):
                import requests as _req
                _req.delete(
                    f"http://localhost:5000/api/v1/tickets/{ticket_id}",
                    headers={"Authorization": f"Bearer {st.session_state.get('jwt_token','')}"},
                    timeout=5,
                )
                st.session_state.pop(f"confirm_del_tk_{ticket_id}", None)
                st.rerun()
            if c2.button("Cancel", key=f"cancel_del_tk_{ticket_id}"):
                st.session_state.pop(f"confirm_del_tk_{ticket_id}", None)
                st.rerun()


def _render_staff_controls(ticket_id: str, t: dict, api_post):
    status_options = ["in_progress", "resolved", "closed"]
    current = t.get("status", "open")
    if current not in status_options:
        status_options = [current] + status_options

    new_status = st.selectbox("Update Status", status_options,
                              index=status_options.index(current) if current in status_options else 0,
                              key=f"sf_status_{ticket_id}")
    new_resolution = st.text_area("Resolution notes", value=t.get("resolution") or "", key=f"sf_res_{ticket_id}")

    if st.button("Update", key=f"sf_update_{ticket_id}"):
        res = api_post(f"/tickets/{ticket_id}", {"status": new_status, "resolution": new_resolution or None}, method="PATCH")
        if res:
            st.success("Updated.")
            st.rerun()


def _render_comments(ticket_id: str, api_get, api_post):
    comments = api_get(f"/tickets/{ticket_id}/comments") or []
    if comments:
        st.markdown("**Comments:**")
        for c in comments:
            ts = (c.get("created_at") or "")[:16]
            st.markdown(f"`{c['author']}` · {ts}")
            st.markdown(f"> {c['body']}")
    else:
        st.caption("No comments yet.")

    username = st.session_state.get("username", "")
    new_comment = st.text_area("Add comment", key=f"comment_{ticket_id}", height=80)
    if st.button("Post Comment", key=f"post_comment_{ticket_id}"):
        if new_comment.strip():
            res = api_post(f"/tickets/{ticket_id}/comments", {"body": new_comment.strip()})
            if res:
                st.rerun()
        else:
            st.warning("Comment cannot be empty.")


# ── Create form ────────────────────────────────────────────────────────────────

def _render_create_form(api_post, namespace: str | None = None, ns_options: list | None = None):
    st.subheader("Create New Ticket")

    with st.form("new_ticket_form", clear_on_submit=True):
        title = st.text_input("Title *", placeholder="Brief summary of the issue")
        description = st.text_area("Description *", placeholder="Describe the issue in detail...", height=120)
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", CATEGORIES)
        with col2:
            prio_labels = [f"{PRIORITY_ICONS[p]} {PRIORITY_LABELS[p]}" for p in [1, 2, 3, 4]]
            prio_sel = st.selectbox("Priority", prio_labels, index=2)
            priority = [1, 2, 3, 4][prio_labels.index(prio_sel)]

        # Namespace — admins/operators can choose; clients are locked
        if ns_options:
            ns_sel = st.selectbox("Namespace", ns_options)
            payload_ns = ns_sel
        elif namespace:
            st.text_input("Namespace", value=namespace, disabled=True)
            payload_ns = namespace
        else:
            payload_ns = None

        submitted = st.form_submit_button("Submit Ticket", use_container_width=True)

    if submitted:
        if not title.strip() or not description.strip():
            st.error("Title and description are required.")
        else:
            payload: dict = {
                "title": title.strip(),
                "description": description.strip(),
                "category": category,
                "priority": priority,
            }
            if payload_ns:
                payload["namespace"] = payload_ns
            res = api_post("/tickets", payload)
            if res:
                st.success(f"Ticket created! ID: `{res['id'][:8]}...`")
                st.rerun()
            else:
                st.error("Failed to create ticket. Check API is running.")


# ── Stats ──────────────────────────────────────────────────────────────────────

def _render_stats(api_get):
    stats = api_get("/tickets/stats") or {}

    by_status = stats.get("by_status", {})
    by_priority = stats.get("by_priority", {})
    by_ns = stats.get("by_namespace", {})

    col1, col2, col3, col4 = st.columns(4)
    total = sum(by_status.values())
    col1.metric("Total Tickets", total)
    col2.metric("SLA Breached", stats.get("sla_breached", 0))
    col3.metric("Unassigned Open", stats.get("unassigned_open", 0))
    col4.metric("Resolved", by_status.get("resolved", 0) + by_status.get("closed", 0))

    st.markdown("---")
    left, right = st.columns(2)

    with left:
        st.markdown("**By Status:**")
        for s, cnt in sorted(by_status.items()):
            st.markdown(f"{STATUS_ICONS.get(s,'•')} `{s}` — {cnt}")

        st.markdown("**By Priority:**")
        for p_str, cnt in sorted(by_priority.items()):
            try:
                p = int(p_str)
            except (ValueError, TypeError):
                p = 3
            st.markdown(f"{PRIORITY_ICONS.get(p,'•')} {PRIORITY_LABELS.get(p,'?')} — {cnt}")

    with right:
        if by_ns:
            st.markdown("**By Namespace:**")
            for ns, cnt in sorted(by_ns.items(), key=lambda x: -x[1]):
                st.markdown(f"`{ns}` — {cnt}")
