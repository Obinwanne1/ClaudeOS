"""Observability page — Phase 10.2: Traces, latency, quality trends.

Shows per-agent quality scores, latency percentiles, token costs,
and eval dimension breakdowns. Powered by the LLM-as-Judge eval system.
"""
from __future__ import annotations

import json
import streamlit as st
from dashboard.components.brand import PRIMARY, get_theme_vars


def render(api_get, api_post, bulk_delete=None):
    st.title("🔭 Observability")
    tv = get_theme_vars()

    role = st.session_state.get("user_role", "viewer")
    user_ns = st.session_state.get("user_namespace")
    is_scoped = role in ("client", "viewer") and bool(user_ns)

    tab_quality, tab_latency, tab_tokens, tab_memory = st.tabs(
        ["⭐ Quality Scores", "⏱ Latency", "💰 Token Cost", "🧠 Memory Health"]
    )

    # Fetch run data
    _runs_url = (
        f"/agents/runs?limit=100&namespace={user_ns}" if is_scoped
        else "/agents/runs?limit=100"
    )
    runs_data = api_get(_runs_url) or {}
    runs = runs_data.get("runs", [])

    with tab_quality:
        _render_quality(runs, tv)

    with tab_latency:
        _render_latency(runs, tv)

    with tab_tokens:
        _render_tokens(runs, tv)

    with tab_memory:
        _render_memory_health(api_get, tv)


def _render_quality(runs: list, tv: dict) -> None:
    st.subheader("Agent Quality Scores")

    scored = [r for r in runs if r.get("eval_score") is not None]
    if not scored:
        st.info(
            "No quality scores yet. Scores appear automatically after each agent run "
            "(powered by LLM-as-Judge using Claude Haiku)."
        )
        return

    # Per-agent average scores
    from collections import defaultdict
    agent_scores: dict[str, list] = defaultdict(list)
    for r in scored:
        agent_id = (r.get("agent_id") or "unknown")[:20]
        agent_scores[agent_id].append(float(r["eval_score"]))

    st.markdown("**Average quality by agent (last 100 runs)**")
    rows = []
    for agent, scores in sorted(agent_scores.items(), key=lambda x: -sum(x[1])/len(x[1])):
        avg = sum(scores) / len(scores)
        mn = min(scores)
        mx = max(scores)
        color = "#5a9e56" if avg >= 4 else ("#f59e0b" if avg >= 2.5 else "#ef4444")
        rows.append({
            "Agent": agent,
            "Avg Score": f"{avg:.2f}/5",
            "Min": f"{mn:.1f}",
            "Max": f"{mx:.1f}",
            "Runs Scored": len(scores),
        })
    st.dataframe(rows, use_container_width=True)

    # Quality alert
    low_quality = [(a, sum(s)/len(s)) for a, s in agent_scores.items() if sum(s)/len(s) < 2.5]
    if low_quality:
        for agent, avg in low_quality:
            st.warning(f"⚠️ Agent **{agent}** avg quality {avg:.1f}/5 — below threshold")

    st.markdown("---")
    st.markdown("**Score distribution**")
    score_vals = [r["eval_score"] for r in scored]
    buckets = {"5 (Excellent)": 0, "4 (Good)": 0, "3 (Fair)": 0, "2 (Poor)": 0, "1 (Bad)": 0}
    for s in score_vals:
        if s >= 4.5:
            buckets["5 (Excellent)"] += 1
        elif s >= 3.5:
            buckets["4 (Good)"] += 1
        elif s >= 2.5:
            buckets["3 (Fair)"] += 1
        elif s >= 1.5:
            buckets["2 (Poor)"] += 1
        else:
            buckets["1 (Bad)"] += 1

    try:
        import plotly.graph_objects as go
        fig = go.Figure(go.Bar(
            x=list(buckets.keys()),
            y=list(buckets.values()),
            marker_color=[PRIMARY, "#5a9e56", "#f59e0b", "#ef4444", "#991b1b"],
        ))
        fig.update_layout(
            plot_bgcolor=tv["PLOT_BG"],
            paper_bgcolor=tv["PLOT_BG"],
            font_color=tv["TEXT"],
            margin=dict(l=0, r=0, t=10, b=0),
            height=250,
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        for bucket, count in buckets.items():
            st.markdown(f"**{bucket}:** {count}")

    # Eval dimension breakdown
    st.markdown("---")
    st.markdown("**Average eval dimensions (last 100 scored runs)**")
    dim_totals = {"task_completion": [], "factual_grounding": [], "conciseness": [], "safety": []}
    for r in scored:
        try:
            dims = json.loads(r.get("eval_dimensions") or "{}")
            for k in dim_totals:
                if k in dims:
                    dim_totals[k].append(float(dims[k]))
        except Exception:
            pass

    dim_cols = st.columns(4)
    dim_labels = {
        "task_completion": "Task Completion",
        "factual_grounding": "Factual Grounding",
        "conciseness": "Conciseness",
        "safety": "Safety",
    }
    for i, (k, vals) in enumerate(dim_totals.items()):
        avg = sum(vals) / len(vals) if vals else 0
        dim_cols[i].metric(dim_labels[k], f"{avg:.2f}/5" if k != "safety" else f"{avg:.0%}")


def _render_latency(runs: list, tv: dict) -> None:
    st.subheader("Response Latency")
    timed = [r for r in runs if r.get("duration_ms") and r.get("status") == "done"]
    if not timed:
        st.info("No completed runs with timing data yet.")
        return

    durations = sorted([r["duration_ms"] for r in timed])
    n = len(durations)
    p50 = durations[n // 2]
    p95 = durations[int(n * 0.95)]
    p99 = durations[int(n * 0.99)] if n >= 100 else durations[-1]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("p50 Latency", f"{p50:,}ms")
    c2.metric("p95 Latency", f"{p95:,}ms")
    c3.metric("p99 Latency", f"{p99:,}ms")
    c4.metric("Avg Latency", f"{sum(durations)//len(durations):,}ms")

    # Per-agent latency
    from collections import defaultdict
    agent_ms: dict[str, list] = defaultdict(list)
    for r in timed:
        agent_ms[(r.get("agent_id") or "?")[:16]].append(r["duration_ms"])

    st.markdown("**Avg latency by agent**")
    rows = sorted(
        [{"Agent": a, "Avg ms": f"{sum(ms)//len(ms):,}", "Runs": len(ms)}
         for a, ms in agent_ms.items()],
        key=lambda x: -int(x["Avg ms"].replace(",", "")),
    )
    st.dataframe(rows, use_container_width=True)


def _render_tokens(runs: list, tv: dict) -> None:
    st.subheader("Token Usage & Cost")
    done = [r for r in runs if r.get("status") == "done"]
    if not done:
        st.info("No completed runs yet.")
        return

    total_in = sum(r.get("tokens_in", 0) for r in done)
    total_out = sum(r.get("tokens_out", 0) for r in done)
    # Sonnet 4.6 pricing: $3/M input, $15/M output (approx)
    cost_usd = (total_in / 1_000_000 * 3.0) + (total_out / 1_000_000 * 15.0)

    c1, c2, c3 = st.columns(3)
    c1.metric("Input Tokens", f"{total_in:,}")
    c2.metric("Output Tokens", f"{total_out:,}")
    c3.metric("Est. Cost (USD)", f"${cost_usd:.4f}")

    # Per-agent token breakdown
    from collections import defaultdict
    agent_tokens: dict[str, dict] = defaultdict(lambda: {"in": 0, "out": 0, "runs": 0})
    for r in done:
        a = (r.get("agent_id") or "?")[:16]
        agent_tokens[a]["in"] += r.get("tokens_in", 0)
        agent_tokens[a]["out"] += r.get("tokens_out", 0)
        agent_tokens[a]["runs"] += 1

    rows = []
    for agent, t in sorted(agent_tokens.items(), key=lambda x: -(x[1]["in"] + x[1]["out"])):
        agent_cost = (t["in"] / 1_000_000 * 3.0) + (t["out"] / 1_000_000 * 15.0)
        rows.append({
            "Agent": agent,
            "Input Tokens": f"{t['in']:,}",
            "Output Tokens": f"{t['out']:,}",
            "Est. Cost": f"${agent_cost:.4f}",
            "Runs": t["runs"],
        })
    st.dataframe(rows, use_container_width=True)
    st.caption("Pricing based on Claude Sonnet 4.6 rates (~$3/M input, ~$15/M output). Actual costs may vary.")


def _render_memory_health(api_get, tv: dict) -> None:
    st.subheader("Memory System Health")

    ns_data = api_get("/memory/namespaces") or {}
    namespaces = ns_data.get("namespaces", {})

    if not namespaces:
        st.info("No memory entries found.")
        return

    total_entries = sum(namespaces.values())
    c1, c2 = st.columns(2)
    c1.metric("Total Memory Entries", total_entries)
    c2.metric("Namespaces", len(namespaces))

    st.markdown("**Entries by namespace**")
    rows = [{"Namespace": ns, "Entries": cnt}
            for ns, cnt in sorted(namespaces.items(), key=lambda x: -x[1])]
    st.dataframe(rows, use_container_width=True)

    st.markdown("---")
    st.markdown("**Memory Consolidation**")
    st.markdown(
        "The consolidation engine runs every 4 hours, compressing episodic entries "
        "into semantic summaries. Archived entries are preserved, not deleted."
    )
    if st.button("Run Consolidation Now", type="primary"):
        result = api_post("/memory/consolidate", {})
        if result:
            st.success(
                f"Consolidation complete: "
                f"{result.get('clusters_found',0)} clusters found, "
                f"{result.get('entries_archived',0)} archived, "
                f"{result.get('entries_created',0)} summaries created."
            )
        else:
            st.error("Consolidation endpoint not available")
