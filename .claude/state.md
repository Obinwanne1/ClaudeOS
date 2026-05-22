# ClaudeOS Phase State

## Current Phase: 9 — All Phases Complete ✅

## Completed Phases
- Phase 1: Core Infrastructure
- Phase 2: Memory Engine
- Phase 3: Agent Registry + Control Center
- Phase 4: Workflow Engine
- Phase 5: Client/Project Vault
- Phase 6: Output Manager
- Phase 7: Cloud Deployment

## Phase 7 — What Was Built

### Files Created
- `sync/__init__.py`
- `sync/engine.py` — watermark-based push-only sync engine
- `sync/schemas.py` — SyncResult, SyncStatus Pydantic models
- `sync/supabase_schema.sql` — SQL to run in Supabase dashboard
- `core/api/routes/sync.py` — 4 Flask endpoints
- `dashboard/pages/_settings.py` — Settings page with sync controls
- `memory/db/migrations/002_sync_state.sql` — sync_state + sync_log tables

### Files Modified
- `core/api/app.py` — registered sync blueprint
- `dashboard/app.py` — wired Settings page (was placeholder)
- `workflows/scheduler.py` — added _register_sync_job, _run_sync_job

### API Endpoints
- GET  /api/v1/sync/status
- POST /api/v1/sync/push          (body: {} or {"table": "outputs"})
- POST /api/v1/sync/reset-watermark
- GET  /api/v1/sync/log

### Architecture
- Push-only: SQLite is source of truth, Supabase is cloud mirror
- Watermark: tracks last_synced_at per table in sync_state
- Auto-sync: APScheduler job every 15min (activates when SUPABASE_URL+KEY set)
- Tables synced: memory_entries, agent_runs, outputs, namespaces, projects, system_events

### To Activate Cloud Sync
Add to .env:
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=service_role_key_here
```
Then run sync/supabase_schema.sql in Supabase SQL Editor.

## All 9 Phases Complete
ClaudeOS is fully built. Architecture is stable.

## Post-Phase Bug Fixes (2026-05-22)

### Theme Toggle
- Restored circular icon button (44px, bottom-left fixed)
- `st.html()` is sandboxed — scripts cannot access parent DOM
- `st.markdown` strips `<script>` tags
- Fix: `st.components.v1.html(height=0)` — same-origin iframe, JS uses `window.parent.document`
- Hides Streamlit trigger button via MutationObserver + CSS

### Agent Runs Namespace Isolation (Overview)
- Bug: `/agents/runs` was in `_READ_ONLY_PREFIXES` — cached globally, `/agents` prefix matched via `startswith`
- Fix 1: removed `/agents/runs` from prefixes; added explicit bypass in `api_get_cached` before prefix check
- Fix 2: `_overview.py` now builds `_runs_url` with `namespace={user_ns}` for scoped users
- Fix 3: `effective_namespace()` in `core/auth.py` — fallback to `requested` param if `g.user_namespace` is null
- Result: client users see only their namespace runs on Overview; admin sees all namespaces
