"""Agents page — catalog grid, dispatch modal, run history."""
import streamlit as st
from dashboard.components.brand import PRIMARY, PRIMARY_LIGHT, SURFACE, badge, get_theme_vars


CATEGORY_COLORS = {
    "ops": "#407E3C",
    "research": "#3b82f6",
    "content": "#8b5cf6",
    "analysis": "#f59e0b",
    "comms": "#ec4899",
    "system": "#6b7280",
    "engineering": "#ef4444",
    "domain": "#14b8a6",
}


def render(api_get, api_post):
    st.title("🤖 Agents")

    agents_data = api_get("/agents?enabled_only=false")
    if not agents_data:
        st.error("API unreachable")
        return

    agents = agents_data.get("agents", [])
    if not agents:
        st.info("No agents registered. Run `python scripts/seed_agents.py`")
        return

    # Filter bar
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Search agents", placeholder="name, category, tag...", label_visibility="collapsed")
    with col2:
        cats = ["All"] + sorted({a["category"] for a in agents})
        cat_filter = st.selectbox("Category", cats, label_visibility="collapsed")

    filtered = agents
    if search:
        q = search.lower()
        filtered = [a for a in filtered if q in a["name"] or q in a["description"] or q in a["category"] or any(q in t for t in a.get("tags", []))]
    if cat_filter != "All":
        filtered = [a for a in filtered if a["category"] == cat_filter]

    st.markdown(f"**{len(filtered)}** agents", unsafe_allow_html=True)
    st.markdown("---")

    # Agent grid
    for i in range(0, len(filtered), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(filtered):
                break
            a = filtered[i + j]
            color = CATEGORY_COLORS.get(a["category"], PRIMARY)
            with col:
                with st.container():
                    tv = get_theme_vars()
                    st.markdown(f"""
<div class="agent-card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <strong style="color:{tv['TEXT']};">{a['display_name']}</strong>
    <span style="background:{color}33;color:{color};border:1px solid {color}55;
                 padding:2px 8px;border-radius:12px;font-size:0.7rem;font-weight:600;">
      {a['category'].upper()}
    </span>
  </div>
  <div style="color:{tv['TEXT_MUTED']};font-size:0.85rem;margin-bottom:8px;">{a['description']}</div>
  <div style="font-size:0.75rem;color:{tv['TEXT_MUTED']};">
    model: <code>{a['model']}</code> · max_tokens: {a['max_tokens']}
    {f" · 🔒 {a['namespace_lock']}" if a.get('namespace_lock') else ""}
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # Dispatch panel
    st.subheader("Dispatch Agent")
    d_col1, d_col2 = st.columns([1, 2])
    with d_col1:
        agent_names = [a["name"] for a in agents]
        sel_agent = st.selectbox("Agent", agent_names, key="dispatch_agent")
        _role = st.session_state.get("user_role", "admin")
        _user_ns = st.session_state.get("user_namespace")
        _ns_opts = [_user_ns] if _role in ("client", "viewer") and _user_ns else ["global", "reci-transport", "ivycandy-hair", "faiyke-ai", "personal"]
        sel_ns = st.selectbox("Namespace", _ns_opts, key="dispatch_ns")
        save_out = st.checkbox("Save output", value=True)
    with d_col2:
        dispatch_prompt = st.text_area("Prompt", height=150, key="dispatch_prompt")
        if st.button("Dispatch", width='stretch', type="primary"):
            if dispatch_prompt.strip():
                result = api_post(f"/agents/{sel_agent}/run", {
                    "prompt": dispatch_prompt,
                    "namespace": sel_ns,
                    "save_output": save_out,
                })
                if result:
                    st.success(f"Run started: `{result.get('run_id','?')}`")
                    st.session_state["last_run_id"] = result.get("run_id")
                else:
                    st.error("Dispatch failed")
            else:
                st.warning("Enter a prompt")

    # Run status — auto-polls until done/failed
    if st.session_state.get("last_run_id"):
        import time as _time
        import re as _re
        run_id = st.session_state["last_run_id"]
        # Use uncached api_get so status is always fresh
        run = api_get(f"/agents/runs/{run_id}")
        if run:
            status = run.get("status", "?")
            icons = {"done": "✅", "failed": "❌", "running": "⏳", "pending": "⏸️"}
            st.write(f"{icons.get(status, '•')} Status: **{status}**")
            if status in ("running", "pending"):
                st.info("Agent running… auto-refreshing every 5s")
                _time.sleep(5)
                st.rerun()
            if run.get("output") and run["output"].get("text"):
                st.markdown("**Output:**")
                raw = run["output"]["text"].strip()
                raw = _re.sub(r"^```[a-zA-Z]*\n?", "", raw)
                raw = _re.sub(r"\n?```$", "", raw)
                st.code(raw.strip(), language="json" if raw.strip().startswith("{") else None)
            if run.get("error"):
                st.error(run["error"])
            st.caption(f"Tokens: {run.get('tokens_in',0)} in + {run.get('tokens_out',0)} out · {run.get('duration_ms',0)}ms")
            if status in ("done", "failed") and st.button("Clear"):
                del st.session_state["last_run_id"]
                st.rerun()

    st.markdown("---")

    # Recent runs table
    st.subheader("Recent Runs")
    _runs_role = st.session_state.get("user_role", "admin")
    _runs_ns = st.session_state.get("user_namespace")
    _runs_url = f"/agents/runs?limit=20&namespace={_runs_ns}" if _runs_role in ("client", "viewer") and _runs_ns else "/agents/runs?limit=20"
    runs_data = api_get(_runs_url)
    if runs_data and runs_data.get("runs"):
        rows = []
        for r in runs_data["runs"]:
            rows.append({
                "Run ID": r.get("id","")[:8] + "...",
                "Agent": r.get("agent_id","")[:12],
                "Namespace": r.get("namespace",""),
                "Status": r.get("status",""),
                "Tokens": f"{r.get('tokens_in',0)}+{r.get('tokens_out',0)}",
                "Duration": f"{r.get('duration_ms') or 0}ms",
                "Started": (r.get("created_at") or "")[:16],
            })
        st.dataframe(rows, width='stretch')
    else:
        st.caption("No runs yet.")
