"""Overview page — OS health, KPIs, live event feed, quick dispatch."""
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dashboard.components.brand import aurora_hero, PRIMARY


def render(api_get, api_post, bulk_delete=None):
    role      = st.session_state.get("user_role", "viewer")
    username  = st.session_state.get("username", "")
    user_ns   = st.session_state.get("user_namespace")
    is_scoped = role in ("client", "viewer") and bool(user_ns)
    is_admin  = role in ("admin", "operator")

    aurora_hero(
        title="ClaudeOS",
        subtitle="AI Operating System — coordination layer for all agents, memory, and workflows.",
        pill="v7.0 · All Systems",
    )

    # Namespace context banner for scoped users
    if is_scoped:
        st.markdown(
            f'<div style="display:inline-flex;align-items:center;gap:8px;'
            f'background:rgba(64,126,60,0.12);border:1px solid {PRIMARY};'
            f'border-radius:8px;padding:6px 14px;margin-bottom:12px;font-size:0.85rem;">'
            f'<span style="color:{PRIMARY};font-weight:700;">🏢 Workspace</span>'
            f'<span style="color:inherit;">{user_ns}</span></div>',
            unsafe_allow_html=True,
        )

    # Fetch all data in parallel
    _calls = {
        "status":     "/system/status",
        "stats":      "/system/stats",
        "agents":     "/agents",
        "runs":       "/agents/runs?limit=10",
        "namespaces": "/memory/namespaces",
    }
    results: dict = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(api_get, path): key for key, path in _calls.items()}
        for f in as_completed(futures):
            results[futures[f]] = f.result()

    status      = results.get("status")
    stats       = results.get("stats")
    agents_data = results.get("agents")
    runs_data   = results.get("runs")
    counts = stats.get("counts", {}) if stats else {}
    open_tickets = counts.get("open_tickets", 0)

    # KPI row — 6 metrics; swap Workflows→Open Tickets for scoped users
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Memory", counts.get("memory_entries", 0))
    col2.metric("Agents", counts.get("agents", 0))
    col3.metric("Runs", counts.get("agent_runs", 0))
    if is_scoped:
        col4.metric("Outputs", counts.get("outputs", 0))
        col5.metric("Projects", counts.get("projects", 0))
        col6.metric("Open Tickets", open_tickets, delta=None if open_tickets == 0 else f"{open_tickets} active")
    else:
        col4.metric("Workflows", counts.get("workflows", 0))
        col5.metric("Outputs", counts.get("outputs", 0))
        col6.metric("Open Tickets", open_tickets)

    st.markdown("---")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        if is_admin:
            st.subheader("System Status")
            if status:
                services = status.get("services", {})
                for svc, info in services.items():
                    icon = "🟢" if info.get("status") == "ok" else "🔴"
                    detail = ""
                    if svc == "database":
                        detail = f"  `{info.get('path','?')}` · {info.get('size_kb',0)} KB"
                    elif svc == "api":
                        detail = f"  port :{info.get('port','?')}"
                    st.markdown(f"{icon} **{svc.upper()}**{detail}")
            else:
                st.error("API unreachable — run `start.ps1`")
                st.code(".\\scripts\\start.ps1", language="powershell")

        # Recent activity feed
        st.subheader("Recent Activity" if is_scoped else "Recent Agent Runs")
        runs = (runs_data or {}).get("runs", [])
        if runs:
            for run in runs[:8]:
                status_icon = {"done": "✅", "failed": "❌", "running": "⏳", "pending": "⏸️"}.get(run.get("status", ""), "•")
                agent_id = run.get("agent_id", "")[:8]
                ns       = run.get("namespace", "global")
                created  = run.get("created_at", "")[:16] if run.get("created_at") else ""
                ns_part  = "" if is_scoped else f" · `{ns}`"
                st.markdown(f"`{status_icon} {run.get('status','?'):8}` · agent `{agent_id}`{ns_part} · {created}")
        else:
            # Empty state
            st.info(
                f"👋 Welcome, **{username}**! No agent runs yet.\n\n"
                "Use **Quick Dispatch** on the right to run your first agent, "
                "or explore **Agents** in the sidebar."
            )

    with col_right:
        st.subheader("Quick Dispatch")
        if agents_data and agents_data.get("agents"):
            agent_names = [a["name"] for a in agents_data["agents"]]
            selected_agent = st.selectbox("Agent", agent_names, key="quick_agent")

            if is_scoped:
                # Client users dispatch only into their namespace
                selected_ns = user_ns
                st.caption(f"Namespace: **{user_ns}**")
            else:
                selected_ns = st.selectbox(
                    "Namespace",
                    ["global", "reci-transport", "ivycandy-hair", "faiyke-ai", "personal"],
                    key="quick_ns",
                )

            prompt = st.text_area("Prompt", height=100, key="quick_prompt", placeholder="What should this agent do?")

            if st.button("Run Agent", use_container_width=True):
                if prompt.strip():
                    result = api_post(f"/agents/{selected_agent}/run", {
                        "prompt": prompt,
                        "namespace": selected_ns,
                    })
                    if result:
                        st.success(f"Dispatched! Run ID: `{result.get('run_id','?')[:8]}...`")
                        st.info(f"Poll: `GET /api/v1/agents/runs/{result.get('run_id','?')}`")
                    else:
                        st.error("Dispatch failed — check API logs")
                else:
                    st.warning("Enter a prompt first")

        # Memory breakdown — admins see all namespaces, clients see own
        ns_data = results.get("namespaces")
        if ns_data and ns_data.get("namespaces"):
            if is_scoped:
                own_cnt = ns_data["namespaces"].get(user_ns, 0)
                st.subheader("Your Memory")
                st.markdown(f"**{user_ns}** — {own_cnt} entries")
            else:
                st.subheader("Memory by Namespace")
                for ns, cnt in sorted(ns_data["namespaces"].items(), key=lambda x: -x[1]):
                    st.markdown(f"**{ns}** — {cnt} entries")
