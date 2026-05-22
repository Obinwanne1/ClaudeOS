"""Overview page — OS health, KPIs, live event feed, quick dispatch."""
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dashboard.components.brand import aurora_hero, PRIMARY


def _render_kpi_grid(kpis: list) -> None:
    """Render KPI cards as a pure HTML/CSS grid — immune to Streamlit column overrides.
    3 columns on desktop, 2 columns on mobile (≤480px).
    kpis: list of (label, value, delta_str|None)
    """
    from dashboard.components.brand import get_theme_vars
    t = get_theme_vars()
    # All HTML must be single-line — Streamlit's markdown parser chokes on
    # multi-line attribute values and treats subsequent lines as raw text.
    cards = ""
    for label, value, delta in kpis:
        d = f'<div style="font-size:0.72rem;color:#f87171;margin-top:2px;">{delta}</div>' if delta else ""
        cs = f"background:{t['SURFACE']};border:1px solid {t['BORDER']};border-radius:10px;padding:14px 16px;min-width:0;"
        ls = f"font-size:0.78rem;color:{t['TEXT_MUTED']};font-weight:500;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
        vs = f"font-size:1.9rem;font-weight:700;color:{t['TEXT']};line-height:1.1;"
        cards += f'<div style="{cs}"><div style="{ls}">{label}</div><div style="{vs}">{value}</div>{d}</div>'
    st.markdown(f'<div class="cos-kpi-grid">{cards}</div>', unsafe_allow_html=True)


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

    # KPI grid — pure HTML/CSS, bypasses Streamlit's column system entirely.
    # Renders 3-per-row on desktop, 2-per-row on mobile (≤480px).
    if is_scoped:
        kpis = [
            ("Memory",      counts.get("memory_entries", 0), None),
            ("Agents",      counts.get("agents", 0),         None),
            ("Runs",        counts.get("agent_runs", 0),     None),
            ("Outputs",     counts.get("outputs", 0),        None),
            ("Projects",    counts.get("projects", 0),       None),
            ("Open Tickets",open_tickets, f"🔴 {open_tickets} active" if open_tickets else None),
        ]
    else:
        kpis = [
            ("Memory",      counts.get("memory_entries", 0), None),
            ("Agents",      counts.get("agents", 0),         None),
            ("Runs",        counts.get("agent_runs", 0),     None),
            ("Workflows",   counts.get("workflows", 0),      None),
            ("Outputs",     counts.get("outputs", 0),        None),
            ("Open Tickets",open_tickets, f"🔴 {open_tickets} active" if open_tickets else None),
        ]
    _render_kpi_grid(kpis)

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
