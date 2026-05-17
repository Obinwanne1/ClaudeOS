"""Outputs page — browse, search, and export agent/workflow outputs."""
import os
import requests
import streamlit as st

_API_BASE = "http://localhost:5000/api/v1"

TYPE_ICONS = {
    "report": "📄",
    "draft": "✏️",
    "analysis": "🔍",
    "code": "💻",
    "note": "📝",
    "archive": "📦",
}


def render(api_get, api_post):
    st.title("Output Manager")

    tab_browse, tab_search, tab_stats = st.tabs(["Browse", "Search", "Stats"])

    with tab_browse:
        _render_browse(api_get, api_post)

    with tab_search:
        _render_search(api_get)

    with tab_stats:
        _render_stats(api_get)


def _render_browse(api_get, api_post):
    role = st.session_state.get("user_role", "admin")
    user_ns = st.session_state.get("user_namespace")

    col1, col2, col3 = st.columns(3)
    with col1:
        if role in ("client", "viewer") and user_ns:
            ns_filter = user_ns
            st.selectbox("Namespace", [user_ns], key="out_ns_filter", disabled=True)
        else:
            ns_data = api_get("/namespaces") or []
            ns_options = ["all"] + [n["slug"] for n in ns_data]
            ns_filter = st.selectbox("Namespace", ns_options, key="out_ns_filter")
    with col2:
        type_options = ["all", "report", "draft", "analysis", "code", "note", "archive"]
        type_filter = st.selectbox("Type", type_options, key="out_type_filter")
    with col3:
        limit = st.selectbox("Limit", [20, 50, 100], key="out_limit")

    url = f"/outputs?limit={limit}"
    if ns_filter != "all":
        url += f"&namespace={ns_filter}"
    if type_filter != "all":
        url += f"&type={type_filter}"

    outputs = api_get(url) or []

    if not outputs:
        st.info("No outputs found.")
        return

    st.caption(f"{len(outputs)} outputs")

    for out in outputs:
        icon = TYPE_ICONS.get(out.get("output_type", ""), "•")
        title = out.get("title", "Untitled")
        ns = out.get("namespace", "global")
        otype = out.get("output_type", "?")
        created = (out.get("created_at") or "")[:10]
        size_kb = round(out.get("size_bytes", 0) / 1024, 1)
        tags = out.get("tags") or []
        summary = out.get("summary") or ""
        oid = out.get("id", "")

        with st.expander(f"{icon} **{title}** · `{ns}` · {created}"):
            col_meta, col_actions = st.columns([3, 1])
            with col_meta:
                st.markdown(f"**Type:** `{otype}` · **Size:** {size_kb} KB")
                if tags:
                    tag_str = " ".join(f"`{t}`" for t in tags[:8])
                    st.markdown(f"**Tags:** {tag_str}")
                if summary:
                    st.caption(summary)

            with col_actions:
                if st.button("View", key=f"view_{oid}", width='stretch'):
                    st.session_state[f"show_content_{oid}"] = True
                # Fetch export only on demand — avoids N HTTP calls per render
                if st.button("⬇ Download MD", key=f"dl_btn_{oid}", width='stretch'):
                    _key = os.environ.get("CLAUDEOS_DEV_API_KEY", "")
                    _r = requests.get(
                        f"{_API_BASE}/outputs/{oid}/export?format=markdown",
                        headers={"X-API-Key": _key}, timeout=5,
                    )
                    if _r.ok:
                        fname = f"{title[:40].replace(' ','_')}.md"
                        st.download_button("Save", data=_r.text, file_name=fname,
                                           mime="text/markdown", key=f"dl_{oid}")
                if st.button("🗑 Delete", key=f"del_{oid}", width='stretch'):
                    st.session_state[f"confirm_delete_{oid}"] = True

            if st.session_state.get(f"confirm_delete_{oid}"):
                st.warning("Confirm delete?")
                c1, c2 = st.columns(2)
                if c1.button("Yes, delete", key=f"yes_del_{oid}"):
                    key = os.environ.get("CLAUDEOS_DEV_API_KEY", "")
                    requests.delete(
                        f"{_API_BASE}/outputs/{oid}",
                        headers={"X-API-Key": key},
                        timeout=5,
                    )
                    st.session_state.pop(f"confirm_delete_{oid}", None)
                    st.rerun()
                if c2.button("Cancel", key=f"cancel_del_{oid}"):
                    st.session_state.pop(f"confirm_delete_{oid}", None)
                    st.rerun()

            if st.session_state.get(f"show_content_{oid}"):
                content_data = api_get(f"/outputs/{oid}")
                if content_data:
                    st.markdown("---")
                    st.markdown(content_data.get("content", "*(no content)*"))
                if st.button("Hide", key=f"hide_{oid}"):
                    st.session_state.pop(f"show_content_{oid}", None)
                    st.rerun()


def _render_search(api_get):
    st.subheader("Full-Text Search")
    role = st.session_state.get("user_role", "admin")
    user_ns = st.session_state.get("user_namespace")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Search query", key="fts_query", placeholder="morning briefing, client report, ...")
    with col2:
        if role in ("client", "viewer") and user_ns:
            search_ns = user_ns
            st.selectbox("Namespace", [user_ns], key="fts_ns", disabled=True)
        else:
            ns_data = api_get("/namespaces") or []
            ns_options = ["all"] + [n["slug"] for n in ns_data]
            search_ns = st.selectbox("Namespace", ns_options, key="fts_ns")

    if st.button("Search", width='stretch') and query.strip():
        url = f"/outputs/search?q={query}&limit=20"
        if search_ns != "all":
            url += f"&namespace={search_ns}"
        results = api_get(url) or []

        if not results:
            st.info("No results.")
        else:
            st.caption(f"{len(results)} results")
            for r in results:
                icon = TYPE_ICONS.get(r.get("output_type", ""), "•")
                score = abs(r.get("score", 0.0))
                st.markdown(
                    f"{icon} **{r.get('title','?')}** · `{r.get('namespace','')}` · "
                    f"`{r.get('output_type','')}` · score: `{score:.3f}`"
                )
                if r.get("summary"):
                    st.caption(r["summary"])
                st.markdown("---")


def _render_stats(api_get):
    st.subheader("Output Statistics")
    role = st.session_state.get("user_role", "admin")
    user_ns = st.session_state.get("user_namespace")
    is_scoped = role in ("client", "viewer") and user_ns

    col1, col2 = st.columns(2)
    with col1:
        label = f"Namespace: `{user_ns}`" if is_scoped else "Global"
        st.markdown(f"**{label}**")
        stats_url = f"/outputs/stats?namespace={user_ns}" if is_scoped else "/outputs/stats"
        stats = api_get(stats_url) or {}
        total = stats.get("total_count", 0)
        total_kb = round(stats.get("total_bytes", 0) / 1024, 1)
        st.metric("Total Outputs", total)
        st.metric("Total Size", f"{total_kb} KB")

        by_type = stats.get("by_type", {})
        if by_type:
            st.markdown("**By Type:**")
            for otype, info in sorted(by_type.items()):
                icon = TYPE_ICONS.get(otype, "•")
                st.markdown(f"{icon} `{otype}` — {info['count']} outputs · {round(info['total_bytes']/1024,1)} KB")

    with col2:
        if not is_scoped:
            # Single aggregated call — avoids N per-namespace HTTP round-trips
            all_stats = api_get("/outputs/stats/all") or {}
            by_ns = all_stats.get("by_namespace", {})
            if by_ns:
                st.markdown("**By Namespace:**")
                for slug, info in sorted(by_ns.items()):
                    count = info.get("total_count", 0)
                    if count > 0:
                        kb = round(info.get("total_bytes", 0) / 1024, 1)
                        st.markdown(f"`{slug}` — {count} outputs · {kb} KB")
