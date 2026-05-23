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
              └─ All routes (memory, agents, outputs, tickets, workflows, etc.)

Layer 0:  Streamlit dashboard (:8501) — login-gated, role-filtered nav, 10 pages
Layer 1:  Flask REST API (:5000) — JWT + X-API-Key auth on all routes
Layer 2:  Memory Engine (SQLite FTS5 + ChromaDB + hybrid BM25 retrieval)
Layer 3:  Agent Registry (12 agents, YAML definitions)
Layer 4:  Workflow Engine (APScheduler, 7 pipelines, webhook triggers)
Layer 5:  Client Vault (namespace isolation)
Layer 6:  Output Manager (auto-tag, FTS, export)
Layer 7:  Supabase Cloud Sync (push-only, 15-min auto)
Layer 8:  Auth & Security (JWT, bcrypt, roles, audit log)
Layer 9:  Ticketing System (SLA tiers, staff role, bulk ops)
Layer 10: Real-Time Intelligence (SSE streaming, LLM-as-Judge eval, Observability)
Layer 11: Advanced Memory (hybrid RAG, tiered context, consolidation, contextual prefixing)
Layer 12: Protocols (MCP Tool Server :5100, A2A Agent Cards, webhook triggers)
Layer 13: Multimodal (multi-turn chat, image analysis, voice input, live dashboard)
```

## Critical Files
- `core/api/app.py` — Flask factory, all routes bootstrap here
- `core/auth.py` — JWT, bcrypt, session management, decorators, audit log
- `core/api/routes/auth_routes.py` — /api/v1/auth/* (login, register, refresh, logout, me)
- `core/api/routes/admin_routes.py` — /api/v1/admin/* (users, sessions, API keys, audit, security config)
- `core/api/routes/tickets.py` — /api/v1/tickets/* (ticketing REST API)
- `core/api/routes/agents.py` — agents REST + SSE stream + A2A cards
- `core/api/routes/workflows.py` — workflows REST + webhook trigger endpoints
- `core/api/routes/memory.py` — memory CRUD + hybrid-search + consolidate endpoints
- `memory/engine.py` — memory facade, all agents call this
- `memory/retriever.py` — hybrid BM25+vector RRF retrieval (Phase 11.2)
- `memory/context_builder.py` — tiered context injection for agent prompts (Phase 11.3)
- `memory/consolidator.py` — episodic→semantic consolidation engine (Phase 11.1)
- `agents/executor.py` — Claude API wrapper, streaming, multi-turn, image support, eval trigger
- `agents/evaluator.py` — LLM-as-Judge async quality scoring (Phase 10.3)
- `agents/dispatcher.py` — routes requests to executor, namespace lock enforcement
- `workflows/pipeline.py` — step executor for all 7 workflows
- `workflows/scheduler.py` — APScheduler: cron workflows + consolidation + sync + reminders
- `dashboard/app.py` — Streamlit entry point, auth gate, role nav (10 pages)
- `dashboard/components/login_form.py` — branded login + self-registration form (st.form)
- `dashboard/components/brand.py` — CSS injection, theme toggle, all visual primitives
- `dashboard/_pages/_agents.py` — Chat/Catalog/Runs tabs, streaming, image, voice, eval
- `dashboard/_pages/_overview.py` — Live feed, auto-refresh, error alerts, eval score pills
- `dashboard/_pages/_observability.py` — Quality trends, latency, tokens, memory health
- `dashboard/_pages/_workflows.py` — Workflows + Webhooks tab
- `dashboard/_pages/_admin.py` — Admin Panel UI (users, API keys, audit, sessions, security)
- `mcp/server.py` — MCP Tool Server, exposes 12 agents as MCP tools (port 5100)
- `scripts/create_admin.py` — first-run admin seed script
- `scripts/start.ps1` — kills ports, starts Flask + Streamlit
- `scripts/start_mcp.ps1` — starts MCP server on port 5100

## Stack
- Python: Flask (API), Streamlit (dashboard)
- AI: anthropic SDK ≥0.40.0, claude-sonnet-4-6 (agents), claude-haiku-4-5 (eval/consolidation)
- Auth: PyJWT≥2.10.1, bcrypt==4.2.0
- Memory: SQLite FTS5, ChromaDB, sentence-transformers, rank-bm25
- Charts: plotly
- Scheduler: APScheduler BackgroundScheduler
- WSGI: waitress (not gunicorn — Windows)
- Optional: openai-whisper (voice), mcp + uvicorn (MCP server)
- Testing: pytest

## Auth & Security Rules
- All API routes require auth (`@require_auth`) — JWT Bearer or X-API-Key fallback
- `/api/v1/health` is the ONLY public endpoint (webhook trigger uses X-Webhook-Secret, not JWT)
- Roles: admin (all access) | operator (all namespaces, no user mgmt) | client (own namespace only) | viewer (own namespace, read-only) | staff (assigned tickets only)
- JWT access tokens: 60 min TTL. Refresh tokens: 7 days, stored as SHA-256 hash
- Passwords: bcrypt 12 rounds, min 10 chars, upper+lower+digit required
- Account lockout: 5 failed attempts → 15-min lock (configurable via system_config)
- `must_change_password` flag: user forced to change on next login
- Client one-per-namespace enforced in application layer
- Never expose raw refresh tokens in logs or responses beyond initial issue
- `effective_namespace()` in auth.py enforces client scoping — never trust client-supplied namespace
  - Falls back to `requested` param if `g.user_namespace` is null
- Username lookup uses `LOWER()` match — login is case-insensitive
- Webhook endpoints use `hmac.compare_digest` to validate X-Webhook-Secret — no JWT needed

## Database Tables
**Auth Layer:**
- `users` — id, username, email, password_hash, role, namespace, is_active, failed_attempts, locked_until, must_change_password
- `user_sessions` — refresh token hashes, ip, ua, expires_at, revoked
- `auth_events` — full audit log: login_success/failure, logout, token_refresh, user_created, lockout_triggered, etc.
- `system_config` — key/value security settings

**Agent Layer:**
- `agent_runs` — all run records + eval_score, eval_reasoning, eval_dimensions, eval_at (migration 014)
- `agent_conversations` — multi-turn conversation sessions (migration 017)
- `agent_conversation_turns` — individual turns with role, content, tokens (migration 017)

**Memory Layer:**
- `memory_entries` — all memory + context_prefix, is_consolidated, archived, consolidated_from (migration 015)
- `memory_fts` — FTS5 virtual table for keyword search
- `memory_vectors` — ChromaDB chroma_id mapping

**Workflow Layer:**
- `workflows` — definitions + webhook_secret, webhook_enabled (migration 016)
- `workflow_runs` — pipeline execution history

## Dashboard Rules
- `inject()` and `theme_toggle()` MUST be called BEFORE the auth gate — they render on login page
- Theme toggle: fixed bottom-left, 44px circular icon, implemented via `components.v1.html(height=0)`
- Sidebar renders AFTER auth gate — only visible to logged-in users
- Role-based nav: clients/viewers hide Settings, Workflows, Observability, Admin; staff sees Tickets only
- Auto token refresh: decode locally, if expiry < 5 min → call `/auth/refresh` silently
- 401 response → clear session_state + `st.rerun()` (returns to login)
- Login form uses `st.form` — Enter-to-submit
- Streaming: use `requests.get(..., stream=True)` + `resp.iter_lines()` for SSE consumption
- Multi-turn chat: conversation stored in `st.session_state[f"conv_{agent}_{ns}"]` list of dicts
- Observability page visible to admin + operator only (hidden from client, viewer, staff)

## Phase 10-13 Rules
- SSE streaming: `execute_stream()` in executor.py is a generator — yields text chunks. Flask wraps with `stream_with_context`. Never buffer the full response.
- Eval scoring: always async via `_bg_pool.submit(_trigger_eval, ...)` — never block agent run on eval
- Eval uses claude-haiku-4-5-20251001 (cheap+fast). Score = tc×0.40 + fg×0.30 + cc×0.20 + sf×0.10
- Tiered context: `memory/context_builder.py:build_context(namespace, query)` replaces `get_agent_context()` in executor. Falls back to flat context if context_builder fails.
- Hybrid retrieval: `memory/retriever.py:hybrid_search()` — BM25 + ChromaDB in ThreadPoolExecutor, merged via RRF (k=60). Falls back to FTS5 if rank-bm25 not installed.
- Consolidation job: every 4h via APScheduler. Archives originals (archived=1), never hard-deletes.
- Webhooks: `POST /workflows/<name>/trigger` is the only non-JWT endpoint besides /health. Secured by HMAC comparison of X-Webhook-Secret header.
- MCP server: runs independently on port 5100. Start via `scripts/start_mcp.ps1`. Optional — not required for core operation.
- Image support: executor `_build_messages()` accepts `images=[{data: base64, media_type: str}]` — injected as Claude API image content blocks.
- Voice input: requires `openai-whisper`. Uses `@st.cache_resource` to load model once per session.
- A2A cards: `GET /agents/<name>/.well-known/agent.json` — pure JSON generation, no extra deps.

## Performance Patterns
- Parallel API calls via `ThreadPoolExecutor` — all overview data fetched in one shot (5 concurrent)
- N+1 → parallel: namespace workspace + projects fetched concurrently in Client Vault
- Ticket assignees batch-fetched in a single `WHERE id IN (...)` query
- Ticket comments lazy-loaded: only fetched on "💬 Comments" toggle
- `_cached_api_get` cache key includes JWT token — prevents cross-user cache pollution
- `/agents/runs` excluded from `_READ_ONLY_PREFIXES` — always bypasses cache
- Bulk session revoke: single `UPDATE ... WHERE id IN (...)`
- `_api_key_last_updated` bounded to 500 entries with TTL eviction
- Security settings update uses `executemany`
- TTL config cache in `core/auth.py:_cfg()` — 60s in-process cache
- Hybrid retrieval: BM25 + vector run in parallel (ThreadPoolExecutor), not sequential
- Tiered context: namespace summary cached 5 min in-process — not rebuilt per request
- Eval pool: 2-worker ThreadPoolExecutor, non-blocking — never delays agent response
- Consolidation: only processes entries older than 24h, capped at 200 per namespace per run
- Memory consolidation caches BM25 corpus per namespace (rebuilt only on write)

## Theme System
- Dark/light mode: `st.session_state["theme"]` ("dark"/"light")
- `get_theme_vars()` in brand.py returns CSS vars dict
- `_build_css(t)` generates full CSS from theme vars — one call, entire app styled
- `inject()` must be called on every page render
- Theme toggle: `st.components.v1.html(height=0)` — JS uses `window.parent.document`
  - `st.html()` is sandboxed (scripts blocked); `st.markdown` strips scripts
- Aurora background removed — no animated gradients, no will-change: transform

## Rules
- Never use gunicorn — use waitress on Windows
- Always `encoding='utf-8'` on file reads/writes
- Never commit .env, vault workspace files, or data/claudeos.db
- Namespace isolation is mandatory — no cross-namespace memory reads
- Every agent run logs to agent_runs table
- Every output saves to outputs table + file system
- Port detection: read .env FLASK_PORT/STREAMLIT_PORT/MCP_PORT first
- Never use `&&` in shell — use `;` or separate calls (PowerShell)
- Eval is async — never block on it. If evaluator.py import fails, log warning and continue.
- Consolidation archives, never deletes — `archived=1` not `DELETE`
- Webhook secrets: always use `secrets.token_hex(32)`, always compare with `hmac.compare_digest`

## Server Start
```powershell
.\scripts\start.ps1                 # Flask + Streamlit (required)
.\scripts\start_mcp.ps1             # MCP server (optional, port 5100)
```

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
- Phase 1:  Core Infrastructure ✅
- Phase 2:  Memory Engine ✅
- Phase 3:  Agent Registry + Control Center ✅
- Phase 4:  Workflow Engine ✅
- Phase 5:  Client/Project Vault ✅
- Phase 6:  Output Manager ✅
- Phase 7:  Cloud Deployment (Supabase Sync) ✅
- Phase 8:  Auth, Admin Backend & Multi-User Login ✅
- Phase 9:  Ticketing System + Bulk Delete ✅
- Phase 10: Real-Time Intelligence ✅
  - SSE streaming: GET /agents/<name>/stream (execute_stream generator)
  - LLM-as-Judge: async Haiku eval after every run (migration 014)
  - Observability dashboard: quality, latency p50/p95/p99, token cost, memory health
- Phase 11: Advanced Memory & Retrieval ✅
  - Hybrid BM25+Vector RAG with RRF (memory/retriever.py, rank-bm25)
  - Tiered context injection (memory/context_builder.py, ~40% token reduction)
  - Memory consolidation engine (memory/consolidator.py, 4h APScheduler job)
  - Contextual memory prefixing (context_prefix column, migration 015)
- Phase 12: Event-Driven Workflows & Protocols ✅
  - Webhook triggers (POST /workflows/<name>/trigger, X-Webhook-Secret auth, migration 016)
  - MCP Tool Server (mcp/server.py, port 5100, 12 agents as MCP tools)
  - A2A Agent Cards (GET /agents/<name>/.well-known/agent.json)
- Phase 13: Multimodal Input & Live Dashboard ✅
  - Multi-turn chat UI (conversation history, migration 017)
  - Image/screenshot analysis (base64 content blocks via executor)
  - Voice input (st.audio_input + local Whisper, optional)
  - Live Overview (auto-refresh toggle, eval score pills, error/running alerts)
