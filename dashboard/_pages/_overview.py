"""Overview page — OS health, KPIs, live event feed, quick dispatch."""
import streamlit as st
from datetime import datetime


def render(api_get, api_post):
    st.title("ClaudeOS Overview")

    status = api_get("/system/status")
    stats = api_get("/system/stats")
    agents_data = api_get("/agents")
    counts = stats.get("counts", {}) if stats else {}

    # KPI row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Memory Entries", counts.get("memory_entries", 0))
    col2.metric("Agents", counts.get("agents", 0))
    col3.metric("Agent Runs", counts.get("agent_runs", 0))
    col4.metric("Workflows", counts.get("workflows", 0))
    col5.metric("Outputs", counts.get("outputs", 0))

    st.markdown("---")

    col_left, col_right = st.columns([2, 1])

    with col_left:
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

        # Live event feed
        st.subheader("Recent Events")
        events_data = api_get("/system/events") if hasattr(api_get, "__call__") else None
        # Fallback: show recent agent runs as events
        runs_data = api_get("/agents/runs?limit=10")
        if runs_data and runs_data.get("runs"):
            for run in runs_data["runs"][:8]:
                status_icon = {"done": "✅", "failed": "❌", "running": "⏳", "pending": "⏸️"}.get(run.get("status", ""), "•")
                agent_id = run.get("agent_id", "")[:8]
                ns = run.get("namespace", "global")
                created = run.get("created_at", "")[:16] if run.get("created_at") else ""
                st.markdown(f"`{status_icon} {run.get('status','?'):8}` · agent `{agent_id}` · `{ns}` · {created}")
        else:
            st.caption("No runs yet.")

    with col_right:
        st.subheader("Quick Dispatch")
        if agents_data and agents_data.get("agents"):
            agent_names = [a["name"] for a in agents_data["agents"]]
            selected_agent = st.selectbox("Agent", agent_names, key="quick_agent")
            selected_ns = st.selectbox("Namespace", ["global", "reci-transport", "ivycandy-hair", "faiyke-ai", "personal"], key="quick_ns")
            prompt = st.text_area("Prompt", height=100, key="quick_prompt", placeholder="What should this agent do?")

            if st.button("Run Agent", width='stretch'):
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

        # Namespace counts from memory
        ns_data = api_get("/memory/namespaces")
        if ns_data and ns_data.get("namespaces"):
            st.subheader("Memory by Namespace")
            for ns, cnt in sorted(ns_data["namespaces"].items(), key=lambda x: -x[1]):
                st.markdown(f"**{ns}** — {cnt} entries")
