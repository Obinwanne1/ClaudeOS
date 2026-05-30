"""Agents page — Phase 10, 12, 13 upgrades.

New capabilities:
- Multi-turn conversation chat UI (Phase 13.4)
- SSE streaming responses via requests (Phase 10.1)
- Native file attachment via chat_input(accept_file=True): images + .md/.txt (Phase 13.2+)
  - Sidebar file_uploader kept as fallback; both merged into _all_files
  - Text files (.md/.txt) injected as fenced context block in prompt
  - Images encoded as base64 content blocks, multiple supported
- Voice input via audio recording (Phase 13.1)
- Eval score display on run history (Phase 10.3)
- A2A Agent Card viewer (Phase 12.3)
"""
from __future__ import annotations

import base64
import json
import re
import time
import uuid

import requests
import streamlit as st
from dashboard.components.brand import PRIMARY, PRIMARY_LIGHT, SURFACE, badge, get_theme_vars

CATEGORY_COLORS = {
    "ops":         "#407E3C",
    "research":    "#3b82f6",
    "content":     "#8b5cf6",
    "analysis":    "#f59e0b",
    "comms":       "#ec4899",
    "system":      "#6b7280",
    "engineering": "#ef4444",
    "domain":      "#14b8a6",
}

_SCORE_COLOR = {
    (4.0, 5.1): "#5a9e56",
    (2.5, 4.0): "#f59e0b",
    (0.0, 2.5): "#ef4444",
}


def _score_badge(score) -> str:
    if score is None:
        return ""
    for (lo, hi), color in _SCORE_COLOR.items():
        if lo <= float(score) < hi:
            return f'<span style="background:{color}22;color:{color};border:1px solid {color}55;padding:1px 7px;border-radius:10px;font-size:0.72rem;font-weight:700;">⭐ {score:.1f}</span>'
    return ""


def render(api_get, api_post, bulk_delete=None):
    st.title("🤖 Agents")

    agents_data = api_get("/agents?enabled_only=false")
    if not agents_data:
        st.error("API unreachable")
        return

    agents = agents_data.get("agents", [])
    if not agents:
        st.info("No agents registered. Run `python scripts/seed_agents.py`")
        return

    # Tab navigation and persistence across reruns (card clicks + theme toggles).
    # Python signals target=0 on card click; all other reruns use sessionStorage
    # (browser-side, invisible to Streamlit backend, survives theme-toggle reruns).
    _goto_chat_now = st.session_state.pop("_goto_chat", False)
    _target_tab = 0 if _goto_chat_now else -1  # -1 = "restore from sessionStorage"

    import time as _t
    import streamlit.components.v1 as _cv1
    _cv1.html(f"""<script>
(function(){{
    var target={_target_tab}, nonce={int(_t.time()*1000)};
    var KEY='claudeos_agents_tab';
    setTimeout(function(){{
        var tabs=window.parent.document.querySelectorAll('[data-testid="stTab"]');
        if(!tabs.length) return;
        var desired;
        if(target>=0){{
            // Explicit navigation (catalog card click) — go to target and save
            desired=target;
            window.parent.sessionStorage.setItem(KEY,desired);
        }}else{{
            // Restore: read last user-selected tab (default 1 = Catalog on first visit)
            var stored=window.parent.sessionStorage.getItem(KEY);
            desired=stored!==null?parseInt(stored):1;
        }}
        // Only click if tab is not already active (prevents infinite rerun loop)
        if(desired<tabs.length&&tabs[desired].getAttribute('aria-selected')!=='true'){{
            tabs[desired].click();
        }}
        // Track future user tab clicks into sessionStorage (no rerun triggered)
        tabs.forEach(function(tab,idx){{
            if(!tab._agentsBound){{
                tab._agentsBound=true;
                tab.addEventListener('click',function(){{
                    window.parent.sessionStorage.setItem(KEY,idx);
                }});
            }}
        }});
    }},120);
}})();
</script>""", height=0)

    tab_chat, tab_catalog, tab_runs = st.tabs(["💬 Chat", "📋 Catalog", "📊 Run History"])

    with tab_chat:
        _render_chat_tab(agents, api_get, api_post)

    with tab_catalog:
        _render_catalog_tab(agents, api_get, api_post)

    with tab_runs:
        _render_runs_tab(api_get)


# ── Chat Tab ──────────────────────────────────────────────────────────────────

def _render_chat_tab(agents: list, api_get, api_post):
    """Multi-turn conversational agent chat with streaming, images, and voice."""
    tv = get_theme_vars()

    col_settings, col_chat = st.columns([1, 3])

    with col_settings:
        st.markdown("**Agent Settings**")
        agent_names = [a["name"] for a in agents if a.get("enabled")]
        _pending = st.session_state.pop("_pending_agent", None)
        # Must set session state BEFORE widget instantiation (not after) to avoid StreamlitAPIException
        if _pending and _pending in agent_names:
            st.session_state["chat_agent"] = _pending
        sel_agent = st.selectbox("Agent", agent_names, key="chat_agent")

        _role = st.session_state.get("user_role", "admin")
        _user_ns = st.session_state.get("user_namespace")
        if _role in ("client", "viewer") and _user_ns:
            _ns_opts = [_user_ns]
        else:
            _ns_data = api_get("/namespaces") or []
            _ns_opts = [n["slug"] for n in _ns_data if isinstance(n, dict) and n.get("slug")] or ["global"]
        sel_ns = st.selectbox("Namespace", _ns_opts, key="chat_ns")
        save_out = st.checkbox("Save output", value=True, key="chat_save")

        st.markdown("---")
        st.markdown("**Attach**")
        uploaded = st.file_uploader(
            "Image or Markdown file",
            type=["png", "jpg", "jpeg", "webp", "gif", "md", "txt"],
            key=f"chat_img_{sel_agent}",
            label_visibility="collapsed",
        )
        if uploaded:
            _ext = uploaded.name.lower().split(".")[-1]
            if _ext in ("md", "txt"):
                st.caption(f"📄 {uploaded.name} ({round(uploaded.size/1024,1)} KB)")
            else:
                st.image(uploaded, width=140)

        # Voice input — key includes clear-counter so widget resets on Clear
        _audio_gen = st.session_state.get(f"_audio_gen_{sel_agent}", 0)
        st.markdown("**Voice Input**")
        audio_data = st.audio_input("Record prompt", key=f"chat_audio_{sel_agent}_{_audio_gen}",
                                     label_visibility="collapsed")
        if audio_data:
            _transcribe_audio(audio_data)

        st.markdown("---")
        def _do_clear():
            _agent = st.session_state.get('chat_agent', '')
            _ns    = st.session_state.get('chat_ns', '')
            st.session_state.pop(f"conv_{_agent}_{_ns}", None)
            st.session_state.pop(f"conv_id_{_agent}", None)
            st.session_state.pop("_last_audio_hash", None)
            # Increment counter → new key → audio widget re-renders blank
            st.session_state[f"_audio_gen_{_agent}"] = st.session_state.get(f"_audio_gen_{_agent}", 0) + 1

        st.button("Clear conversation", key="chat_clear",
                  on_click=_do_clear, use_container_width=True)

        # Agent Card viewer
        with st.expander("🪪 Agent Card (A2A)"):
            card = api_get(f"/agents/{sel_agent}/.well-known/agent.json")
            if card:
                st.json(card)

    with col_chat:
        conv_key = f"conv_{sel_agent}_{sel_ns}"
        if conv_key not in st.session_state:
            st.session_state[conv_key] = []

        history: list[dict] = st.session_state[conv_key]

        # Render conversation history
        chat_container = st.container()
        with chat_container:
            for turn in history:
                role = turn["role"]
                with st.chat_message(role, avatar="🧑" if role == "user" else "🤖"):
                    st.markdown(turn["content"])
                    if role == "assistant" and turn.get("meta"):
                        meta = turn["meta"]
                        score_html = _score_badge(meta.get("eval_score"))
                        st.markdown(
                            f'<span style="color:{tv["TEXT_MUTED"]};font-size:0.73rem;">'
                            f'⏱ {meta.get("duration_ms",0)}ms · '
                            f'{meta.get("tokens_in",0)}+{meta.get("tokens_out",0)} tokens'
                            f'</span> {score_html}',
                            unsafe_allow_html=True,
                        )

        # Input area — accepts text + files (images, md, txt) natively
        _chat_val = st.chat_input(
            f"Message {sel_agent}… (attach images/files via 📎)",
            key=f"chat_input_{sel_agent}",
            accept_file=True,
            file_type=["png", "jpg", "jpeg", "webp", "gif", "md", "txt"],
        )

        # Normalise: chat_input returns str OR ChatInputValue OR None
        _chat_files = []
        if _chat_val is not None and not isinstance(_chat_val, str):
            _raw_prompt = _chat_val.text or ""
            _chat_files = list(_chat_val.files or [])
        elif isinstance(_chat_val, str):
            _raw_prompt = _chat_val
        else:
            _raw_prompt = None

        # Use transcribed text if available (overrides empty chat prompt)
        if st.session_state.get("_transcribed_text"):
            _raw_prompt = st.session_state.pop("_transcribed_text")

        # Merge sidebar uploader with chat-input files
        _all_files = _chat_files[:]
        if uploaded:
            _all_files.append(uploaded)

        prompt = _raw_prompt

        if prompt is not None:
            # Split files into images vs text
            _IMG_EXTS = {"png", "jpg", "jpeg", "webp", "gif"}
            _img_files  = [f for f in _all_files if f.name.lower().split(".")[-1] in _IMG_EXTS]
            _text_files = [f for f in _all_files if f.name.lower().split(".")[-1] in ("md", "txt")]

            # Inject text file content into prompt
            for _tf in _text_files:
                _file_text = _tf.read().decode("utf-8", errors="replace")
                prompt = f"--- FILE: {_tf.name} ---\n{_file_text}\n---\n\n{prompt}"

            # Add user message to history
            user_turn = {"role": "user", "content": prompt}
            if _img_files:
                user_turn["has_image"] = True
            history.append(user_turn)

            with st.chat_message("user", avatar="🧑"):
                st.markdown(prompt)
                for _imf in _img_files:
                    st.image(_imf, width=200)

            # Build API messages for multi-turn
            api_messages = _history_to_api_messages(history[:-1])  # exclude current turn

            # Prepare image data as base64 content blocks
            images = None
            if _img_files:
                images = []
                for _imf in _img_files:
                    _imf.seek(0)
                    _b64 = base64.b64encode(_imf.read()).decode("utf-8")
                    images.append({"data": _b64, "media_type": _mime_type(_imf.name)})

            # Dispatch agent — always stream (non-blocking, logs run record)
            with st.chat_message("assistant", avatar="🤖"):
                response_text, meta = _stream_response(
                    sel_agent, prompt, sel_ns, api_messages, images, api_get,
                    api_post=api_post, save_out=save_out,
                )

                err = st.session_state.pop("_stream_error", None)
                if response_text:
                    history.append({
                        "role": "assistant",
                        "content": response_text,
                        "meta": meta,
                    })
                    st.session_state[conv_key] = history
                    st.rerun()
                elif err:
                    history.append({
                        "role": "assistant",
                        "content": f"❌ **Error:** {err}",
                    })
                    st.session_state[conv_key] = history
                    st.rerun()


def _stream_response(
    agent_name: str,
    prompt: str,
    namespace: str,
    messages: list,
    images,
    api_get,
    api_post=None,
    save_out: bool = False,
) -> tuple[str, dict]:
    """Stream SSE response from Flask SSE endpoint."""
    import os
    _FLASK_PORT = os.environ.get("FLASK_PORT", "5000")
    token = st.session_state.get("jwt_token", "")
    headers = {"Authorization": f"Bearer {token}", "Accept": "text/event-stream"}

    params = {
        "prompt": prompt,
        "namespace": namespace,
        "save_output": "true" if save_out else "false",
    }
    if messages:
        params["messages"] = json.dumps(messages)

    url = f"http://localhost:{_FLASK_PORT}/api/v1/agents/{agent_name}/stream"

    placeholder = st.empty()
    full_text = ""
    meta: dict = {"tokens_in": 0, "tokens_out": 0}
    start = time.monotonic()

    # Use POST when images present (GET can't carry body); GET otherwise
    if images:
        body = {"prompt": prompt, "namespace": namespace, "save_output": save_out}
        if messages:
            body["messages"] = messages
        body["images"] = images
        req_ctx = requests.post(url, json=body, headers=headers, stream=True, timeout=300)
    else:
        req_ctx = requests.get(url, params=params, headers=headers, stream=True, timeout=300)

    try:
        with req_ctx as resp:
            if not resp.ok:
                st.error(f"Stream error: {resp.status_code}")
                return "", {}

            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")
                if not decoded.startswith("data: "):
                    continue
                payload = json.loads(decoded[6:])
                if payload.get("type") == "token":
                    full_text += payload.get("text", "")
                    placeholder.markdown(full_text + "▌")
                elif payload.get("type") == "done":
                    placeholder.markdown(full_text)
                    meta["tokens_in"] = payload.get("tokens_in", 0)
                    meta["tokens_out"] = payload.get("tokens_out", 0)
                    break
                elif payload.get("type") == "error":
                    err = payload.get("message", "Stream error")
                    st.session_state["_stream_error"] = err
                    return full_text, {}

        meta["duration_ms"] = int((time.monotonic() - start) * 1000)
        return full_text, meta

    except Exception as e:
        st.session_state["_stream_error"] = f"Streaming failed: {e}"
        return "", {}


def _blocking_response(
    agent_name: str,
    prompt: str,
    namespace: str,
    save_out: bool,
    messages: list,
    images,
    api_post,
    api_get,
) -> tuple[str, dict]:
    """Non-streaming: dispatch + poll until done."""
    payload = {
        "prompt": prompt,
        "namespace": namespace,
        "save_output": save_out,
    }
    if messages:
        payload["messages"] = messages
    if images:
        payload["images"] = images

    result = api_post(f"/agents/{agent_name}/run", payload)
    if not result:
        st.error("Dispatch failed")
        return "", {}

    run_id = result.get("run_id")
    placeholder = st.empty()
    placeholder.info("⏳ Agent running…")

    for _ in range(60):  # max 5 minutes
        time.sleep(5)
        run = api_get(f"/agents/runs/{run_id}")
        if not run:
            break
        status = run.get("status")
        if status == "done":
            placeholder.empty()
            output_text = (run.get("output") or {}).get("text", "")
            # Clean markdown fences
            output_text = re.sub(r"^```[a-zA-Z]*\n?", "", output_text)
            output_text = re.sub(r"\n?```$", "", output_text).strip()
            st.markdown(output_text)
            meta = {
                "duration_ms": run.get("duration_ms", 0),
                "tokens_in": run.get("tokens_in", 0),
                "tokens_out": run.get("tokens_out", 0),
                "eval_score": run.get("eval_score"),
            }
            return output_text, meta
        elif status == "failed":
            placeholder.empty()
            st.error(run.get("error", "Agent failed"))
            return "", {}

    placeholder.empty()
    st.warning("Agent timed out — check Run History")
    return "", {}


def _transcribe_audio(audio_data) -> None:
    """Transcribe audio using Whisper and store in session state."""
    import hashlib
    audio_bytes = audio_data.read()
    audio_hash = hashlib.md5(audio_bytes).digest()
    if st.session_state.get("_last_audio_hash") == audio_hash:
        return  # Same audio, already transcribed
    st.session_state["_last_audio_hash"] = audio_hash

    with st.spinner("Transcribing audio…"):
        try:
            import tempfile, os
            # Save to temp file (audio_bytes already read — no second .read() needed)
            suffix = ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                import whisper
                model = _get_whisper_model()
                result = model.transcribe(tmp_path)
                text = result.get("text", "").strip()
                if text:
                    st.session_state["_transcribed_text"] = text
                    st.success(f"Transcribed: _{text}_")
            finally:
                os.unlink(tmp_path)
        except ImportError:
            st.warning("Voice input requires `openai-whisper`. Run: `pip install openai-whisper`")
        except Exception as e:
            st.error(f"Transcription failed: {e}")


@st.cache_resource
def _get_whisper_model():
    import whisper
    return whisper.load_model("base")


def _mime_type(filename: str) -> str:
    ext = filename.lower().split(".")[-1]
    return {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")


def _history_to_api_messages(history: list) -> list:
    """Convert Streamlit history list to Claude API messages format."""
    messages = []
    for turn in history:
        role = turn["role"]
        content = turn["content"]
        messages.append({"role": role, "content": content})
    return messages


# ── Catalog Tab ───────────────────────────────────────────────────────────────

def _render_catalog_tab(agents: list, api_get, api_post):
    tv = get_theme_vars()
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Search agents", placeholder="name, category, tag…",
                               label_visibility="collapsed")
    with col2:
        cats = ["All"] + sorted({a["category"] for a in agents})
        cat_filter = st.selectbox("Category", cats, label_visibility="collapsed")

    filtered = agents
    if search:
        q = search.lower()
        filtered = [a for a in filtered if
                    q in a["name"] or q in a["description"] or q in a["category"]
                    or any(q in t for t in a.get("tags", []))]
    if cat_filter != "All":
        filtered = [a for a in filtered if a["category"] == cat_filter]

    st.markdown(f"**{len(filtered)}** agents")
    st.markdown("---")

    # Hide all card trigger buttons (used only as Streamlit callbacks)
    st.markdown("""<style>
[class*="st-key-card_chat_"] {
    height: 0 !important; min-height: 0 !important;
    overflow: hidden !important; margin: 0 !important; padding: 0 !important;
}
</style>""", unsafe_allow_html=True)

    for i in range(0, len(filtered), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(filtered):
                break
            a = filtered[i + j]
            color = CATEGORY_COLORS.get(a["category"], PRIMARY)
            with col:
                _safe = a['name'].replace('-', '_').replace(' ', '_')
                _btn_key = f"card_chat_{_safe}"
                enabled_dot = "●" if a["enabled"] else "○"
                enabled_color = "#5a9e56" if a["enabled"] else "#6b7280"
                ns_lock = f"· 🔒 {a['namespace_lock']}" if a.get('namespace_lock') else ""
                import streamlit.components.v1 as _cv1
                _cv1.html(f"""<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}}
body{{background:transparent;padding:0 0 8px 0;}}
.card{{
    background:{tv['SURFACE']};
    border:1px solid {tv['BORDER']};
    border-radius:10px;
    padding:14px 16px;
    cursor:pointer;
    transition:background 0.15s,border-color 0.15s,box-shadow 0.15s;
    user-select:none;
}}
.card:hover{{
    background:{color}28;
    border-color:{color};
    box-shadow:0 0 0 2px {color}44;
}}
.card:active{{background:{color}44;}}
.row{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}}
.name{{font-weight:700;color:{tv['TEXT']};font-size:0.88rem;}}
.dot{{color:{enabled_color};margin-right:5px;}}
.badge{{background:{color}33;color:{color};border:1px solid {color}55;padding:2px 8px;border-radius:12px;font-size:0.68rem;font-weight:600;}}
.desc{{color:{tv['TEXT_MUTED']};font-size:0.82rem;margin-bottom:8px;line-height:1.4;}}
.meta{{font-size:0.72rem;color:{tv['TEXT_MUTED']};}}
code{{background:rgba(255,255,255,0.1);padding:1px 5px;border-radius:3px;font-family:monospace;font-size:0.7rem;}}
</style></head><body>
<div class="card" onclick="
  var el=window.parent.document.querySelector('[class*=st-key-{_btn_key}] button');
  if(el)el.click();
">
  <div class="row">
    <div class="name"><span class="dot">{enabled_dot}</span>{a['display_name']}</div>
    <div class="badge">{a['category'].upper()}</div>
  </div>
  <div class="desc">{a['description']}</div>
  <div class="meta">model: <code>{a['model']}</code> · max_tokens: {a['max_tokens']} {ns_lock}</div>
</div>
</body></html>""", height=112, scrolling=False)
                if st.button("\u200b", key=_btn_key, use_container_width=True):
                    st.session_state["_pending_agent"] = a["name"]
                    st.session_state["_goto_chat"] = True
                    st.rerun()


# ── Runs Tab ──────────────────────────────────────────────────────────────────

def _render_runs_tab(api_get):
    tv = get_theme_vars()
    st.subheader("Recent Agent Runs")

    _role = st.session_state.get("user_role", "admin")
    _user_ns = st.session_state.get("user_namespace")
    _runs_url = (
        f"/agents/runs?limit=50&namespace={_user_ns}"
        if _role in ("client", "viewer") and _user_ns
        else "/agents/runs?limit=50"
    )
    runs_data = api_get(_runs_url)
    if not runs_data or not runs_data.get("runs"):
        st.caption("No runs yet.")
        return

    runs = runs_data["runs"]

    # Summary stats
    done = sum(1 for r in runs if r.get("status") == "done")
    failed = sum(1 for r in runs if r.get("status") == "failed")
    scored = [r for r in runs if r.get("eval_score") is not None]
    avg_score = sum(r["eval_score"] for r in scored) / len(scored) if scored else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Runs", len(runs))
    c2.metric("Completed", done)
    c3.metric("Failed", failed)
    c4.metric("Avg Quality", f"{avg_score:.1f}/5" if avg_score else "—",
              help="LLM-as-Judge weighted score")

    st.markdown("---")

    rows = []
    for r in runs:
        eval_score = r.get("eval_score")
        score_str = f"{eval_score:.1f}" if eval_score is not None else "—"
        rows.append({
            "Run ID":    (r.get("id") or "")[:8] + "…",
            "Agent":     (r.get("agent_id") or "")[:16],
            "Namespace": r.get("namespace", ""),
            "Status":    r.get("status", ""),
            "Quality":   score_str,
            "Tokens":    f"{r.get('tokens_in',0)}+{r.get('tokens_out',0)}",
            "Duration":  f"{r.get('duration_ms') or 0}ms",
            "Started":   (r.get("created_at") or "")[:16],
        })
    st.dataframe(rows, use_container_width=True)

    # Show eval reasoning for selected run
    st.markdown("---")
    run_ids = [(r.get("id") or "")[:8] + "…" for r in runs if r.get("eval_reasoning")]
    if run_ids:
        sel = st.selectbox("View eval reasoning", ["—"] + run_ids, key="eval_sel")
        if sel != "—":
            idx = run_ids.index(sel)
            run = [r for r in runs if r.get("eval_reasoning")][idx]
            dims = {}
            try:
                dims = json.loads(run.get("eval_dimensions") or "{}")
            except Exception:
                pass
            st.markdown(f"**Reasoning:** {run.get('eval_reasoning', '')}")
            if dims:
                dc1, dc2, dc3, dc4 = st.columns(4)
                dc1.metric("Task Completion", f"{dims.get('task_completion', 0):.1f}/5")
                dc2.metric("Factual Grounding", f"{dims.get('factual_grounding', 0):.1f}/5")
                dc3.metric("Conciseness", f"{dims.get('conciseness', 0):.1f}/5")
                dc4.metric("Safety", "✅" if dims.get("safety", 1) >= 1 else "❌")
