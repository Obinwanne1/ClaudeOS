"""Client Usage Dashboard — Namespace Pulse Score + AI activity metrics.

Visible to client/viewer roles only. Shows:
- AI Activity Summary (tokens, cost, runs, outputs)
- Namespace Pulse Score (composite 0–100)
- Recent activity feed
- Memory summary
"""
import streamlit as st
from dashboard.components.brand import aurora_hero, get_theme_vars, get_ns_brand


def render(api_get, api_post, bulk_delete=None):
    ns = st.session_state.get("user_namespace")
    role = st.session_state.get("user_role", "viewer")

    # Admins/operators use Observability page — this page is client-only
    if role in ("admin", "operator"):
        st.info("Admins: use the **Observability** page for full system metrics.")
        return

    brand = get_ns_brand()
    company = (brand.get("company_name") or ns or "Your Workspace").strip()
    icon = (brand.get("icon") or "🏢").strip()

    aurora_hero(
        title=f"{icon} {company}",
        subtitle="AI usage analytics — costs, quality, and workspace health.",
        pill="Usage · Last 30 days",
    )

    if not ns:
        st.warning("No namespace assigned to your account. Contact your admin.")
        return

    data = api_get(f"/system/namespace-stats?namespace={ns}")
    if not data:
        st.error("Could not load usage data — API may be offline.")
        return

    t = get_theme_vars()

    # ── KPI row ──────────────────────────────────────────────────────────────
    tok_in  = data.get("tokens_in", 0)
    tok_out = data.get("tokens_out", 0)
    cost    = data.get("cost_usd", 0.0)
    runs    = data.get("run_count", 0)
    outputs = data.get("output_count", 0)
    eval_avg = data.get("eval_avg", 0.0)

    kpis = [
        ("AI Runs (30d)",    runs,                          None),
        ("Tokens In",        f"{tok_in:,}",                 None),
        ("Tokens Out",       f"{tok_out:,}",                None),
        ("Est. Cost",        f"${cost:.3f}",                "USD · Sonnet 4.6"),
        ("Avg Quality",      f"{eval_avg:.1f}/5",           None),
        ("Outputs",          outputs,                       None),
    ]
    cards = ""
    for label, value, delta in kpis:
        d = (f'<div style="font-size:0.7rem;color:{t["TEXT_MUTED"]};margin-top:2px;">{delta}</div>'
             if delta else "")
        cards += (
            f'<div style="background:{t["SURFACE"]};border:1px solid {t["BORDER"]};'
            f'border-radius:10px;padding:14px 16px;min-width:0;">'
            f'<div style="font-size:0.78rem;color:{t["TEXT_MUTED"]};font-weight:500;'
            f'margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{label}</div>'
            f'<div style="font-size:1.9rem;font-weight:700;color:{t["TEXT"]};line-height:1.1;">{value}</div>'
            f'{d}</div>'
        )
    st.markdown(f'<div class="cos-kpi-grid">{cards}</div>', unsafe_allow_html=True)

    st.markdown("---")

    col_pulse, col_feed = st.columns([1, 2])

    # ── Namespace Pulse Score ─────────────────────────────────────────────────
    with col_pulse:
        st.subheader("Namespace Pulse")
        pulse = data.get("pulse_score", 0.0)
        _pulse_color = (
            "#5a9e56" if pulse >= 75
            else ("#f59e0b" if pulse >= 50 else "#ef4444")
        )
        _pulse_label = (
            "Excellent" if pulse >= 85
            else ("Good" if pulse >= 70 else ("Fair" if pulse >= 50 else "Needs Attention"))
        )

        # Circular gauge (pure HTML/CSS — no chart lib)
        _radius = 54
        _circ   = 2 * 3.14159 * _radius
        _dash   = _circ * (pulse / 100)
        _gap    = _circ - _dash
        st.markdown(
            f'<div style="display:flex;flex-direction:column;align-items:center;'
            f'padding:16px 0 8px;">'
            f'<svg width="140" height="140" viewBox="0 0 140 140">'
            f'<circle cx="70" cy="70" r="{_radius}" fill="none" '
            f'stroke="{t["BORDER"]}" stroke-width="12"/>'
            f'<circle cx="70" cy="70" r="{_radius}" fill="none" '
            f'stroke="{_pulse_color}" stroke-width="12" '
            f'stroke-dasharray="{_dash:.1f} {_gap:.1f}" '
            f'stroke-dashoffset="{_circ * 0.25:.1f}" stroke-linecap="round"/>'
            f'<text x="70" y="66" text-anchor="middle" dominant-baseline="middle" '
            f'font-size="22" font-weight="800" fill="{_pulse_color}" '
            f'font-family="Poppins,sans-serif">{pulse:.0f}</text>'
            f'<text x="70" y="84" text-anchor="middle" dominant-baseline="middle" '
            f'font-size="10" fill="{t["TEXT_MUTED"]}" font-family="Poppins,sans-serif">/ 100</text>'
            f'</svg>'
            f'<div style="font-size:0.95rem;font-weight:700;color:{_pulse_color};'
            f'margin-top:4px;">{_pulse_label}</div>'
            f'<div style="font-size:0.72rem;color:{t["TEXT_MUTED"]};margin-top:2px;'
            f'text-align:center;">Composite workspace health</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Score breakdown
        t_total  = data.get("ticket_total", 0)
        t_closed = data.get("tickets_closed", 0)
        m_total  = data.get("memory_count", 0)
        m_fresh  = data.get("memory_fresh", 0)
        wf_total = data.get("workflow_total", 0)
        wf_ok    = data.get("workflow_ok", 0)

        _dims = [
            ("Quality Score",  f"{eval_avg:.1f}/5",           "40%"),
            ("Ticket Resolve", f"{t_closed}/{t_total}",        "30%"),
            ("Memory Fresh",   f"{m_fresh}/{m_total} entries", "20%"),
            ("Workflow OK",    f"{wf_ok}/{wf_total} runs",     "10%"),
        ]
        for dim, val, weight in _dims:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:center;padding:3px 0;font-size:0.78rem;">'
                f'<span style="color:{t["TEXT_MUTED"]};">{dim}</span>'
                f'<span style="color:{t["TEXT"]};font-weight:600;">{val}</span>'
                f'<span style="color:{t["TEXT_MUTED"]};font-size:0.68rem;">{weight}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Recent Activity Feed ──────────────────────────────────────────────────
    with col_feed:
        st.subheader("Recent AI Activity")
        recent = data.get("recent_runs", [])
        if recent:
            for run in recent:
                _status = run.get("status", "?")
                _icon_map = {"done": "✅", "failed": "❌", "running": "⏳", "pending": "⏸️"}
                _icon_r = _icon_map.get(_status, "•")
                _color_map = {"done": "#5a9e56", "failed": "#ef4444",
                              "running": "#f59e0b", "pending": "#6b7280"}
                _col = _color_map.get(_status, "#6b7280")
                _agent = (run.get("agent_id") or "")[:14]
                _raw = run.get("created_at", "")
                _dur = run.get("duration_ms")
                _es  = run.get("eval_score")

                try:
                    from datetime import datetime as _dt
                    _p = _dt.fromisoformat(_raw.replace("Z", ""))
                    _ts = f"{_p.day} {_p.strftime('%b')} · {_p.strftime('%H:%M')}"
                except Exception:
                    _ts = _raw[:16]

                _dur_str = f"{_dur / 1000:.1f}s" if _dur else ""
                _score_pill = ""
                if _es is not None:
                    _sc = "#5a9e56" if _es >= 4 else ("#f59e0b" if _es >= 2.5 else "#ef4444")
                    _score_pill = (
                        f'<span style="background:{_sc}22;color:{_sc};border:1px solid {_sc}44;'
                        f'padding:1px 6px;border-radius:8px;font-size:0.7rem;">⭐{_es:.1f}</span>'
                    )
                _pill = (
                    f'background:{t["SURFACE2"]};color:{t["TEXT"]};'
                    f'padding:1px 6px;border-radius:4px;font-size:0.78rem;font-family:monospace;'
                )
                st.markdown(
                    f'<div style="padding:7px 0;font-size:0.82rem;'
                    f'border-bottom:1px solid {t["BORDER"]};">'
                    f'<span style="color:{_col};font-weight:600;">{_icon_r} {_status}</span>'
                    f'&nbsp;·&nbsp;<span style="{_pill}">{_agent}</span>'
                    f'&nbsp;{_score_pill}'
                    f'<span style="float:right;color:{t["TEXT_MUTED"]};font-size:0.75rem;">'
                    f'{_ts}{(" · " + _dur_str) if _dur_str else ""}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No AI runs yet. Use **Agents → Chat** to get started.")

        # Memory summary
        st.markdown("---")
        st.subheader("Memory Summary")
        last_cons = data.get("last_consolidated")
        _cons_str = last_cons[:10] if last_cons else "Never"
        st.markdown(
            f'<div style="display:flex;gap:24px;flex-wrap:wrap;">'
            f'<div style="text-align:center;">'
            f'<div style="font-size:1.6rem;font-weight:700;color:{t["TEXT"]};">{m_total}</div>'
            f'<div style="font-size:0.75rem;color:{t["TEXT_MUTED"]};">Total Entries</div>'
            f'</div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:1.6rem;font-weight:700;color:#5a9e56;">{m_fresh}</div>'
            f'<div style="font-size:0.75rem;color:{t["TEXT_MUTED"]};">Fresh (7d)</div>'
            f'</div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:1rem;font-weight:600;color:{t["TEXT_MUTED"]};">{_cons_str}</div>'
            f'<div style="font-size:0.75rem;color:{t["TEXT_MUTED"]};">Last Consolidated</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
