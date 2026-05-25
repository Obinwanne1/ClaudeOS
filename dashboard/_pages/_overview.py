"""Overview page — Phase 13.3: Live activity feed with real-time polling."""
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dashboard.components.brand import aurora_hero, PRIMARY


def _render_kpi_grid(kpis: list) -> None:
    from dashboard.components.brand import get_theme_vars
    t = get_theme_vars()
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
        pill="v8.0 · All Systems",
    )

    if is_scoped:
        st.markdown(
            f'<div style="display:inline-flex;align-items:center;gap:8px;'
            f'background:rgba(64,126,60,0.12);border:1px solid {PRIMARY};'
            f'border-radius:8px;padding:6px 14px;margin-bottom:12px;font-size:0.85rem;">'
            f'<span style="color:{PRIMARY};font-weight:700;">🏢 Workspace</span>'
            f'<span style="color:inherit;">{user_ns}</span></div>',
            unsafe_allow_html=True,
        )

    # Parallel data fetch
    _runs_url = (
        f"/agents/runs?limit=10&namespace={user_ns}" if is_scoped and user_ns
        else "/agents/runs?limit=10"
    )
    _calls = {
        "status":     "/system/status",
        "stats":      "/system/stats",
        "agents":     "/agents",
        "runs":       _runs_url,
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

    # KPI grid
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

        # Live activity feed
        _render_live_feed(runs_data, is_scoped, username, api_post)

    with col_right:
        st.subheader("Quick Dispatch")
        if agents_data and agents_data.get("agents"):
            agent_names = [a["name"] for a in agents_data["agents"]]
            selected_agent = st.selectbox("Agent", agent_names, key="quick_agent")

            if is_scoped:
                selected_ns = user_ns
                st.caption(f"Namespace: **{user_ns}**")
            else:
                # Dynamic namespace list from already-fetched /memory/namespaces
                ns_data_q = results.get("namespaces")
                _ns_opts = sorted(ns_data_q["namespaces"].keys()) if ns_data_q and ns_data_q.get("namespaces") else ["global"]
                selected_ns = st.selectbox("Namespace", _ns_opts, key="quick_ns")

            prompt = st.text_area("Prompt", height=100, key="quick_prompt",
                                  placeholder="What should this agent do?")

            if st.button("Run Agent", use_container_width=True):
                if prompt.strip():
                    result = api_post(f"/agents/{selected_agent}/run", {
                        "prompt": prompt,
                        "namespace": selected_ns,
                    })
                    if result:
                        st.success(f"Dispatched! Run ID: `{result.get('run_id','?')[:8]}...`")
                    else:
                        st.error("Dispatch failed — check API logs")
                else:
                    st.warning("Enter a prompt first")

        # Memory breakdown
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

    # Live refresh toggle
    st.markdown("---")
    _render_live_refresh_toggle()


def _render_live_feed(runs_data, is_scoped: bool, username: str, api_post=None) -> None:
    """Live activity feed — auto-refreshes every 8 seconds when live mode is on."""
    from dashboard.components.brand import get_theme_vars as _tv
    _t = _tv()

    col_title, col_toggle = st.columns([3, 1])
    with col_title:
        st.subheader("🔴 Live Activity")
    with col_toggle:
        live_on = st.toggle("Auto-refresh", value=st.session_state.get("live_mode", False),
                            key="live_toggle")
        st.session_state["live_mode"] = live_on

    runs = (runs_data or {}).get("runs", [])

    # Error alert strip
    recent_errors = [r for r in runs[:5] if r.get("status") == "failed"]
    if recent_errors:
        st.markdown(
            f'<div style="background:#ef444422;border:1px solid #ef4444;border-radius:8px;'
            f'padding:8px 14px;margin-bottom:8px;font-size:0.82rem;color:#ef4444;">'
            f'⚠️ {len(recent_errors)} recent failure{"s" if len(recent_errors)>1 else ""} — '
            f'check run history</div>',
            unsafe_allow_html=True,
        )

    # Running now indicator
    running_now = [r for r in runs if r.get("status") in ("running", "pending")]
    if running_now:
        st.markdown(
            f'<div style="background:#f59e0b22;border:1px solid #f59e0b;border-radius:8px;'
            f'padding:6px 14px;margin-bottom:8px;font-size:0.82rem;color:#f59e0b;">'
            f'⏳ {len(running_now)} agent{"s" if len(running_now)>1 else ""} running now</div>',
            unsafe_allow_html=True,
        )

    if runs:
        feed_placeholder = st.empty()
        with feed_placeholder.container():
            for run in runs[:10]:
                _status = run.get("status", "?")
                _run_id = run.get("id", "")
                _icon = {"done": "✅", "failed": "❌", "running": "⏳", "pending": "⏸️"}.get(_status, "•")
                _agent = (run.get("agent_id") or "")[:12]
                _ns    = run.get("namespace", "global")
                _raw   = run.get("created_at", "")
                eval_score = run.get("eval_score")
                score_pill = ""
                if eval_score is not None:
                    sc_color = "#5a9e56" if eval_score >= 4 else ("#f59e0b" if eval_score >= 2.5 else "#ef4444")
                    score_pill = f'<span style="background:{sc_color}22;color:{sc_color};border:1px solid {sc_color}44;padding:1px 6px;border-radius:8px;font-size:0.7rem;">⭐{eval_score:.1f}</span>'
                try:
                    from datetime import datetime as _dt
                    _parsed = _dt.fromisoformat(_raw.replace("Z", ""))
                    _created = f"{_parsed.day} {_parsed.strftime('%b')} · {_parsed.strftime('%H:%M')}"
                except Exception:
                    _created = _raw[:16]
                _muted = _t["TEXT_MUTED"]
                _surf2 = _t["SURFACE2"]
                _txt   = _t["TEXT"]
                _ns_part = "" if is_scoped else f'<span style="color:{_muted};font-size:0.75rem;"> · {_ns}</span>'
                _color = {"done": "#5a9e56", "failed": "#ef4444", "running": "#f59e0b", "pending": "#6b7280"}.get(_status, "#6b7280")
                _pill = f"background:{_surf2};color:{_txt};padding:1px 6px;border-radius:4px;font-size:0.78rem;font-family:monospace;"
                if _status == "failed" and _run_id:
                    _col_main, _col_btn = st.columns([10, 1])
                    with _col_main:
                        st.markdown(
                            f'<div style="padding:7px 0;font-size:0.82rem;border-bottom:1px solid {_t["BORDER"]};">'
                            f'<span style="color:{_color};font-weight:600;">{_icon} {_status}</span>'
                            f'&nbsp;&nbsp;·&nbsp;&nbsp;<span style="{_pill}">{_agent}</span>{_ns_part}'
                            f'&nbsp;&nbsp;{score_pill}'
                            f'&nbsp;&nbsp;&nbsp;<span style="color:{_muted};font-size:0.75rem;">{_created}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with _col_btn:
                        _confirm_key = f"confirm_del_{_run_id}"
                        if st.session_state.get(_confirm_key):
                            if st.button("✓", key=f"del_confirm_{_run_id}", help="Confirm delete"):
                                resp = api_post(f"/agents/runs/{_run_id}", method="DELETE")
                                st.session_state.pop(_confirm_key, None)
                                if resp is not None:
                                    st.rerun()
                                else:
                                    st.error("Delete failed")
                        else:
                            if st.button("🗑️", key=f"del_run_{_run_id}", help="Delete this failed run"):
                                st.session_state[_confirm_key] = True
                                st.rerun()
                else:
                    st.markdown(
                        f'<div style="padding:7px 0;font-size:0.82rem;border-bottom:1px solid {_t["BORDER"]};">'
                        f'<span style="color:{_color};font-weight:600;">{_icon} {_status}</span>'
                        f'&nbsp;&nbsp;·&nbsp;&nbsp;<span style="{_pill}">{_agent}</span>{_ns_part}'
                        f'&nbsp;&nbsp;{score_pill}'
                        f'&nbsp;&nbsp;&nbsp;<span style="color:{_muted};font-size:0.75rem;">{_created}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
    else:
        from dashboard.components.brand import empty_state
        empty_state(
            icon="🤖",
            title=f"Welcome, {username}!",
            body="No agent runs yet. Use Quick Dispatch on the right or go to Agents → Chat.",
        )

    if live_on:
        import time
        time.sleep(8)
        st.rerun()


def _render_live_refresh_toggle() -> None:
    """Token burn rate mini-chart."""
    from dashboard.components.brand import get_theme_vars
    t = get_theme_vars()
    st.markdown(
        f'<div style="color:{t["TEXT_MUTED"]};font-size:0.75rem;text-align:center;">'
        f'Auto-refresh: toggle "Live Activity" above · Quality scores powered by LLM-as-Judge</div>',
        unsafe_allow_html=True,
    )
