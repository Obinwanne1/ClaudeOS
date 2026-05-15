"""Settings page — Phase 7: Supabase Cloud Sync controls."""
from __future__ import annotations

import streamlit as st
from dashboard.components.brand import PRIMARY, get_theme_vars


def render(api_get, api_post):
    st.title("🔧  Settings")
    st.markdown("---")

    # ── Supabase Sync ──────────────────────────────────────────
    st.subheader("☁️  Supabase Cloud Sync")

    status = api_get("/sync/status", timeout=5)
    if status is None:
        st.error("API offline — cannot fetch sync status.")
        return

    configured = status.get("configured", False)
    last_sync = status.get("last_sync_at")
    table_states = status.get("table_states", {})
    auto_enabled = status.get("auto_sync_enabled", False)
    interval = status.get("auto_sync_interval_min", 15)

    # Connection status badge
    if configured:
        st.markdown(
            f'<span style="background:{PRIMARY};color:#fff;padding:3px 10px;border-radius:12px;font-size:0.8rem;">● Connected</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span style="background:#ef4444;color:#fff;padding:3px 10px;border-radius:12px;font-size:0.8rem;">● Not Configured</span>',
            unsafe_allow_html=True,
        )
        st.info("Add `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` to your `.env` file, then restart the server.")
        st.markdown("**Supabase schema** — run this SQL in your Supabase dashboard:")
        _show_schema_snippet()
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    total_pushed = sum(t.get("rows_pushed", 0) for t in table_states.values())
    total_failed = sum(t.get("rows_failed", 0) for t in table_states.values())
    col1.metric("Total Pushed", f"{total_pushed:,}")
    col2.metric("Total Failed", f"{total_failed:,}", delta=f"-{total_failed}" if total_failed else None, delta_color="inverse")
    col3.metric("Auto-sync", f"Every {interval}m" if auto_enabled else "Off")

    if last_sync:
        st.markdown(f'<div style="color:{get_theme_vars()["TEXT_MUTED"]};font-size:0.8rem;">Last sync: {last_sync}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Manual sync controls ───────────────────────────────────
    st.markdown("**Manual Controls**")
    c1, c2, c3 = st.columns(3)

    if c1.button("🔄 Push All Now", use_container_width=True, type="primary"):
        with st.spinner("Syncing…"):
            result = api_post("/sync/push", {})
        if result:
            pushed = result.get("total_pushed", 0)
            failed = result.get("total_failed", 0)
            ms = result.get("duration_ms", 0)
            if failed == 0:
                st.success(f"Pushed {pushed} rows in {ms}ms")
            else:
                st.warning(f"Pushed {pushed} rows, {failed} failed — check log below")
            st.rerun()
        else:
            st.error("Push failed — API error")

    table_options = list(table_states.keys())
    selected_table = c2.selectbox("Table", table_options, label_visibility="collapsed")
    if c3.button("Push Table", use_container_width=True):
        with st.spinner(f"Syncing {selected_table}…"):
            result = api_post("/sync/push", {"table": selected_table})
        if result:
            st.success(f"Pushed {result.get('rows_pushed', 0)} rows")
            st.rerun()
        else:
            st.error("Push failed")

    # ── Per-table state ────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Table Sync State**")
    rows = []
    for tname, ts in table_states.items():
        rows.append({
            "Table": tname,
            "Last Synced": ts.get("last_synced_at") or "Never",
            "Pushed": ts.get("rows_pushed", 0),
            "Failed": ts.get("rows_failed", 0),
            "Last Error": (ts.get("last_error") or "")[:60],
        })
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)

    # ── Reset watermark ────────────────────────────────────────
    with st.expander("⚠️  Reset Watermark (re-sync all)"):
        st.warning("Resetting forces a full re-push of all rows on next sync. Use only to recover from errors.")
        rc1, rc2 = st.columns(2)
        reset_table = rc1.selectbox("Table to reset", ["(all)"] + table_options, key="reset_sel")
        if rc2.button("Reset", type="secondary"):
            payload = {} if reset_table == "(all)" else {"table": reset_table}
            result = api_post("/sync/reset-watermark", payload)
            if result and result.get("ok"):
                st.success(f"Watermark reset for: {result.get('table', 'all')}")
                st.rerun()
            else:
                st.error("Reset failed")

    # ── Sync Log ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Sync Log** (last 30 runs)")
    log = api_get("/sync/log?limit=30", timeout=5)
    if log:
        st.dataframe(
            [
                {
                    "Started": r.get("started_at", "")[:19],
                    "Table": r.get("table_name"),
                    "OK": r.get("rows_ok", 0),
                    "Fail": r.get("rows_fail", 0),
                    "ms": r.get("duration_ms", 0),
                    "Error": (r.get("error") or "")[:50],
                }
                for r in log
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No sync runs yet.")

    # ── Schema helper ──────────────────────────────────────────
    st.markdown("---")
    with st.expander("📋  Supabase SQL Schema"):
        _show_schema_snippet()


def _show_schema_snippet():
    try:
        from pathlib import Path
        sql_path = Path(__file__).parent.parent.parent / "sync" / "supabase_schema.sql"
        if sql_path.exists():
            sql = sql_path.read_text(encoding="utf-8")
            st.code(sql, language="sql")
        else:
            st.warning("sync/supabase_schema.sql not found")
    except Exception as e:
        st.error(f"Could not load schema: {e}")
