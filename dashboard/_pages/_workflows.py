"""Workflows page — manage, trigger, and monitor workflow runs."""
import streamlit as st
from datetime import datetime


def render(api_get, api_post, bulk_delete=None):
    st.title("⚙️ Workflow Engine")

    tab_list, tab_runs, tab_scheduler, tab_webhooks = st.tabs(["Workflows", "Run History", "Scheduler", "🔗 Webhooks"])

    with tab_list:
        _render_workflow_list(api_get, api_post)

    with tab_runs:
        _render_run_history(api_get)

    with tab_scheduler:
        _render_scheduler(api_get, api_post)

    with tab_webhooks:
        _render_webhooks(api_get, api_post)


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


def _render_webhooks(api_get, api_post):
    """Webhook trigger management — Phase 12.1."""
    from dashboard.components.brand import get_theme_vars, PRIMARY
    tv = get_theme_vars()

    st.subheader("🔗 Webhook Triggers")
    st.markdown(
        "Enable webhooks so external systems (GitHub, Stripe, Supabase, n8n) "
        "can trigger workflows via HTTP POST."
    )

    data = api_get("/workflows?enabled=false")
    workflows = data if isinstance(data, list) else []
    if not workflows:
        st.info("No workflows found.")
        return

    for wf in workflows:
        with st.expander(f"**{wf['display_name']}** — `{wf['name']}`"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**Trigger type:** `{wf.get('trigger_type','manual')}`")
                st.markdown(f"**Namespace:** `{wf.get('namespace','global')}`")

                # Show current webhook status
                webhook_info = api_get(f"/workflows/{wf['name']}")
                webhook_enabled = (webhook_info or {}).get("webhook_enabled", False)
                webhook_url = (webhook_info or {}).get("webhook_url")

                if webhook_enabled and webhook_url:
                    st.markdown(
                        f'<div style="background:{tv["SURFACE"]};border:1px solid #407E3C;'
                        f'border-radius:8px;padding:10px 14px;margin:8px 0;">'
                        f'<div style="color:#5a9e56;font-weight:600;margin-bottom:4px;">✅ Webhook Active</div>'
                        f'<code style="font-size:0.78rem;word-break:break-all;">{webhook_url}</code>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption("Include header: `X-Webhook-Secret: <your-secret>` in POST requests")
                    st.caption("Body: `{\"context\": {\"key\": \"value\"}}`")

            with col2:
                if webhook_enabled:
                    if st.button("🔄 Regenerate Secret", key=f"wh_regen_{wf['name']}", use_container_width=True):
                        result = api_post(f"/workflows/{wf['name']}/webhook/enable", {})
                        if result:
                            st.success("New secret generated!")
                            st.code(result.get("webhook_secret", ""), language=None)
                            st.rerun()
                    if st.button("❌ Disable", key=f"wh_dis_{wf['name']}", use_container_width=True):
                        api_post(f"/workflows/{wf['name']}/webhook/disable", {})
                        st.rerun()
                else:
                    if st.button("⚡ Enable Webhook", key=f"wh_en_{wf['name']}", use_container_width=True, type="primary"):
                        result = api_post(f"/workflows/{wf['name']}/webhook/enable", {})
                        if result:
                            st.success("Webhook enabled!")
                            st.markdown(f"**URL:** `{result.get('webhook_url','')}`")
                            st.markdown("**Secret** (save this — shown once):")
                            st.code(result.get("webhook_secret", ""), language=None)
                            st.caption(result.get("usage", ""))
                            st.rerun()
                        else:
                            st.error("Failed to enable webhook")

    st.markdown("---")
    st.markdown("**Example: trigger from curl**")
    st.code(
        'curl -X POST http://localhost:5000/api/v1/workflows/morning-briefing/trigger \\\n'
        '  -H "X-Webhook-Secret: your-secret-here" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"context": {"namespace": "global", "topic": "AI news"}}\'',
        language="bash",
    )
