# CLAUDE.md — ClaudeOS Project Rules

## Project
ClaudeOS — AI Operating System. Coordination layer unifying all Claude Code skills, agents, and workflows.
Brand: #407E3C green + white. Target: Windows 10 / PowerShell.

## Architecture
- Layer 0: Streamlit dashboard (:8501)
- Layer 1: Flask REST API (:5000)
- Layer 2: Memory Engine (SQLite FTS5 + ChromaDB)
- Layer 3: Agent Registry (12 agents, YAML definitions)
- Layer 4: Workflow Engine (APScheduler, 7 pipelines)
- Layer 5: Client Vault (namespace isolation)
- Layer 6: Output Manager (auto-tag, FTS, export)
- Layer 7: Supabase Cloud Sync (Phase 7)

## Critical Files
- `core/api/app.py` — Flask factory, all routes bootstrap here
- `memory/engine.py` — memory facade, all agents call this
- `agents/executor.py` — Claude API wrapper, injects namespace context
- `workflows/pipeline.py` — step executor for all 7 workflows
- `dashboard/app.py` — Streamlit entry point

## Stack
- Python: Flask (API), Streamlit (dashboard)
- AI: anthropic SDK, claude-sonnet-4-6
- Memory: SQLite FTS5, ChromaDB, sentence-transformers
- Scheduler: APScheduler BackgroundScheduler
- WSGI: waitress (not gunicorn — Windows)
- Testing: pytest

## Rules
- Never use gunicorn — use waitress on Windows
- Always encoding='utf-8' on file reads/writes
- Never commit .env, vault workspace files, or data/claudeos.db
- Namespace isolation is mandatory — no cross-namespace memory reads
- Every agent run logs to agent_runs table
- Every output saves to outputs table + file system
- Port detection: read .env FLASK_PORT/STREAMLIT_PORT first

## Server Start
```powershell
.\scripts\start.ps1
```
Kills :5000 and :8501 first, starts Flask via waitress, verifies /health, then starts Streamlit.

## Phase Status — ALL COMPLETE
- Phase 1: Core Infrastructure ✅
- Phase 2: Memory Engine ✅
- Phase 3: Agent Registry + Control Center ✅
- Phase 4: Workflow Engine ✅
- Phase 5: Client/Project Vault ✅
- Phase 6: Output Manager ✅
- Phase 7: Cloud Deployment (Supabase Sync) ✅
