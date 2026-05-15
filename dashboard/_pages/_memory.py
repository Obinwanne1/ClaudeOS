"""Memory page — namespace tabs, FTS+semantic search, add entry form."""
import streamlit as st
from dashboard.components.brand import get_theme_vars


NAMESPACES = ["global", "reci-transport", "ivycandy-hair", "faiyke-ai", "personal"]
CATEGORIES = ["fact", "decision", "context", "preference", "reminder", "insight"]


def render(api_get, api_post):
    st.title("🧠 Memory")

    # Stats bar
    ns_data = api_get("/memory/namespaces")
    counts = ns_data.get("namespaces", {}) if ns_data else {}
    total = sum(counts.values())
    st.markdown(f"**{total} total entries** across {len(counts)} namespaces")

    col1, col2, col3, col4, col5 = st.columns(5)
    for col, ns in zip([col1, col2, col3, col4, col5], NAMESPACES):
        col.metric(ns, counts.get(ns, 0))

    st.markdown("---")

    tab_search, tab_browse, tab_add = st.tabs(["Search", "Browse", "Add Entry"])

    # ── Search ──────────────────────────────────────────────────────────────
    with tab_search:
        s_col1, s_col2, s_col3 = st.columns([3, 1, 1])
        with s_col1:
            query = st.text_input("Search memory", placeholder="e.g. brand color, RECI fleet, client contact...", label_visibility="collapsed")
        with s_col2:
            mode = st.selectbox("Mode", ["text", "semantic", "both"], label_visibility="collapsed")
        with s_col3:
            search_ns = st.selectbox("Namespace", ["(any)"] + NAMESPACES, label_visibility="collapsed")

        if query.strip():
            payload = {
                "query": query,
                "mode": mode,
                "top_k": 10,
            }
            if search_ns != "(any)":
                payload["namespace"] = search_ns

            result = api_post("/memory/search", payload)
            if result:
                entries = result.get("results", [])
                st.markdown(f"**{len(entries)} results** for `{query}` (mode: {mode})")
                for e in entries:
                    _render_entry_card(e)
            else:
                st.error("Search failed")

    # ── Browse ───────────────────────────────────────────────────────────────
    with tab_browse:
        b_col1, b_col2, b_col3 = st.columns(3)
        with b_col1:
            browse_ns = st.selectbox("Namespace", ["(all)"] + NAMESPACES, key="browse_ns")
        with b_col2:
            browse_cat = st.selectbox("Category", ["(all)"] + CATEGORIES, key="browse_cat")
        with b_col3:
            min_conf = st.slider("Min confidence", 0.0, 1.0, 0.0, 0.1)

        params = f"?limit=50&min_confidence={min_conf}"
        if browse_ns != "(all)":
            params += f"&namespace={browse_ns}"
        if browse_cat != "(all)":
            params += f"&category={browse_cat}"

        data = api_get(f"/memory{params}")
        if data:
            entries = data.get("entries", [])
            st.markdown(f"**{len(entries)} entries**")
            for e in entries:
                _render_entry_card(e)
        else:
            st.error("Failed to load entries")

    # ── Add Entry ────────────────────────────────────────────────────────────
    with tab_add:
        a_col1, a_col2 = st.columns(2)
        with a_col1:
            add_ns = st.selectbox("Namespace", NAMESPACES, key="add_ns")
            add_cat = st.selectbox("Category", CATEGORIES, key="add_cat")
            add_key = st.text_input("Key", placeholder="e.g. client.contact_email")
            add_conf = st.slider("Confidence", 0.0, 1.0, 1.0, 0.05)
        with a_col2:
            add_value = st.text_area("Value", height=150)
            add_tags = st.text_input("Tags (comma-separated)", placeholder="e.g. client, contact, email")

        if st.button("Save to Memory", type="primary"):
            if add_key.strip() and add_value.strip():
                tags = [t.strip() for t in add_tags.split(",") if t.strip()]
                result = api_post("/memory", {
                    "namespace": add_ns,
                    "category": add_cat,
                    "key": add_key,
                    "value": add_value,
                    "tags": tags,
                    "confidence": add_conf,
                    "source": "dashboard",
                })
                if result:
                    st.success(f"Saved: `{add_key}` → `{add_value[:60]}...`" if len(add_value) > 60 else f"Saved: `{add_key}`")
                else:
                    st.error("Save failed")
            else:
                st.warning("Key and Value are required")

    # Import button
    st.markdown("---")
    if st.button("Import from .claude/memory/"):
        result = api_post("/memory/import", {})
        if result:
            st.success(f"Imported {result.get('imported',0)}/{result.get('total_files',0)} files")
        else:
            st.error("Import failed")


def _render_entry_card(e: dict):
    cat_colors = {
        "fact": "#407E3C", "decision": "#3b82f6", "context": "#f59e0b",
        "preference": "#8b5cf6", "reminder": "#ef4444", "insight": "#14b8a6",
    }
    cat = e.get("category", "fact")
    color = cat_colors.get(cat, "#407E3C")
    conf = e.get("confidence", 1.0)
    tags = e.get("tags", [])
    value_preview = (e.get("value", "") or "")[:200]

    with st.expander(f"**{e.get('key','?')}** · `{e.get('namespace','?')}`", expanded=False):
        st.markdown(f"""
<div style="display:flex;gap:8px;margin-bottom:8px;align-items:center;">
  <span style="background:{color}33;color:{color};border:1px solid {color}55;
               padding:1px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;">{cat.upper()}</span>
  <span style="color:{get_theme_vars()['TEXT_MUTED']};font-size:0.8rem;">confidence: {conf:.0%}</span>
  {' '.join(f'<span class="tag-chip">{t}</span>' for t in tags)}
</div>
""", unsafe_allow_html=True)
        st.markdown(value_preview + ("..." if len(e.get("value","")) > 200 else ""))
        created = (e.get("created_at") or "")[:16]
        st.caption(f"ID: `{e.get('id','')[:8]}...` · Created: {created}")
