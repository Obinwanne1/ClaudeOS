# ClaudeOS Dashboard — Code Review Report

**Reviewed:** 2026-05-25T00:00:00Z
**Depth:** standard (cross-file awareness applied)
**Files Reviewed:** 8
**Status:** issues_found

---

## Files Reviewed

1. `dashboard/app.py`
2. `dashboard/components/brand.py`
3. `dashboard/_pages/_overview.py`
4. `dashboard/_pages/_admin.py`
5. `dashboard/_pages/_agents.py`
6. `core/api/app.py`
7. `core/api/routes/system.py`
8. `core/auth.py`

---

## Summary

The codebase is well-structured and security-conscious. Auth, namespace isolation, and the JWT/refresh flow are implemented correctly. Most issues found are medium-severity: namespace data leaking into unsanitised HTML, an unauthenticated session-restore endpoint that acts as an opaque bearer credential, a missing rate limit on that endpoint, and a silent data-loss path in the admin deactivate flow. One critical-class issue: the `/auth/session/<key>` endpoint returns full tokens including the raw refresh token to any caller who can reach the Flask port, with no rate limiting in place.

---

## CRITICAL Issues

### CR-01: `/auth/session/<key>` is unauthenticated and returns raw refresh tokens — no rate limit

**File:** `core/api/routes/auth_routes.py:351-368`

The `GET /auth/session/<key>` and `DELETE /auth/session/<key>` endpoints require **no authentication**. Any HTTP client that can reach port 5000 (including other users on LAN, or any code running on the host) can call these endpoints. The response includes the `access_token` and the `refresh_token` in plaintext.

The `session_key` is a `secrets.token_urlsafe(32)` (approx 256 bits of entropy), so brute force is infeasible. However:
- There is no `@limiter.limit()` decorator on these endpoints.
- The `dashboard_sessions` table stores the **raw** `refresh_token` (not its SHA-256 hash), meaning a DB read also exposes it directly. This contradicts the pattern used in `user_sessions` where only the hash is stored.

**Fix — two parts:**

1. Add rate limiting to the session endpoints:
```python
@auth_bp.get("/session/<key>")
@limiter.limit("20 per minute")
def restore_dashboard_session(key):
    ...
```

2. Store only the token hash in `dashboard_sessions`, mirroring the `user_sessions` pattern:
```python
# At store time (store_dashboard_session):
refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
conn.execute("INSERT INTO dashboard_sessions ... VALUES (?, ..., ?, ...)",
             (key, ..., refresh_hash, ...))
# Return the raw token only in the immediate response, not from DB lookup.
```

---

### CR-02: User namespace value injected into HTML without escaping in `_overview.py`

**File:** `dashboard/_pages/_overview.py:39-41`

`user_ns` comes from `st.session_state["user_namespace"]`, decoded from the JWT payload without further sanitisation. If an admin creates a namespace slug containing HTML/JS (e.g., `<img src=x onerror=alert(1)>`), any client/viewer bound to that namespace will execute arbitrary JavaScript inside the Streamlit parent frame.

```python
# Line 39-41
f'<span style="color:inherit;">{user_ns}</span></div>',
unsafe_allow_html=True,
```

**Fix:**
```python
from html import escape as _esc
...
f'<span style="color:inherit;">{_esc(user_ns)}</span></div>',
```

The same pattern applies to `_ns` in `_render_live_feed` at line 225 (injected raw into the HTML feed row without escaping).

---

## HIGH Issues

### HI-01: `_render_live_feed` injects `_agent` and `_ns` values into raw HTML without escaping

**File:** `dashboard/_pages/_overview.py:209, 225, 234, 258`

`_agent` is truncated from `agent_id` (a DB-sourced string) and `_ns` is the namespace from the run record. Both are interpolated directly into `st.markdown(..., unsafe_allow_html=True)` blocks. An agent name or namespace containing HTML characters stored in the DB would inject markup into the live feed for all users.

```python
_agent = (run.get("agent_id") or "")[:12]   # no escaping
_ns_part = f'<span ...> · {_ns}</span>'      # no escaping
```

**Fix:**
```python
from html import escape as _esc
_agent = _esc((run.get("agent_id") or "")[:12])
_ns    = _esc(run.get("namespace", "global"))
```

---

### HI-02: Admin deactivate (single-user path) silently ignores the HTTP response — false success

**File:** `dashboard/_pages/_admin.py:124-128`

The single-user deactivate button fires `_req.delete()` and immediately calls `st.success("Deactivated.")` regardless of the HTTP status code. If the API returns 403, 404, or 500, the admin sees a false success message and the account is not actually deactivated.

```python
if st.button("Deactivate", key=f"deact_{uid}", use_container_width=True):
    _req.delete(
        f"{_API_BASE}/admin/users/{uid}",
        headers=_auth_headers(), timeout=5,
    )
    st.success("Deactivated.")   # shown even on API failure
    st.rerun()
```

**Fix:**
```python
if st.button("Deactivate", key=f"deact_{uid}", use_container_width=True):
    resp = _req.delete(
        f"{_API_BASE}/admin/users/{uid}",
        headers=_auth_headers(), timeout=5,
    )
    if resp.ok:
        st.success("Deactivated.")
    else:
        err = resp.json().get("error", f"HTTP {resp.status_code}") if resp.content else f"HTTP {resp.status_code}"
        st.error(f"Failed: {err}")
    st.rerun()
```

---

### HI-03: Multi-turn conversation history sent as GET query-string parameter — logged in plaintext

**File:** `dashboard/_pages/_agents.py:224-227`

Multi-turn conversation history is JSON-serialised and sent as a URL query parameter on a GET request to the SSE stream endpoint:

```python
params = {"prompt": prompt, "namespace": namespace}
if messages:
    params["messages"] = json.dumps(messages)   # appended to GET query string
requests.get(url, params=params, ...)
```

This means:
- The full conversation history (and `prompt`) appears in Flask/nginx access logs in plaintext.
- URL length limits (typically 8 KB) will cause silent truncation or 414 errors for long conversations.
- Any PII or secrets in prompts are permanently logged.

**Fix:** Switch the SSE stream endpoint to accept a POST body, or send prompt/messages as POST JSON and use a streaming response. At minimum, exclude `messages` from GET params and pass a conversation ID instead if the server stores history.

---

### HI-04: `effective_namespace()` falls back to user-supplied `requested` for client/viewer roles

**File:** `core/auth.py:366`

```python
def effective_namespace(requested=None):
    role = getattr(g, "user_role", "admin")
    if role in ("client", "viewer"):
        return getattr(g, "user_namespace", None) or requested   # fallback to caller value
    return requested
```

If `g.user_namespace` is `None` (a client account created without a namespace), `effective_namespace()` falls back to the caller-supplied `requested` argument. In `system.py:events()`, `requested` is `request.args.get("namespace")` — a client with no namespace can pass any namespace slug via query param and read that namespace's events. This is a namespace isolation bypass for improperly provisioned accounts.

**Fix:**
```python
def effective_namespace(requested=None):
    role = getattr(g, "user_role", "admin")
    if role in ("client", "viewer"):
        return getattr(g, "user_namespace", None)  # never trust caller value for restricted roles
    return requested
```

Enforce at account creation that client/viewer accounts always have a namespace assigned.

---

## MEDIUM Issues

### ME-01: Audio dedup fingerprint is 10 bytes of RIFF header — fails for different recordings at same settings

**File:** `dashboard/_pages/_agents.py:340-343`

```python
check_bytes = audio_data.read(10)
if st.session_state.get("_last_audio_bytes") == check_bytes:
    return
```

The first 10 bytes of a WAV/RIFF file are the RIFF magic bytes and file size header — identical for any two recordings made at the same sample rate and channel count. Two different voice prompts from the same mic at the same settings will match on these 10 bytes, and the second recording will never be transcribed.

**Fix:**
```python
import hashlib
audio_bytes = audio_data.read()
audio_hash = hashlib.md5(audio_bytes).digest()
if st.session_state.get("_last_audio_hash") == audio_hash:
    return
st.session_state["_last_audio_hash"] = audio_hash
# Write audio_bytes directly to tmp — no second read needed
with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
    tmp.write(audio_bytes)
    tmp_path = tmp.name
```

---

### ME-02: ThreadPoolExecutor workers in `_overview.py` lack `st.session_state` context — JWT may be missing

**File:** `dashboard/_pages/_overview.py:61-64`

The comment at lines 49-52 correctly explains why `/system/stats` was moved to the main thread. However, the four remaining parallel calls (`/system/status`, `/agents`, `/agents/runs?namespace=...`, `/memory/namespaces`) still execute in worker threads. `api_get` calls `_get_headers()` which accesses `st.session_state`. Worker threads do not inherit the Streamlit script's session state, so these requests fall back to `CLAUDEOS_DEV_API_KEY` (operator scope), bypassing namespace scoping for clients.

**Fix:** Pre-capture headers on the main thread before submitting:
```python
# In render(), before the ThreadPoolExecutor block:
from dashboard.app import _get_headers
_captured_headers = _get_headers()   # called on main Streamlit thread

import requests as _req
import os
_base = f"http://localhost:{os.environ.get('FLASK_PORT','5000')}/api/v1"

with ThreadPoolExecutor(max_workers=4) as ex:
    def _fetch(path):
        r = _req.get(f"{_base}{path}", headers=_captured_headers, timeout=3)
        return r.json() if r.ok else None
    futures = {ex.submit(_fetch, path): key for key, path in _calls.items()}
```

---

### ME-03: `_build_css` cache `max_entries=2` is per-session in Streamlit — misses cross-session sharing

**File:** `dashboard/components/brand.py:263`

```python
@st.cache_data(max_entries=2)
def _build_css(theme_key: str) -> str:
```

`st.cache_data` with `max_entries=2` works for two themes within a single session. However the intent appears to be to share the CSS across sessions (avoid regenerating ~8 KB on every user's first render). Since `theme_key` is deterministic and the CSS never changes at runtime, use `ttl=None` to cache permanently:

```python
@st.cache_data(ttl=None)
def _build_css(theme_key: str) -> str:
```

---

### ME-04: `/system/namespace-stats` workflow run query not scoped by namespace

**File:** `core/api/routes/system.py:155-163`

```python
wf_row = conn.execute(
    "SELECT COUNT(*), SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) "
    "FROM workflow_runs WHERE created_at>=?",
    (month_ago,),
).fetchone()
```

The workflow runs query has no `namespace` filter. The `pulse_score` for a client namespace includes all workflow runs across all namespaces in the `wf_score` component (10% weight), making this metric meaningless and potentially misleading. If `workflow_runs` has a `namespace` column:

**Fix:**
```python
wf_row = conn.execute(
    "SELECT COUNT(*), SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) "
    "FROM workflow_runs WHERE namespace=? AND created_at>=?",
    (ns, month_ago),
).fetchone()
```

If the column does not exist, the `wf_score` component should be excluded from the pulse calculation or hardcoded to 100 (current fallback) with a comment.

---

### ME-05: Admin branding preview injects unsanitised company name and icon into HTML

**File:** `dashboard/_pages/_admin.py:484`

The branding live preview renders `_name` (company name from text input) and `_icon` (emoji from text input) directly into an `unsafe_allow_html` block without escaping:

```python
f'{_icon} {_name}</div>'   # _name and _icon not escaped
```

An admin who types `"><script>alert(1)</script>` as a company name will execute JS in the preview before saving. Since only admins can reach this page the risk is self-inflicted, but it's an incorrect pattern.

**Fix:**
```python
from html import escape as _esc
_name_safe = _esc(_name)
_icon_safe = _esc(_icon)
# then use _name_safe / _icon_safe in the f-string
```

---

### ME-06: `bulk_delete` in `app.py` swallows exceptions with no log entry

**File:** `dashboard/app.py:213`

```python
except Exception:
    pass    # no logging
return None
```

Unlike `api_get` and `api_post` which call `logger.warning()` on failure, `bulk_delete` uses a bare `except: pass`. Network errors, timeouts, and server faults are silently dropped with no trace in logs, making post-incident debugging impossible.

**Fix:**
```python
except Exception as e:
    logger.warning("bulk_delete %s failed: %s", path, e)
```

---

## LOW Issues

### LO-01: MutationObserver created on every rerun — accumulates under 8-second live-refresh

**File:** `dashboard/components/brand.py:859-861`

The MutationObserver in `theme_toggle()` auto-disconnects after 5 seconds. Under live-refresh mode (8-second interval), a new observer is injected every 8 seconds before the old one disconnects, creating brief overlapping observers. No correctness bug today, but may cause flicker if both fire simultaneously.

---

### LO-02: `_maybe_refresh_token` decodes JWT without signature verification

**File:** `dashboard/app.py:104`

```python
payload = _jwt.decode(token, options={"verify_signature": False})
```

Intentional (Flask validates on every API call), but the comment should note explicitly why this is safe so future developers do not replicate the pattern naively.

---

### LO-03: Rate limiter uses `remote_addr` — ineffective behind a reverse proxy

**File:** `core/api/limiter.py:5`

`get_remote_address` returns `request.remote_addr`. Behind nginx/caddy, all requests appear from `127.0.0.1`, collapsing all users into a single rate-limit bucket. Add `ProxyFix` middleware if this will ever run behind a proxy.

---

### LO-04: Dead function `_blocking_response` in `_agents.py` — never called

**File:** `dashboard/_pages/_agents.py:278-335`

`_blocking_response()` is defined but never called. The chat tab always uses `_stream_response()`. Remove it or add a comment explaining it is an intentional fallback.

---

### LO-05: `from datetime import datetime` imported inside a loop in `_overview.py`

**File:** `dashboard/_pages/_overview.py:217`

```python
for run in runs[:10]:
    try:
        from datetime import datetime as _dt   # re-imported on every iteration
```

Move the import to the top of the function or module.

---

### LO-06: `_admin.py` duplicates Flask port discovery instead of using the passed `api_post` helper

**File:** `dashboard/_pages/_admin.py:12-13`

`_admin.py` reads `FLASK_PORT` and constructs its own `_API_BASE`, duplicating the logic from `app.py`. Several actions in the admin page bypass the passed-in `api_post`/`api_get` helpers and call `_req.post/delete` directly. This means those calls also bypass the automatic 401-handler and session refresh logic. Prefer using the passed-in `api_post` for all mutating calls.

---

## Priority Fix Order

| Priority | ID    | Issue                                                        |
|----------|-------|--------------------------------------------------------------|
| 1        | CR-01 | Rate-limit `/auth/session/<key>`; hash refresh token in DB   |
| 2        | CR-02 | Escape `user_ns` before `unsafe_allow_html` in overview      |
| 3        | HI-01 | Escape `agent_id` and `namespace` in live feed HTML          |
| 4        | HI-04 | Remove `or requested` fallback in `effective_namespace()`    |
| 5        | HI-02 | Check HTTP response in single-user admin deactivate          |
| 6        | HI-03 | Move prompt/messages out of GET query string for SSE         |
| 7        | ME-01 | Fix audio dedup to hash full content, not 10-byte header     |
| 8        | ME-02 | Pre-capture JWT headers before ThreadPoolExecutor submission |
| 9        | ME-04 | Scope workflow_runs query by namespace in pulse score        |
| 10       | ME-06 | Add `logger.warning()` to `bulk_delete` exception handler    |

---

_Reviewer: Claude (gsd-code-reviewer) · Depth: standard_
_Date: 2026-05-25_
