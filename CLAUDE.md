# CLAUDE.md — ClaudeOS Project Rules

## Project
ClaudeOS — AI Operating System. Coordination layer unifying all Claude Code skills, agents, and workflows into a single authenticated control center.
Brand: #407E3C green + white. Target: Windows 10 / PowerShell.

## Architecture
```
Browser (Streamlit :8501)
  └─ Login gate → st.session_state["jwt_token"]
      └─ api_get/api_post → Authorization: Bearer <token>
          └─ Flask :5000
              ├─ require_auth (JWT or X-API-Key fallback)
              ├─ require_role("admin") → /api/v1/admin/*
              └─ All existing routes (memory, agents, outputs, tickets, etc.)

Layer 0: Streamlit dashboard (:8501) — login-gated, role-filtered nav
Layer 1: Flask REST API (:5000) — JWT + X-API-Key auth on all routes
Layer 2: Memory Engine (SQLite FTS5 + ChromaDB)
Layer 3: Agent Registry (12 agents, YAML definitions)
Layer 4: Workflow Engine (APScheduler, 7 pipelines)
Layer 5: Client Vault (namespace isolation)
Layer 6: Output Manager (auto-tag, FTS, export)
Layer 7: Supabase Cloud Sync (push-only, 15-min auto)
Layer 8: Auth & Security (JWT, bcrypt, roles, audit log)
Layer 9: Ticketing System (SLA tiers, staff role, bulk ops)
```

## Critical Files
- `core/api/app.py` — Flask factory, all routes bootstrap here
- `core/auth.py` — JWT, bcrypt, session management, decorators, audit log
- `core/api/routes/auth_routes.py` — /api/v1/auth/* (login, register, refresh, logout, me)
- `core/api/routes/admin_routes.py` — /api/v1/admin/* (users, sessions, API keys, audit, security config)
- `core/api/routes/tickets.py` — /api/v1/tickets/* (ticketing REST API)
- `memory/engine.py` — memory facade, all agents call this
- `agents/executor.py` — Claude API wrapper, injects namespace context
- `workflows/pipeline.py` — step executor for all 7 workflows
- `dashboard/app.py` — Streamlit entry point, auth gate, role nav
- `dashboard/components/login_form.py` — branded login + self-registration form (st.form, Enter-to-submit)
- `dashboard/components/brand.py` — CSS injection, theme toggle, all visual primitives
- `dashboard/_pages/_admin.py` — Admin Panel UI (users, API keys, audit, sessions, security)
- `scripts/create_admin.py` — first-run admin seed script

## Stack
- Python: Flask (API), Streamlit (dashboard)
- AI: anthropic SDK, claude-sonnet-4-6
- Auth: PyJWT==2.9.0, bcrypt==4.2.0
- Memory: SQLite FTS5, ChromaDB, sentence-transformers
- Scheduler: APScheduler BackgroundScheduler
- WSGI: waitress (not gunicorn — Windows)
- Testing: pytest

## Auth & Security Rules
- All API routes require auth (`@require_auth`) — JWT Bearer or X-API-Key fallback
- `/api/v1/health` is the ONLY public endpoint
- Roles: admin (all access) | operator (all namespaces, no user mgmt) | client (own namespace only) | viewer (own namespace, read-only) | staff (assigned tickets only — can self-assign and advance ticket status)
- JWT access tokens: 60 min TTL. Refresh tokens: 7 days, stored as SHA-256 hash
- Passwords: bcrypt 12 rounds, min 10 chars, upper+lower+digit required
- Account lockout: 5 failed attempts → 15-min lock (configurable via system_config)
- `must_change_password` flag: user forced to change on next login
- Client one-per-namespace enforced in application layer
- Never expose raw refresh tokens in logs or responses beyond initial issue
- `effective_namespace()` in auth.py enforces client scoping — never trust client-supplied namespace
- Username lookup uses `LOWER()` match — login is case-insensitive

## Database Tables (Auth Layer)
- `users` — id, username, email, password_hash, role, namespace, is_active, failed_attempts, locked_until, must_change_password
- `user_sessions` — refresh token hashes, ip, ua, expires_at, revoked
- `auth_events` — full audit log: login_success/failure, logout, token_refresh, user_created, lockout_triggered, etc.
- `system_config` — key/value security settings (max_failed_attempts, lockout_minutes, token TTLs, allow_self_register)

## Dashboard Rules
- `inject()` and `theme_toggle()` MUST be called BEFORE the auth gate (`st.stop()`) — they need to render on the login page
- Theme toggle lives at bottom-left: `position:fixed;bottom:24px;left:16px;z-index:2147483647`
- Sidebar renders AFTER auth gate — it is only visible to logged-in users
- Role-based nav: clients/viewers do not see Settings, Workflows, Admin; admin sees Admin tab; staff sees Tickets only
- Auto token refresh: `api_get` decodes token locally, if expiry < 5 min away → call `/auth/refresh` silently
- 401 response from any API call → clear session_state + `st.rerun()` (returns user to login)
- Login form uses `st.form` — password field submits on Return key (Enter-to-submit)

## Performance Patterns
- Parallel API calls via `ThreadPoolExecutor` — all overview data fetched in one shot (5 concurrent)
- N+1 → parallel: namespace workspace + projects fetched concurrently in Client Vault
- Ticket assignees batch-fetched in a single `WHERE id IN (...)` query — not 1 per ticket
- Ticket comments lazy-loaded: only fetched when user opens the "💬 Comments" toggle
- `_cached_api_get` cache key includes JWT token — prevents cross-user cache pollution
- Bulk session revoke: single `UPDATE ... WHERE id IN (...)` — not a per-session loop
- Outputs bulk delete: single DB transaction via `delete_bulk()` in `outputs/manager.py`
- Admin `/namespaces` fetched once in `render()`, passed to Users and API Keys tabs — not called twice
- `_is_assignee` uses EXISTS point query — no full assignee list fetch
- User validation: single `WHERE username IN (...)` batch query — not 1 query per username
- `ticket_stats`: 5 metrics aggregated in 3 queries via `SUM(CASE WHEN ...)` conditionals
- `idx_events_created` index on `system_events(created_at DESC)` — added in migration 012
- `_api_key_last_updated` dict bounded to 500 entries with TTL eviction — no unbounded growth
- Security settings update uses `executemany` — not a per-row loop
- TTL config cache in `core/auth.py:_cfg()` — 60s in-process cache, avoids per-request DB hit
- Single DB connection per operation in `_validate_api_key_header` — no redundant transactions
- `memory/store.py:update()` — check `cursor.rowcount` before post-fetch, avoids dead reads

## Theme System
- Dark/light mode driven by `st.session_state["theme"]` ("dark"/"light")
- `get_theme_vars()` in brand.py returns CSS vars dict based on current theme
- `_build_css(t)` generates the full CSS string from theme vars — one call, entire app styled
- `inject()` must be called on every page render (it re-injects fresh CSS matching current theme)
- Password eye icon: `[data-testid="stTextInput"] button` + SVG `fill: {t['TEXT']}` override
- Theme toggle: circular 44px icon button, no text label
  - Dark mode: dark navy `#111827` circle + white 8-ray sun SVG + small white dot
  - Light mode: light gray `#f0f0f0` circle + dark crescent moon SVG
  - Hover scales 1.1×
- Aurora background removed — no `@keyframes aurora`, no animated gradient layers, no `backdrop-filter: blur()` or `will-change: transform`

## Rules
- Never use gunicorn — use waitress on Windows
- Always `encoding='utf-8'` on file reads/writes
- Never commit .env, vault workspace files, or data/claudeos.db
- Namespace isolation is mandatory — no cross-namespace memory reads
- Every agent run logs to agent_runs table
- Every output saves to outputs table + file system
- Port detection: read .env FLASK_PORT/STREAMLIT_PORT first
- Never use `&&` in shell — use `;` or separate calls (PowerShell)

## Server Start
```powershell
.\scripts\start.ps1
```
Kills :5000 and :8501 first, starts Flask via waitress, verifies /health, then starts Streamlit.

## First-Run Setup (new install)
```powershell
pip install -r requirements.txt
python scripts/migrate.py
python scripts/seed_agents.py
python scripts/seed_workflows.py
python scripts/seed_namespaces.py
python scripts/create_admin.py --username admin --password Admin123!
.\scripts\start.ps1
```

## Phase Status — ALL COMPLETE
- Phase 1: Core Infrastructure ✅
- Phase 2: Memory Engine ✅
- Phase 3: Agent Registry + Control Center ✅
- Phase 4: Workflow Engine ✅
- Phase 5: Client/Project Vault ✅
- Phase 6: Output Manager ✅
- Phase 7: Cloud Deployment (Supabase Sync) ✅
- Phase 8: Auth, Admin Backend & Multi-User Login ✅
  - JWT access + opaque refresh tokens
  - bcrypt passwords, account lockout, audit log
  - Admin Panel: user management, API keys, sessions, security config
  - Login gate with self-registration (configurable)
  - Role-based nav + namespace isolation enforced end-to-end
  - must_change_password enforcement
  - Performance: parallel fetches, TTL cache, N+1 eliminated
  - Responsive CSS (mobile ≤600px, tablet ≤900px)
  - Dark/light theme toggle (bottom-left, persists in session)
- Phase 9: Ticketing System + Bulk Delete ✅
  - Full ticket lifecycle: create, assign, status transitions, resolution notes
  - SLA tiers: P1 (critical) · P2 (high) · P3 (medium) · P4 (low)
  - Comments on tickets, lazy-loaded
  - Bulk delete across all resource types: memory, agents/runs, outputs, tickets
  - Checkbox + bulk toolbar UI on every list page
  - New `staff` role: assigned tickets only, can self-assign and advance status
  - Enter-to-submit login via `st.form`
  - Case-insensitive username login (`LOWER()` match)
  - Circular icon theme toggle (no text label, 44px, dark navy / light gray)
  - Aurora background removed (GPU/CPU reduction)
  - 12 additional performance fixes (batch queries, EXISTS, bounded cache, executemany, lazy comments, scoped cache keys, index migration)
