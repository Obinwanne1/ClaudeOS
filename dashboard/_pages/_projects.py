"""Client Vault page — namespaces, projects, workspace stats."""
import streamlit as st


PRIORITY_LABELS = {1: "🔴 High", 2: "🟡 Medium", 3: "🟢 Low"}
STATUS_ICONS = {"active": "🟢", "paused": "⏸️", "archived": "📦"}


def render(api_get, api_post):
    st.title("Client Vault")

    tab_ns, tab_proj, tab_ctx = st.tabs(["Namespaces", "Projects", "Context Files"])

    with tab_ns:
        _render_namespaces(api_get, api_post)

    with tab_proj:
        _render_projects(api_get, api_post)

    with tab_ctx:
        _render_context(api_get, api_post)


def _render_namespaces(api_get, api_post):
    role = st.session_state.get("user_role", "admin")
    user_ns = st.session_state.get("user_namespace")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Namespaces")
    with col2:
        show_all = st.toggle("Show disabled", value=False) if role in ("admin", "operator") else False

    all_namespaces = api_get(f"/namespaces?enabled={'false' if show_all else 'true'}") or []
    # Clients see only their namespace
    if role in ("client", "viewer") and user_ns:
        namespaces = [ns for ns in all_namespaces if ns.get("slug") == user_ns]
    else:
        namespaces = all_namespaces

    if not namespaces:
        st.info("No namespaces found. Run `python scripts/seed_namespaces.py`")
    else:
        for ns in namespaces:
            color = ns.get("color", "#407E3C")
            icon = ns.get("icon", "🏢")
            enabled = ns.get("enabled", True)
            badge = "🟢" if enabled else "⚫"

            with st.expander(f"{badge} {icon} **{ns['display_name']}** `{ns['slug']}`"):
                col_info, col_stats, col_actions = st.columns([2, 2, 1])

                with col_info:
                    st.markdown(f"**Type:** `{ns.get('type','?')}`")
                    st.markdown(f"**Description:** {ns.get('description','—')}")
                    st.markdown(f"**Color:** `{color}`")

                with col_stats:
                    ws = api_get(f"/namespaces/{ns['slug']}/workspace")
                    if ws and ws.get("workspace"):
                        for subdir, stat in ws["workspace"].items():
                            fc = stat.get("file_count", 0)
                            kb = round(stat.get("size_bytes", 0) / 1024, 1)
                            st.markdown(f"**{subdir}:** {fc} files · {kb} KB")

                with col_actions:
                    projects = api_get(f"/projects?namespace={ns['slug']}") or []
                    st.metric("Projects", len(projects))

    st.markdown("---")
    if role in ("admin", "operator"):
        with st.expander("➕ New Namespace"):
            _new_namespace_form(api_post)


def _render_projects(api_get, api_post):
    st.subheader("Projects")

    namespaces = api_get("/namespaces") or []
    ns_options = {ns["display_name"]: ns["slug"] for ns in namespaces}
    ns_options = {"All": None, **ns_options}

    col1, col2 = st.columns(2)
    with col1:
        selected_ns_name = st.selectbox("Filter by namespace", list(ns_options.keys()), key="proj_ns_filter")
    with col2:
        status_filter = st.selectbox("Status", ["all", "active", "paused", "archived"], key="proj_status_filter")

    ns_slug = ns_options[selected_ns_name]
    url = "/projects"
    params = []
    if ns_slug:
        params.append(f"namespace={ns_slug}")
    if status_filter != "all":
        params.append(f"status={status_filter}")
    if params:
        url += "?" + "&".join(params)

    projects = api_get(url) or []

    if not projects:
        st.info("No projects found.")
    else:
        for proj in projects:
            status = proj.get("status", "active")
            priority = proj.get("priority", 2)
            sicon = STATUS_ICONS.get(status, "•")
            plabel = PRIORITY_LABELS.get(priority, "")

            with st.expander(f"{sicon} **{proj['name']}** `{proj['slug']}` — {plabel}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Description:** {proj.get('description','—')}")
                    stack = proj.get("tech_stack") or []
                    if stack:
                        st.markdown(f"**Stack:** {' · '.join(f'`{t}`' for t in stack)}")
                    if proj.get("path"):
                        st.markdown(f"**Path:** `{proj['path']}`")
                    st.caption(f"Created: {(proj.get('created_at') or '')[:10]}")
                with col2:
                    new_status = st.selectbox(
                        "Status",
                        ["active", "paused", "archived"],
                        index=["active", "paused", "archived"].index(status),
                        key=f"status_{proj['id']}",
                    )
                    if st.button("Update", key=f"upd_{proj['id']}", width='stretch'):
                        api_post(f"/projects/{proj['id']}", {"status": new_status}, method="PATCH")
                        st.rerun()

    st.markdown("---")
    with st.expander("➕ New Project"):
        _new_project_form(api_get, api_post)


def _render_context(api_get, api_post):
    st.subheader("Context Files")
    st.caption("Per-namespace context injected into agent prompts.")

    namespaces = api_get("/namespaces") or []
    if not namespaces:
        st.info("No namespaces.")
        return

    ns_names = {ns["display_name"]: ns["slug"] for ns in namespaces}
    selected = st.selectbox("Namespace", list(ns_names.keys()), key="ctx_ns_select")
    slug = ns_names[selected]

    files = api_get(f"/namespaces/{slug}/context")
    file_list = files.get("files", []) if files else []

    if file_list:
        st.markdown(f"**{len(file_list)} context files in `{slug}`:**")
        for fname in file_list:
            st.markdown(f"- `{fname}`")
    else:
        st.info("No context files yet.")

    st.markdown("---")
    st.markdown("**Write context file:**")
    filename = st.text_input("Filename", value="notes.md", key="ctx_filename")
    content = st.text_area("Content", height=150, key="ctx_content",
                           placeholder="Background info, preferences, or instructions for this namespace's agents.")
    if st.button("Save Context File", width='stretch'):
        result = api_post(f"/namespaces/{slug}/context", {"filename": filename, "content": content})
        if result:
            st.success(f"Saved `{filename}` to `{slug}`")
            st.rerun()
        else:
            st.error("Save failed")


def _new_namespace_form(api_post):
    slug = st.text_input("Slug (e.g. my-client)", key="new_ns_slug")
    display_name = st.text_input("Display Name", key="new_ns_name")
    description = st.text_input("Description", key="new_ns_desc")
    ns_type = st.selectbox("Type", ["client", "personal", "system"], key="new_ns_type")
    color = st.color_picker("Color", value="#407E3C", key="new_ns_color")
    icon = st.text_input("Icon (emoji)", value="🏢", key="new_ns_icon")
    if st.button("Create Namespace", width='stretch', key="create_ns_btn"):
        if slug and display_name:
            result = api_post("/namespaces", {
                "slug": slug, "display_name": display_name,
                "description": description, "type": ns_type,
                "color": color, "icon": icon,
            })
            if result:
                st.success(f"Created namespace `{slug}`")
                st.rerun()
            else:
                st.error("Create failed — slug may already exist")
        else:
            st.warning("Slug and display name required")


def _new_project_form(api_get, api_post):
    namespaces = api_get("/namespaces") or []
    ns_map = {ns["display_name"]: ns["id"] for ns in namespaces}
    if not ns_map:
        st.info("Create a namespace first.")
        return

    selected_ns = st.selectbox("Namespace", list(ns_map.keys()), key="new_proj_ns")
    name = st.text_input("Project Name", key="new_proj_name")
    slug = st.text_input("Slug", key="new_proj_slug")
    description = st.text_input("Description", key="new_proj_desc")
    stack_raw = st.text_input("Tech Stack (comma-separated)", key="new_proj_stack",
                               placeholder="Python, Flask, Streamlit")
    priority = st.selectbox("Priority", [1, 2, 3],
                             format_func=lambda x: PRIORITY_LABELS[x], key="new_proj_priority")
    if st.button("Create Project", width='stretch', key="create_proj_btn"):
        if name and slug:
            tech_stack = [s.strip() for s in stack_raw.split(",") if s.strip()]
            result = api_post("/projects", {
                "namespace_id": ns_map[selected_ns],
                "name": name, "slug": slug,
                "description": description,
                "tech_stack": tech_stack,
                "priority": priority,
            })
            if result:
                st.success(f"Created project `{slug}`")
                st.rerun()
            else:
                st.error("Create failed — slug may already exist in this namespace")
        else:
            st.warning("Name and slug required")
