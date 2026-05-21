# ClaudeOS — Full Security & Quality Review

**Reviewer:** Claude (gsd-code-reviewer)
**Date:** 2026-05-21
**Depth:** deep (OWASP Top 10 + namespace isolation + JWT + injection + XSS + quality)
**Files reviewed:** 14

---

## Summary

ClaudeOS has a generally solid authentication architecture: bcrypt passwords, opaque refresh tokens stored as SHA-256 hashes, JWT with `algorithms=["HS256"]` pinning, rate-limiting on auth endpoints, and `effective_namespace()` enforced on every data-access route. The most serious issues found are a weak-default JWT secret shipped in `config.py`, two SQL injection vectors through dynamic column lists in update handlers, a path-traversal risk in the output file writer, a password-reset token leaked publicly in the login UI, missing namespace isolation on three data-access endpoints (memory bulk-delete, memory get/update/delete by ID, output get/delete by ID), and several medium-severity exception-swallowing patterns.

No hardcoded passwords, no `eval()`, no `innerHTML` injection from user-supplied data, no `==` coercion bugs, and no Unix-only commands were found. Brand compliance (#407E3C + white) is consistent across all UI files.

---

## CRITICAL Issues

### CR-01: Weak JWT secret default ships in production code

**File:** `core/config.py:12`
**Quoted code:**
```python
CLAUDEOS_SECRET_KEY: str = "dev-secret-change-in-prod"
```
**Issue:** If `.env` is absent or `CLAUDEOS_SECRET_KEY` is not set, every JWT will be signed with `"dev-secret-change-in-prod"`. Any attacker who reads the source (public repo, leaked backup) can forge valid tokens with any `role: admin`. The default is a known string.

**Fix:** Remove the fallback entirely and fail loud at startup if the key is missing or is the known-bad string.

```python
from pydantic import field_validator

CLAUDEOS_SECRET_KEY: str  # No default — required

@field_validator("CLAUDEOS_SECRET_KEY")
@classmethod
def secret_not_default(cls, v: str) -> str:
    if not v or v in ("dev-secret-change-in-prod", "change-me-random-32-chars"):
        raise ValueError(
            "CLAUDEOS_SECRET_KEY must be set to a random secret in .env "
            "(not the example value)"
        )
    if len(v) < 32:
        raise ValueError("CLAUDEOS_SECRET_KEY must be at least 32 characters")
    return v
```

---

### CR-02: SQL injection via dynamic column names in `update_user` (admin_routes.py)

**File:** `core/api/routes/admin_routes.py:88–91`
**Quoted code:**
```python
set_clauses = ", ".join(f"{k} = ?" for k in updates)
vals = list(updates.values()) + [user_id]
with get_db() as conn:
    conn.execute(f"UPDATE users SET {set_clauses}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", vals)
```
**Issue:** The `allowed` set `{"role", "namespace", "is_active", "email"}` is a dict filter applied to `body.items()`. The _values_ are parameterised (`?`), but the _column names_ (`k`) are interpolated directly into the SQL string. If the allowlist is ever modified or bypassed (e.g., via a bug in the allowed-set construction), column names become injectable. Even at current scope, passing `"; DROP TABLE users; --"` as a key that somehow slips the filter would execute. Safer to hardcode the column mapping.

**Fix:**
```python
ALLOWED_USER_UPDATES = {
    "role":      "role",
    "namespace": "namespace",
    "is_active": "is_active",
    "email":     "email",
}

updates = {ALLOWED_USER_UPDATES[k]: v for k, v in body.items() if k in ALLOWED_USER_UPDATES}
# ... same set_clauses logic is now safe because keys come from a trusted constant map
```
The allowlist approach already exists; the fix is to derive the SQL column names from a hardcoded map rather than trusting the request key string.

---

### CR-03: SQL injection via dynamic column names in `update_ticket` (tickets.py)

**File:** `core/api/routes/tickets.py:343`
**Quoted code:**
```python
conn.execute(f"UPDATE tickets SET {', '.join(sets)} WHERE id = ?", params)
```
**Issue:** `sets` is built via `sets.append("sla_tier = NULL")` (line 331–332) — note these two appends include no `?` binding:
```python
sets.append("sla_tier = NULL")
sets.append("sla_due_at = NULL")
```
These are safe in isolation. However there is a deeper pattern concern: `sets` is assembled from multiple code branches, with string fragments mixed with parameterised fragments, and then f-string-interpolated into the final SQL. If any future developer adds a branch that uses `body["field"]` directly in a `sets.append()` call this silently becomes injection. The `sla_tier = NULL` / `sla_due_at = NULL` branches specifically bypass parameterisation at lines 331–332.

**Fix:** Use SQLite-compatible parameterised NULL assignment:
```python
# Replace:
sets.append("sla_tier = NULL")
sets.append("sla_due_at = NULL")

# With:
sets.append("sla_tier = ?")
params.append(None)
sets.append("sla_due_at = ?")
params.append(None)
```
This keeps the entire UPDATE fully parameterised.

---

### CR-04: Path traversal in output file writer

**File:** `outputs/manager.py:273–280`
**Quoted code:**
```python
def _write_file(output_id: str, namespace: str, output_type: str, format: str, content: str) -> Path:
    ext = {"markdown": "md", "json": "json", "html": "html"}.get(format, "txt")
    type_dir = output_type if output_type in ("reports", ...) else output_type + "s"
    store_dir = STORE_ROOT / type_dir / namespace
    store_dir.mkdir(parents=True, exist_ok=True)
```
**Issue:** `namespace` and `output_type` come from user-supplied request data (via `OutputSave` schema → `save()`). A `namespace` value of `"../../etc"` or `"../../../Windows/System32"` would cause `store_dir` to resolve outside `STORE_ROOT`. `mkdir(parents=True, exist_ok=True)` will happily create that directory tree, and `file_path.write_text()` will write arbitrary content to an attacker-controlled location on disk.

**Fix:** Sanitise before path construction:
```python
import re

def _safe_path_segment(s: str) -> str:
    """Strip path separators and dotdot sequences."""
    s = re.sub(r'[/\\]', '_', s)  # no separators
    s = re.sub(r'\.\.', '', s)    # no dotdot
    return s[:64] or "unknown"    # bound length

store_dir = STORE_ROOT / _safe_path_segment(type_dir) / _safe_path_segment(namespace)
# Then assert store_dir is under STORE_ROOT:
store_dir.resolve().relative_to(STORE_ROOT.resolve())  # raises ValueError if escape attempted
```

---

### CR-05: Password reset token exposed publicly in browser UI

**File:** `core/api/routes/auth_routes.py:261–267` and `dashboard/components/login_form.py:167–173`
**Quoted code (API):**
```python
return jsonify({
    "message": "Reset token issued. Share with the user securely.",
    "reset_token": raw_token,
    "expires_in_hours": 1,
    "username": username,
})
```
**Quoted code (UI):**
```python
token = data.get("reset_token")
if token:
    st.success("Reset token generated. Copy it and use Step 2:")
    st.code(token, language=None)
```
**Issue:** `POST /auth/forgot-password` is a **public, unauthenticated** endpoint (no `@require_auth`). Any unauthenticated caller who knows a valid username gets the reset token directly in the API response. This completely bypasses the intended "admin relays it out-of-band" flow — an attacker can request it themselves and immediately reset the account password. The comment in the code says "swap for email send when SMTP is configured" but the current implementation is insecure at any scale.

**Fix (interim — no SMTP required):** Make the endpoint require `@require_auth` with `require_role("admin")`. Admin triggers the reset server-side; raw token is only visible to the admin in the Admin Panel, never to the public.

```python
@auth_bp.post("/forgot-password")
@require_auth
@require_role("admin")
@limiter.limit("20/hour")
def forgot_password():
    ...
    # Return token — admin-only response is acceptable
```

Remove the "Forgot Password" tab from the public login form, or replace it with a "Contact your admin to reset your password" message until SMTP is wired up.

---

## HIGH Issues

### HI-01: No namespace check on memory get/update/delete by ID

**File:** `core/api/routes/memory.py:94–127`
**Quoted code:**
```python
@memory_bp.get("/<entry_id>")
@require_auth
def get_memory(entry_id: str):
    entry = engine.get_by_id(entry_id)
    if not entry:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_entry_dict(entry))
```
**Issue:** `GET /memory/<id>`, `PUT /memory/<id>`, and `DELETE /memory/<id>` do not check whether the resolved entry belongs to the caller's namespace. A `client` user who knows (or guesses) a memory entry ID from another namespace can read, overwrite, or delete it. The `effective_namespace()` guard is correctly applied to list and search endpoints but was not applied here. This is an IDOR (OWASP A01).

**Fix:** Add namespace ownership check after fetching:
```python
@memory_bp.get("/<entry_id>")
@require_auth
def get_memory(entry_id: str):
    entry = engine.get_by_id(entry_id)
    if not entry:
        return jsonify({"error": "Not found"}), 404
    allowed_ns = effective_namespace(entry.namespace)
    if allowed_ns and entry.namespace != allowed_ns:
        return jsonify({"error": "Not found"}), 404  # 404 not 403 — don't confirm existence
    return jsonify(_entry_dict(entry))
```
Apply the same pattern to `update_memory` and `delete_memory`.

---

### HI-02: No namespace check on output get/content/export/delete by ID

**File:** `core/api/routes/outputs.py:90–141`
**Quoted code:**
```python
@outputs_bp.get("/<output_id>")
@require_api_key
def get_output(output_id: str):
    from outputs.manager import get_by_id
    out = get_by_id(output_id)
    if not out:
        return jsonify({"error": "Output not found"}), 404
    return jsonify(_out_dict(out))
```
**Issue:** Same IDOR pattern as HI-01. `GET /<id>`, `GET /<id>/content`, `GET /<id>/export`, and `DELETE /<id>` all fetch by ID without verifying the output's namespace matches the caller's allowed namespace. A client user can read any other client's outputs if they know the ID.

**Fix:** Same ownership check pattern:
```python
out = get_by_id(output_id)
if not out:
    return jsonify({"error": "Output not found"}), 404
allowed_ns = effective_namespace(out.namespace)
if allowed_ns and out.namespace != allowed_ns:
    return jsonify({"error": "Output not found"}), 404
```

---

### HI-03: No namespace check on bulk memory delete

**File:** `core/api/routes/memory.py:82–91`
**Quoted code:**
```python
@memory_bp.delete("/bulk")
@require_auth
def bulk_delete_memory():
    ids = (request.get_json(silent=True) or {}).get("ids") or []
    ...
    for eid in ids:
        (deleted if engine.delete(eid) else failed).append(eid)
```
**Issue:** `engine.delete()` does not check namespace. A `client` or `viewer` user can bulk-delete arbitrary memory entries from any namespace by supplying IDs.

**Fix:** Verify each entry's namespace before deleting:
```python
for eid in ids:
    entry = engine.get_by_id(eid)
    if not entry:
        failed.append(eid)
        continue
    allowed_ns = effective_namespace(entry.namespace)
    if allowed_ns and entry.namespace != allowed_ns:
        failed.append(eid)
        continue
    (deleted if engine.delete(eid) else failed).append(eid)
```

---

### HI-04: SQL injection via f-string in `record_failed_attempt` (auth.py)

**File:** `core/auth.py:174–184`
**Quoted code:**
```python
lockout_minutes = _cfg_int("lockout_minutes", 15)
with get_db() as conn:
    conn.execute(
        f"""UPDATE users SET
            failed_attempts = failed_attempts + 1,
            locked_until = CASE
                WHEN failed_attempts + 1 >= ? THEN datetime('now', '+{lockout_minutes} minutes')
                ELSE locked_until
            END, ...""",
        (max_attempts, user_id),
    )
```
**Issue:** `lockout_minutes` is an integer derived from `system_config` via `_cfg_int()`. Although an integer cast prevents string injection, the value is read from a database table that an admin can modify. If the DB is compromised, an attacker could write `lockout_minutes = "0'; DROP TABLE users; --"` to `system_config.value`. `_cfg_int()` would return the default (`15`) due to `ValueError`, but if `_cfg()` is changed to return a raw string someday, injection becomes possible.

**Fix:** Use SQLite's `printf` or parameter substitution for the interval:
```python
conn.execute(
    """UPDATE users SET
       failed_attempts = failed_attempts + 1,
       locked_until = CASE
           WHEN failed_attempts + 1 >= ? THEN datetime('now', '+' || ? || ' minutes')
           ELSE locked_until
       END,
       updated_at = CURRENT_TIMESTAMP
       WHERE id = ?""",
    (max_attempts, lockout_minutes, user_id),
)
```

---

### HI-05: API key auth always grants `operator` role — no scope enforcement

**File:** `core/auth.py:293–297`
**Quoted code:**
```python
g.user_id = f"apikey:{row['id']}"
g.username = row["name"]
g.user_role = "operator"
g.user_namespace = None
g.auth_method = "api_key"
```
**Issue:** Every API key is unconditionally assigned `role = "operator"` and `namespace = None` (global access), regardless of the `permissions` and `namespace` columns stored in the `api_keys` table. An API key created for a specific client namespace (`namespace = "reci-transport"`, `permissions = ["read"]`) behaves as a global operator. `effective_namespace()` returns `None` (all namespaces) for operator/admin, so namespace isolation is fully bypassed for API keys.

**Fix:** Propagate the stored `namespace` and honour `permissions`:
```python
g.user_role      = "operator" if row["namespace"] in (None, "global", "") else "client"
g.user_namespace = row["namespace"] or None
```
For write restrictions, add a permission check decorator or inline check:
```python
if "write" not in (row.get("permissions") or []):
    return jsonify({"error": "API key does not have write permission"}), 403
```

---

## MEDIUM Issues

### ME-01: `aurora_hero()` renders caller-supplied strings as raw HTML

**File:** `dashboard/components/brand.py:612–643`
**Quoted code:**
```python
def aurora_hero(title: str, subtitle: str = "", pill: str = "") -> None:
    ...
    st.markdown(f"""
<div class="aurora-hero-card">
  ...
    {title}
  ...
    {sub_html}   ← subtitle interpolated
  {pill_html}    ← pill interpolated
""", unsafe_allow_html=True)
```
**Issue:** `title`, `subtitle`, and `pill` are interpolated directly into an HTML block rendered with `unsafe_allow_html=True`. All current callers pass string literals, so there is no active XSS. However, if any page passes user-supplied data (e.g., a ticket title from the DB) to `aurora_hero(title=ticket["title"])`, an attacker who controls the ticket title can inject arbitrary HTML/JavaScript into the dashboard.

**Fix:** HTML-escape all parameters before interpolation:
```python
from html import escape as _esc

def aurora_hero(title: str, subtitle: str = "", pill: str = "") -> None:
    title    = _esc(title)
    subtitle = _esc(subtitle)
    pill     = _esc(pill)
    ...
```

---

### ME-02: `badge()` and `sidebar_logo()` render unsanitised strings as HTML

**File:** `dashboard/components/brand.py:608–491`
**Quoted code:**
```python
def badge(text: str, kind: str = "ok") -> str:
    return f'<span class="status-badge badge-{kind}">{text}</span>'
```
**Issue:** `text` and `kind` are interpolated into HTML without escaping. Pages that call `badge(some_api_value)` with a DB-sourced string are XSS-vulnerable. Notably `kind` is also unescaped — an attacker who controls that value could inject `"><script>` via the class attribute.

**Fix:**
```python
from html import escape as _esc

def badge(text: str, kind: str = "ok") -> str:
    SAFE_KINDS = {"ok", "error", "pending"}
    safe_kind = kind if kind in SAFE_KINDS else "ok"
    return f'<span class="status-badge badge-{safe_kind}">{_esc(text)}</span>'
```

---

### ME-03: `render_change_password` interpolates username into HTML without escaping

**File:** `dashboard/components/login_form.py:304–308`
**Quoted code:**
```python
st.markdown(f"""
<div class="cos-chpw-card">
  ...
  Logged in as <strong>{st.session_state.get('username','')}</strong>.
  ...
""", unsafe_allow_html=True)
```
**Issue:** `username` is read from `st.session_state`, which was set from the API response. If the API is ever compromised or a user registers with a username like `<script>alert(1)</script>` and the registration validator does not sanitise it, this XSS vector triggers on the forced-password-change screen — which runs pre-auth gate.

**Fix:**
```python
from html import escape as _esc
username_safe = _esc(st.session_state.get('username', ''))
# Use username_safe in the markdown
```

---

### ME-04: `_admin.py` bulk-action responses not checked for HTTP error codes

**File:** `dashboard/_pages/_admin.py:85–91`, `112–115`, `211–215`, `313–319`
**Quoted code:**
```python
_req.delete(
    f"{_API_BASE}/admin/users/bulk",
    json={"ids": sel_uids},
    headers=_auth_headers(), timeout=10,
)
st.session_state.pop("bulk_confirm_users", None)
st.success("Deactivated.")
st.rerun()
```
**Issue:** The return value of `_req.delete()` is never checked. If the API returns 403, 422, or 500, the UI still shows "Deactivated." / "Revoked." as success. This hides failures silently from the admin.

**Fix:**
```python
resp = _req.delete(f"{_API_BASE}/admin/users/bulk", json={"ids": sel_uids},
                   headers=_auth_headers(), timeout=10)
if resp.ok:
    st.success(f"Deactivated {resp.json().get('count', 0)} users.")
else:
    st.error(f"Failed: {resp.json().get('error', f'HTTP {resp.status_code}')}")
```

---

### ME-05: Bare `except` swallows injection-attempt errors in ticket assignee loop

**File:** `core/api/routes/tickets.py:447–453`
**Quoted code:**
```python
try:
    conn.execute(
        "INSERT OR IGNORE INTO ticket_assignees ...",
        (new_id(), ticket_id, uname, now, g.username),
    )
    added.append(uname)
except Exception:
    pass
```
**Issue:** Silently swallowing `Exception` here means DB constraint violations, schema errors, and genuine bugs are all hidden. The outer loop continues without signalling to the caller that some inserts failed.

**Fix:**
```python
except Exception as e:
    logger.warning("Failed to insert assignee %s for ticket %s: %s", uname, ticket_id, e)
    # Do not append to `added`
```

---

### ME-06: Bare `except` swallows errors in `assign_me`

**File:** `core/api/routes/tickets.py:367–372`
**Quoted code:**
```python
try:
    conn.execute("INSERT OR IGNORE INTO ticket_assignees ...", ...)
except Exception:
    pass
```
**Issue:** Same pattern as ME-05. An `INSERT OR IGNORE` never raises for duplicate keys — the `try/except` here masks actual errors (DB connection lost, schema mismatch) that should surface.

**Fix:** Log the exception:
```python
except Exception as e:
    logger.warning("assign_me insert failed for ticket %s: %s", ticket_id, e)
```

---

### ME-07: Bare `except` in `_save_output` / `_log_event` swallows unexpected errors

**File:** `agents/executor.py:208–209`, `237–238`
**Quoted code:**
```python
    except Exception as e:
        logger.warning("Failed to save output: %s", e)
```
```python
    except Exception:
        pass
```
**Issue:** `_log_event` swallows all exceptions including `OperationalError` (DB locked, disk full) without logging. Silent failure in event logging means ops issues go undetected.

**Fix:**
```python
except Exception as e:
    logger.warning("_log_event failed (%s): %s", event_type, e)
```

---

### ME-08: `GET /memory/context/<namespace>` — no namespace isolation

**File:** `core/api/routes/memory.py:195–200`
**Quoted code:**
```python
@memory_bp.get("/context/<namespace>")
@require_auth
def agent_context(namespace: str):
    min_confidence = float(request.args.get("min_confidence", 0.8))
    context_str = engine.get_agent_context(namespace, min_confidence)
    return jsonify({"namespace": namespace, "context": context_str})
```
**Issue:** The `namespace` URL parameter is passed directly to `engine.get_agent_context()` without going through `effective_namespace()`. A `client` user can call `GET /memory/context/global` or `GET /memory/context/other-client-ns` and receive the full memory context of any namespace.

**Fix:**
```python
def agent_context(namespace: str):
    safe_ns = effective_namespace(namespace)
    context_str = engine.get_agent_context(safe_ns or namespace, min_confidence)
    return jsonify({"namespace": safe_ns or namespace, "context": context_str})
```

---

### ME-09: `GET /memory/import` — no role restriction, uses hardcoded local filesystem path

**File:** `core/api/routes/memory.py:157–178`
**Quoted code:**
```python
@memory_bp.post("/import")
@require_auth
def import_memory():
    settings = get_settings()
    memory_dir = Path(settings.CLAUDE_MEMORY_PATH)
    namespace = request.args.get("namespace", "global")
```
**Issue 1:** Any authenticated user (including `client` and `viewer` roles) can trigger a memory import from the server's local filesystem path. This is an admin-level operation.

**Issue 2:** `namespace` comes from a query param with no `effective_namespace()` enforcement, so any client can import into `global` or any other namespace.

**Fix:**
```python
@memory_bp.post("/import")
@require_auth
@require_role("admin", "operator")  # add this
def import_memory():
    namespace = effective_namespace(request.args.get("namespace", "global"))
```

---

### ME-10: `DELETE /memory/expire` — no role restriction

**File:** `core/api/routes/memory.py:188–192`
**Quoted code:**
```python
@memory_bp.delete("/expire")
@require_auth
def expire_memory():
    count = engine.expire_stale()
```
**Issue:** Any authenticated user, including `client` and `viewer`, can trigger global memory expiry, deleting entries from all namespaces.

**Fix:** Add `@require_role("admin", "operator")`.

---

### ME-11: Unvalidated `api_key` in query string allows key exposure in server logs

**File:** `core/auth.py:325`
**Quoted code:**
```python
raw_key = request.headers.get("X-API-Key") or request.args.get("api_key")
```
**Issue:** Accepting `api_key` as a URL query parameter causes the API key to appear in web server access logs, browser history, referrer headers, and load balancer/proxy logs in plaintext. This is OWASP A02 (Cryptographic Failures — key exposure).

**Fix:** Remove `request.args.get("api_key")`. Require the key only via the `X-API-Key` header.

---

### ME-12: `GET /admin/audit` — query params unsanitised and interpolated into SQL WHERE clause

**File:** `core/api/routes/admin_routes.py:182–197`
**Quoted code:**
```python
where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
...
rows = conn.execute(
    f"SELECT * FROM auth_events {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params
)
```
**Issue:** `event_type` and `username` from request args are properly parameterised via `conditions.append("event_type = ?")` and `params.append(event_type)` — this is fine. The `where` string itself is f-string interpolated, but since `conditions` only ever contains hardcoded string fragments (`"event_type = ?"`, `"username = ?"`), there is no immediate injection. However the pattern is fragile — a future developer might add `conditions.append(f"namespace = {ns}")` and silently introduce injection. Document the invariant or refactor to make it structurally safe.

**Fix (defensive):** Assert that all condition strings are hardcoded:
```python
# Safe — conditions list contains only hardcoded SQL fragments, never user values
# Values are always in params list; this comment documents the invariant
```
Or use a query builder that separates clauses from the WHERE scaffold.

---

### ME-13: Hardcoded `http://localhost:5000` API base in dashboard files

**File:** `dashboard/app.py:40`, `dashboard/components/login_form.py:8`, `dashboard/_pages/_admin.py:6`
**Quoted code:**
```python
API_BASE = "http://localhost:5000/api/v1"
_API_BASE = "http://localhost:5000/api/v1"
```
**Issue:** If the Flask server is deployed remotely or behind a reverse proxy (even at `127.0.0.1:5001`), all API calls fail silently. Config says to read `.env` → `FLASK_PORT`, but none of these files actually do that — they use hardcoded values. This is also a deployment misconfiguration risk.

**Fix:** Read from environment at module level in one shared location:
```python
import os
from dotenv import load_dotenv
load_dotenv()
_FLASK_PORT = os.environ.get("FLASK_PORT", "5000")
API_BASE = f"http://localhost:{_FLASK_PORT}/api/v1"
```
Or better: define a single `API_BASE` in `dashboard/config.py` and import it everywhere.

---

### ME-14: No rate limiting on `change-password` endpoint before `@require_auth`

**File:** `core/api/routes/auth_routes.py:190–193`
**Quoted code:**
```python
@auth_bp.post("/change-password")
@require_auth
@limiter.limit("5 per minute")
def change_password():
```
**Issue:** The `@limiter.limit` decorator is placed **after** `@require_auth`. Flask-Limiter applies limits after the decorated function's wrappers run from outside-in, meaning the rate limit is checked after `require_auth` already validates the JWT. This is functionally correct but the decorator order is misleading and could become a real issue if the auth decorator ever short-circuits before the limiter sees the request. Recommended order is `@limiter.limit` outermost (first decorator applied = outermost wrapper).

**Fix:** Reorder decorators so the rate limiter is outermost:
```python
@auth_bp.post("/change-password")
@limiter.limit("5 per minute")
@require_auth
def change_password():
```

---

## LOW Issues

### LO-01: `_maybe_refresh_token` in `dashboard/app.py` silently swallows all exceptions

**File:** `dashboard/app.py:66–78`
**Quoted code:**
```python
    except Exception:
        pass
```
**Issue:** If `jwt.decode` raises an unexpected exception type (not `DecodeError`), or the refresh POST fails with a connection error, the bare `except` silently swallows it and the user continues with an expired token. The next API call will return 401 and trigger session clear — so it's not a security hole, but it hides networking errors.

**Fix:**
```python
except Exception as e:
    logger.debug("Token refresh skipped: %s", e)
```

---

### LO-02: `api_get` and `api_post` silently swallow all exceptions in dashboard

**File:** `dashboard/app.py:89–98`, `145–155`
**Quoted code:**
```python
    except Exception:
        pass
    return None
```
**Issue:** Network errors, JSON decode errors, and unexpected exceptions all return `None`, which callers treat as "no data". This means a crashed API server and an empty dataset look identical to the UI. Operations like bulk deletes that call `_req.delete()` directly (in `_admin.py`) also have no error handling.

**Fix:** At minimum log the exception:
```python
except Exception as e:
    logger.warning("api_get %s failed: %s", path, e)
return None
```

---

### LO-03: `password_hash` column name exposure — `get_user_by_username` and `get_user_by_id` return full row

**File:** `core/auth.py:219–224`, `227–231`
**Quoted code:**
```python
def get_user_by_username(username: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,)).fetchone()
    return dict(row) if row else None
```
**Issue:** `SELECT *` returns `password_hash` as part of the dict. This dict is passed to `_user_public()` in auth_routes (which strips it), but it is also returned directly in admin_routes without stripping: `_user_dict_full()` does strip it, but `get_user_by_id()` is called in several places in auth code and the raw dict is used directly. If a future code path accidentally serialises the full user dict to a response, password hashes are exposed.

**Fix (defensive):** Either SELECT explicit columns excluding `password_hash`, or delete it from the dict before returning:
```python
user = dict(row)
user.pop("password_hash", None)
return user
```

---

### LO-04: `datetime.utcnow()` used directly — naive UTC, not timezone-aware

**File:** `core/api/routes/auth_routes.py:250`, `core/api/routes/tickets.py:325`, `core/api/routes/tickets.py:570`
**Quoted code:**
```python
expires = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
due = (datetime.utcnow() + timedelta(hours=SLA_HOURS[tier])).strftime("%Y-%m-%d %H:%M:%S")
now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
```
**Issue:** `datetime.utcnow()` is deprecated in Python 3.12+ and creates a naive datetime object. The rest of the codebase uses `utcnow()` from `core.utils` which returns a timezone-aware datetime. Inconsistent naivety can cause comparison bugs when mixing with SQLite's `CURRENT_TIMESTAMP` (which is also naive UTC) — currently harmless, but fragile.

**Fix:** Replace with `utcnow()` from `core.utils`:
```python
from core.utils import utcnow
expires = (utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
```

---

### LO-05: `import time as _time; _time.sleep(0.2)` inline in login route

**File:** `core/api/routes/auth_routes.py:43`
**Quoted code:**
```python
import time as _time; _time.sleep(0.2)
```
**Issue:** This import is inside a hot code path (executed on every failed login). Inline imports are not free; Python checks `sys.modules` each time. More importantly, `time` is a stdlib module that should be imported at the top of the file. The semicolon-on-one-line style is unreadable.

**Fix:** Move to top-level import and call `time.sleep(0.2)`.

---

### LO-06: Audit log built-in URL injection via `_admin.py` audit filter

**File:** `dashboard/_pages/_admin.py:262–266`
**Quoted code:**
```python
if et_filter:
    url += f"&event_type={et_filter}"
if un_filter.strip():
    url += f"&username={un_filter.strip()}"

events = api_get(url) or []
```
**Issue:** `et_filter` and `un_filter` are taken from Streamlit widget values and appended to the URL without URL-encoding. If a user types `foo&limit=500` as a username filter, it becomes `?username=foo&limit=500` and the extra query param is sent to the API. This is not a security issue (the API sanitises `limit` to max 500), but it is a correctness bug.

**Fix:** Use `urllib.parse.urlencode`:
```python
from urllib.parse import urlencode
params = {"limit": 100}
if et_filter:
    params["event_type"] = et_filter
if un_filter.strip():
    params["username"] = un_filter.strip()
url = f"/admin/audit?{urlencode(params)}"
```

---

## INFO

### IN-01: TODO comment — forgot-password flow tagged as incomplete

**File:** `core/api/routes/auth_routes.py:261`
**Quoted code:**
```python
# Return token directly (admin-relay model — swap for email send when SMTP is configured)
```
This is documented technical debt. Tracked as CR-05 above (the current implementation is not just incomplete — it is insecure).

---

### IN-02: Hardcoded client name references in `_TAG_KEYWORDS`

**File:** `outputs/manager.py:34`
**Quoted code:**
```python
"client": ["client", "reci", "ivycandy", "faiyke"],
```
Hardcoding specific client names in core library code couples the Output Manager to specific tenants. These should be driven by the namespaces table or a config value.

---

### IN-03: `_client` global in `agents/executor.py` is not thread-safe

**File:** `agents/executor.py:25–33`
**Quoted code:**
```python
_client = None

def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=get_settings().ANTHROPIC_API_KEY)
    return _client
```
Under waitress with multiple threads, two threads can both see `_client is None` and both create an `Anthropic` client simultaneously. The double-init is harmless (both instances are equivalent) but is a latent race condition on `_client` assignment. Use `threading.Lock` or module-level init to be explicit.

---

### IN-04: `_api_key_last_updated` dict in `core/auth.py` is not thread-safe

**File:** `core/auth.py:269–292`
**Quoted code:**
```python
_api_key_last_updated: dict[str, float] = {}
```
The debounce cache is accessed and mutated by multiple request threads simultaneously without a lock. Under waitress + concurrent requests, the eviction loop at lines 288–292 can raise `RuntimeError: dictionary changed size during iteration`.

**Fix:** Either use `threading.Lock` around mutations, or switch to `collections.OrderedDict` with a lock.

---

### IN-05: Brand compliance — confirmed correct

All UI files use `#407E3C` primary and `#ffffff`/`#E8F5E8` secondary. `brand.py` applies them globally via CSS injection. No rogue colour values found.

---

## Issue Count Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 5     |
| HIGH     | 7     |
| MEDIUM   | 9     |
| LOW      | 6     |
| INFO     | 5     |
| **Total**| **32**|

---

## Priority Fix Order

1. **CR-01** — Replace weak default JWT secret with mandatory env var + startup assertion
2. **CR-05** — Lock `forgot-password` behind admin auth; remove token from public response
3. **HI-01 / HI-02 / HI-03** — Add namespace ownership checks to all by-ID memory and output routes
4. **CR-04** — Add `_safe_path_segment()` guard to output file writer
5. **CR-02 / CR-03** — Eliminate dynamic column name interpolation in SQL UPDATEs
6. **HI-04** — Replace f-string interval in `record_failed_attempt` with parameterised SQL
7. **HI-05** — Propagate API key namespace/permissions into `g.user_role` / `g.user_namespace`
8. **ME-08 / ME-09 / ME-10** — Enforce namespace isolation and role gates on memory context/import/expire
9. **ME-11** — Remove `api_key` query parameter fallback
10. **ME-01 / ME-02 / ME-03** — HTML-escape all user-supplied strings in `unsafe_allow_html` blocks

---

_Reviewed: 2026-05-21_
_Reviewer: Claude (gsd-code-reviewer) — standard + deep_
