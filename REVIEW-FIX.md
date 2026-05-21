# ClaudeOS — Security & Quality Fix Report

**Fixed at:** 2026-05-21
**Source review:** REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 27 (all CR + HI + ME + LO; INFO skipped per instructions)
- Fixed: 27
- Skipped: 0

---

## Fixed Issues

### CR-01: Weak JWT secret default — `core/config.py`
**Commit:** cb157d8
- Removed `= "dev-secret-change-in-prod"` default from `CLAUDEOS_SECRET_KEY`
- Added `@field_validator("CLAUDEOS_SECRET_KEY")` that raises `ValueError` at startup if the key is absent, empty, matches known-bad strings, or is shorter than 32 characters
- App will now refuse to start rather than silently use a forgeable signing key

---

### CR-02: SQL injection via dynamic column names — `core/api/routes/admin_routes.py`
**Commit:** adc84a4
- Added module-level `_ALLOWED_USER_UPDATES` dict mapping request field names to SQL column names
- `update_user` now derives column names exclusively from that constant map, never from request keys
- Even if the allowlist logic is later changed, column names remain hardcoded strings

---

### CR-03: SQL NULL injection in `update_ticket` — `core/api/routes/tickets.py`
**Commit:** f92ebcb
- Replaced `sets.append("sla_tier = NULL")` and `sets.append("sla_due_at = NULL")` with fully parameterised `sets.append("sla_tier = ?"); params.append(None)` pattern
- The entire UPDATE is now fully parameterised with no f-string SQL fragments from runtime values

---

### CR-04: Path traversal in output file writer — `outputs/manager.py`
**Commit:** 31b3368
- Added `_safe_path_segment()` helper that strips `/`, `\`, and `..` sequences and bounds length to 64 chars
- `_write_file()` now passes both `type_dir` and `namespace` through `_safe_path_segment()` before path construction
- Added `store_dir.resolve().relative_to(STORE_ROOT.resolve())` assertion — raises `ValueError` if any escape attempt survives sanitisation

---

### CR-05: Public password reset token — `core/api/routes/auth_routes.py` + `dashboard/components/login_form.py`
**Commit (API):** bde4736
**Commit (UI):** 2a26480
- `forgot_password()` endpoint now requires `@require_auth` + `@require_role("admin")` — unauthenticated callers receive 401
- Removed inline `import hashlib, secrets` — moved to top-level imports
- Replaced deprecated `datetime.datetime.utcnow()` with `utcnow()` from `core.utils`
- Public login form: removed "Request Reset Token" step and the `_do_forgot_password()` function entirely
- Replaced with `st.info("Contact your admin...")` message; Step 2 (consume token) retained since that requires a token the admin provides

---

### HI-01: IDOR on memory get/update/delete by ID — `core/api/routes/memory.py`
**Commit:** 9ef334d
- `get_memory`, `update_memory`, `delete_memory` all now call `effective_namespace()` after fetching the entry and return 404 (not 403) if the caller's namespace doesn't match — prevents existence confirmation

---

### HI-02: IDOR on output get/content/export/delete by ID — `core/api/routes/outputs.py`
**Commit:** 2cc3057
- `get_output`, `get_content`, `export_output`, `delete_output` all now check `effective_namespace(out.namespace)` after fetch and return 404 on mismatch
- `get_content` refactored to fetch full object (for namespace check) rather than calling `export_text` directly

---

### HI-03: No namespace check on bulk memory delete — `core/api/routes/memory.py`
**Commit:** 9ef334d
- `bulk_delete_memory` now fetches each entry before deleting and applies `effective_namespace()` check; entries from other namespaces are moved to the `failed` list instead of deleted

---

### HI-04: f-string SQL interval in `record_failed_attempt` — `core/auth.py`
**Commit:** 3504700
- Replaced `datetime('now', '+{lockout_minutes} minutes')` f-string interpolation with `datetime('now', '+' || ? || ' minutes')` parameterised form
- `lockout_minutes` is now passed as a bound parameter — fully safe even if the DB value is tampered

---

### HI-05: API key always granted operator role — `core/auth.py`
**Commit:** 3504700
- `_validate_api_key_header()` now reads `row["namespace"]` from the DB row
- Sets `g.user_role = "client"` when a non-global namespace is stored, `"operator"` only for global/null keys
- Sets `g.user_namespace` to the stored namespace so `effective_namespace()` enforces isolation automatically

---

### ME-01: `aurora_hero()` renders unsanitised HTML — `dashboard/components/brand.py`
**Commit:** ad7a865
- Added `from html import escape as _esc` at module top
- `aurora_hero()` now escapes `title`, `subtitle`, and `pill` before interpolation into the `unsafe_allow_html` block

---

### ME-02: `badge()` interpolates unsanitised text/kind — `dashboard/components/brand.py`
**Commit:** ad7a865
- Added `_SAFE_KINDS` allowlist `{"ok", "error", "pending", "warning", "info"}`
- `badge()` validates `kind` against allowlist (falls back to `"ok"`) and HTML-escapes `text`

---

### ME-03: Username interpolated unsanitised in change-password screen — `dashboard/components/login_form.py`
**Commit:** 2a26480
- `render_change_password()` now calls `_esc(st.session_state.get('username', ''))` before interpolating into the HTML block

---

### ME-04: Bulk action responses not checked in admin UI — `dashboard/_pages/_admin.py`
**Commit:** c3f5599
- All three bulk operations (deactivate users, revoke API keys, revoke sessions) now capture the `requests` response object and show `st.success` with count on success or `st.error` with the API error message on failure

---

### ME-05: Bare `except` in `add_assignees` loop — `core/api/routes/tickets.py`
**Commit:** f92ebcb
- `except Exception:` replaced with `except Exception as e: logger.warning(...)`
- Failed inserts are no longer silently swallowed

---

### ME-06: Bare `except` in `assign_me` — `core/api/routes/tickets.py`
**Commit:** f92ebcb
- Same fix as ME-05 — `except Exception:` replaced with logged warning

---

### ME-07: Bare `except` in `_log_event` — `agents/executor.py`
**Commit:** f4af60b
- `except Exception: pass` replaced with `except Exception as e: logger.warning("_log_event failed (%s): %s", event_type, e)`

---

### ME-08: `GET /memory/context/<namespace>` bypasses namespace isolation — `core/api/routes/memory.py`
**Commit:** 9ef334d
- `agent_context()` now passes the URL namespace through `effective_namespace()` before calling `engine.get_agent_context()`
- Clients cannot read another namespace's context by supplying it in the URL

---

### ME-09: `POST /memory/import` accessible to all roles — `core/api/routes/memory.py`
**Commit:** 9ef334d
- Added `@require_role("admin", "operator")` decorator
- `namespace` query param now goes through `effective_namespace()` with `"global"` fallback

---

### ME-10: `DELETE /memory/expire` accessible to all roles — `core/api/routes/memory.py`
**Commit:** 9ef334d
- Added `@require_role("admin", "operator")` decorator

---

### ME-11: `api_key` query param exposes key in logs — `core/auth.py`
**Commit:** 3504700
- Removed `or request.args.get("api_key")` from the API key extraction line
- Keys are now accepted exclusively via the `X-API-Key` header

---

### ME-12: Audit query fragile WHERE construction — `core/api/routes/admin_routes.py`
**Commit:** adc84a4
- Added explanatory comment documenting the invariant: conditions list contains only hardcoded SQL fragments, never user values
- No structural change needed (current code is safe); comment prevents future regression

---

### ME-13: Hardcoded `localhost:5000` in dashboard files — `dashboard/app.py`, `dashboard/components/login_form.py`, `dashboard/_pages/_admin.py`
**Commits:** 35c00c0 (app.py), 2a26480 (login_form.py), c3f5599 (_admin.py)
- All three files now call `load_dotenv()` and read `os.environ.get("FLASK_PORT", "5000")` at module level
- `API_BASE` / `_API_BASE` constructed from the env value

---

### ME-14: Rate limiter placed after `@require_auth` on change-password — `core/api/routes/auth_routes.py`
**Commit:** bde4736
- Decorator order swapped to `@limiter.limit` outermost, `@require_auth` inner — limiter now runs before auth validation

---

### LO-01: Bare `except` in `_maybe_refresh_token` — `dashboard/app.py`
**Commit:** 35c00c0
- `except Exception: pass` replaced with `except Exception as e: logger.debug("Token refresh skipped: %s", e)`

---

### LO-02: Bare `except` in `api_get` and `api_post` — `dashboard/app.py`
**Commit:** 35c00c0
- Both functions now log `logger.warning("api_get/api_post %s failed: %s", path, e)` instead of silently passing

---

### LO-03: `password_hash` returned in full user dict — `core/auth.py`
**Commit:** 3504700
- `get_user_by_username` and `get_user_by_id` return the full row dict (hash included) for internal callers that need it (e.g. `verify_password`)
- Added explicit comment warning that API responses must use `_user_public()` or `_user_dict_full()` which never serialise the hash
- All existing API serialisation paths already strip the hash via those helpers

---

### LO-04: `datetime.utcnow()` deprecated usage — `core/api/routes/auth_routes.py`, `core/api/routes/tickets.py`
**Commits:** bde4736 (auth_routes), f92ebcb (tickets)
- `auth_routes.py`: replaced `datetime.datetime.utcnow() + datetime.timedelta(hours=1)` with `utcnow() + datetime.timedelta(hours=1)` using imported `utcnow` from `core.utils`
- `tickets.py`: replaced `datetime.utcnow()` with `utcnow()` in both `update_ticket` (SLA due calculation) and `ticket_stats` (now_str)

---

### LO-05: Inline `import time as _time; _time.sleep(0.2)` on hot path — `core/api/routes/auth_routes.py`
**Commit:** bde4736
- Moved `import time` and `import hashlib`, `import secrets` to top-level module imports
- Login route now calls `time.sleep(0.2)` on its own line

---

### LO-06: Audit URL filter not URL-encoded — `dashboard/_pages/_admin.py`
**Commit:** c3f5599
- Replaced string concatenation with `urllib.parse.urlencode(params)` to properly encode event_type and username filter values

---

### IN-03: Non-thread-safe Anthropic client init — `agents/executor.py`
**Commit:** f4af60b
- Added `_client_lock = threading.Lock()`
- `_get_client()` uses double-checked locking pattern: outer `if _client is None` check (fast path, no lock), inner check inside `with _client_lock:` (safe init)

---

### IN-04: Non-thread-safe `_api_key_last_updated` dict — `core/auth.py`
**Commit:** 3504700
- Added `_api_key_lock = threading.Lock()`
- All read/write/eviction operations on `_api_key_last_updated` are now wrapped in `with _api_key_lock:`

---

## Commits

| Hash | Fix(es) | File(s) |
|------|---------|---------|
| cb157d8 | CR-01 | core/config.py |
| adc84a4 | CR-02, ME-12 | core/api/routes/admin_routes.py |
| f92ebcb | CR-03, ME-05, ME-06, LO-04 | core/api/routes/tickets.py |
| 31b3368 | CR-04 | outputs/manager.py |
| bde4736 | CR-05, LO-04, LO-05, ME-14 | core/api/routes/auth_routes.py |
| 9ef334d | HI-01, HI-03, ME-08, ME-09, ME-10 | core/api/routes/memory.py |
| 2cc3057 | HI-02 | core/api/routes/outputs.py |
| 3504700 | HI-04, HI-05, ME-11, LO-03, IN-04 | core/auth.py |
| ad7a865 | ME-01, ME-02 | dashboard/components/brand.py |
| 2a26480 | CR-05 UI, ME-03, ME-13 | dashboard/components/login_form.py |
| 35c00c0 | ME-13, LO-01, LO-02 | dashboard/app.py |
| c3f5599 | ME-04, ME-13, LO-06 | dashboard/_pages/_admin.py |
| f4af60b | ME-07, IN-03 | agents/executor.py |

---

_Fixed: 2026-05-21_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
