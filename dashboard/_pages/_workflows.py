"""Workflows page — manage, trigger, and monitor workflow runs."""
import streamlit as st
from datetime import datetime


def render(api_get, api_post):
    st.title("Workflow Engine")

    tab_list, tab_runs, tab_scheduler = st.tabs(["Workflows", "Run History", "Scheduler"])

    with tab_list:
        _render_workflow_list(api_get, api_post)

    with tab_runs:
        _render_run_history(api_get)

    with tab_scheduler:
        _render_scheduler(api_get, api_post)


def _render_workflow_list(api_get, api_post):
    data = api_get("/workflows?enabled=false")
    if not data:
        st.error("API unreachable")
        return

    workflows = data if isinstance(data, list) else []
    if not workflows:
        st.info("No workflows found. Seed with `python scripts/seed_workflows.py`")
        return

    trigger_icons = {"schedule": "⏰", "manual": "▶️", "event": "⚡"}

    for wf in workflows:
        enabled = wf.get("enabled", True)
        icon = trigger_icons.get(wf.get("trigger_type", "manual"), "•")
        status_badge = "🟢" if enabled else "⚫"

        with st.expander(f"{status_badge} {icon} **{wf['display_name']}** — `{wf['name']}`"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(wf.get("description", ""))
                st.markdown(
                    f"**Trigger:** `{wf.get('trigger_type','manual')}`  "
                    f"**Namespace:** `{wf.get('namespace','global')}`  "
                    f"**Steps:** {wf.get('step_count', 0)}"
                )
                if wf.get("trigger_type") == "schedule" and wf.get("trigger_spec"):
                    spec = wf["trigger_spec"]
                    sched_str = (
                        f"{spec.get('day_of_week','*')} "
                        f"{spec.get('hour','0'):02}:{spec.get('minute','0'):02} "
                        f"{spec.get('timezone','')}"
                    )
                    st.markdown(f"**Schedule:** `{sched_str}`")

            with col2:
                # Manual trigger
                st.markdown("**Run now**")
                ns_key = f"ns_{wf['name']}"
                ns = st.selectbox(
                    "Namespace",
                    ["global", "reci-transport", "ivycandy-hair", "faiyke-ai", "personal"],
                    key=ns_key,
                    label_visibility="collapsed",
                )
                ctx_key = f"ctx_{wf['name']}"
                ctx_extra = st.text_input(
                    "Context (key=val,…)",
                    key=ctx_key,
                    placeholder="topic=AI,date=today",
                    label_visibility="collapsed",
                )
                if st.button("▶ Run", key=f"run_{wf['name']}", width='stretch'):
                    ctx = {"namespace": ns}
                    if ctx_extra.strip():
                        for pair in ctx_extra.split(","):
                            if "=" in pair:
                                k, v = pair.split("=", 1)
                                ctx[k.strip()] = v.strip()
                    result = api_post(f"/workflows/{wf['name']}/run", {"namespace": ns, "context": ctx})
                    if result:
                        st.success(f"Started `{result.get('run_id','?')[:8]}…`")
                    else:
                        st.error("Dispatch failed")

                toggle_label = "Disable" if enabled else "Enable"
                if st.button(toggle_label, key=f"toggle_{wf['name']}", width='stretch'):
                    api_post(
                        f"/workflows/{wf['name']}",
                        {"enabled": not enabled},
                        method="PATCH",
                    )
                    st.rerun()


def _render_run_history(api_get):
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Recent Runs")
    with col2:
        if st.button("↻ Refresh", width='stretch'):
            st.rerun()

    # Fetch all runs via a generic endpoint
    runs_data = api_get("/workflows/runs/all?limit=30") or []
    if not runs_data:
        st.info("No workflow runs yet.")
        return

    status_icons = {"done": "✅", "failed": "❌", "running": "⏳", "pending": "⏸️"}

    for run in runs_data[:30]:
        sicon = status_icons.get(run.get("status", ""), "•")
        wf_id = run.get("workflow_id", "")[:8]
        run_id = run.get("id", "")[:8]
        started = (run.get("started_at") or "")[:16]
        dur = run.get("duration_ms")
        dur_str = f"{dur}ms" if dur else "—"
        ns = run.get("context", {}).get("namespace", "global") if isinstance(run.get("context"), dict) else "global"

        with st.expander(f"{sicon} `{run_id}…` · workflow `{wf_id}…` · `{ns}` · {started} · {dur_str}"):
            steps = run.get("steps_log") or []
            if steps:
                step_rows = []
                for s in steps:
                    step_rows.append({
                        "Step": s.get("step_id", ""),
                        "Agent": s.get("agent_name", ""),
                        "Status": s.get("status", ""),
                        "Tokens": f"{s.get('tokens_in',0)}+{s.get('tokens_out',0)}",
                        "ms": s.get("duration_ms", 0),
                    })
                st.table(step_rows)
            if run.get("error"):
                st.error(run["error"])
            if run.get("output"):
                st.markdown("**Output preview:**")
                st.text(str(run["output"])[:500])


def _render_scheduler(api_get, api_post):
    st.subheader("Scheduled Jobs")
    jobs = api_get("/workflows/scheduler/jobs") or []

    if not jobs:
        st.info("No scheduled jobs active.")
    else:
        for job in jobs:
            next_run = job.get("next_run", "—")
            if next_run and next_run != "—":
                try:
                    dt = datetime.fromisoformat(next_run)
                    next_run = dt.strftime("%Y-%m-%d %H:%M %Z")
                except Exception:
                    pass
            st.markdown(f"⏰ **`{job['name']}`** — next run: `{next_run}`")
            st.caption(f"Trigger: {job.get('trigger','?')}")

    if st.button("Reload Scheduler from DB"):
        result = api_post("/workflows/scheduler/reload", {})
        if result:
            st.success(f"Reloaded. {len(result.get('jobs', []))} jobs active.")
        else:
            st.error("Reload failed")
