# ClaudeOS Build Skill
**File:** `SKILL.md`  
**Invoke as:** `/claudeos` (copy this file to `~/.claude/skills/claudeos.md`)  
**Purpose:** Reproduce the complete ClaudeOS AI Operating System for any new client from scratch — A to Z — with their name and brand applied throughout. Every feature, every phase, every file.

---

## How to Use This Skill

1. Copy this file to your Claude Code skills directory:
   ```powershell
   Copy-Item SKILL.md "$env:USERPROFILE\.claude\skills\claudeos.md"
   ```
2. In any new project directory, invoke with:
   ```
   /claudeos
   ```
3. Claude will ask you 3 questions, then build the entire system.

---

## Skill Instructions (what Claude does when invoked)

When this skill is invoked, execute the following steps exactly.

---

### STEP 0 — Collect Client Information

Ask the user these questions **one by one**. Wait for each answer before proceeding.

**Question 1 (required):**
> "What is the name of the client or business this system is being built for?  
> (Example: Acme Corp, Lagos Motors, BrightPath Finance)"

**Question 2 (optional — press Enter to skip):**
> "What are the brand colors?  
> Provide as hex codes: Primary, Secondary, Accent  
> (Example: #2563EB, #FFFFFF, #3B82F6)  
> Skip to use ClaudeOS defaults: #407E3C green, #FFFFFF white, #5a9e56 accent)"

**Question 3 (optional — press Enter to skip):**
> "Describe the client's business in one sentence.  
> This is injected into agent system prompts as context.  
> (Example: 'Lagos Motors is a vehicle logistics company operating across Nigeria.')"

After collecting answers, confirm:
> "Building [CLIENT_NAME] AI Operating System with [colors] brand. Proceeding..."

Then execute all steps below without further interruption.

---

### STEP 1 — Derive Variables

From the answers, derive these variables used throughout the build:

```
CLIENT_NAME       = answer to Q1  (e.g. "Acme Corp")
CLIENT_SLUG       = lowercase, hyphens  (e.g. "acme-corp")
CLIENT_NAMESPACE  = CLIENT_SLUG  (e.g. "acme-corp")
CLIENT_ADMIN_USER = first word of CLIENT_NAME, lowercase  (e.g. "acme")

BRAND_PRIMARY     = Q2 primary color OR "#407E3C"
BRAND_SECONDARY   = Q2 secondary color OR "#FFFFFF"
BRAND_ACCENT      = Q2 accent color OR "#5a9e56"
BRAND_DARK        = darken BRAND_PRIMARY by ~20%  (e.g. "#2d5a29" for green)

CLIENT_DESC       = Q3 answer OR "An AI-powered business platform."

SECRET_KEY        = generate random 48-char hex string
ADMIN_PASSWORD    = "Admin123!" + first 4 chars of CLIENT_SLUG (e.g. "Admin123!acme")
```

---

### STEP 2 — Scaffold Directory Structure

Create the following directory structure in the current working directory:

```
[CLIENT_SLUG]/
├── agents/
│   ├── definitions/          ← 12 YAML agent definitions
│   ├── __init__.py
│   ├── dispatcher.py
│   ├── evaluator.py
│   ├── executor.py
│   ├── registry.py
│   └── schemas.py
├── core/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── admin_routes.py
│   │   │   ├── agents.py
│   │   │   ├── auth_routes.py
│   │   │   ├── memory.py
│   │   │   ├── outputs.py
│   │   │   ├── projects.py
│   │   │   ├── sync.py
│   │   │   ├── system.py
│   │   │   ├── tickets.py
│   │   │   └── workflows.py
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── limiter.py
│   │   └── middleware.py
│   ├── __init__.py
│   ├── auth.py
│   ├── config.py
│   ├── database.py
│   └── utils.py
├── dashboard/
│   ├── _pages/
│   │   ├── _admin.py
│   │   ├── _agents.py
│   │   ├── _memory.py
│   │   ├── _observability.py
│   │   ├── _outputs.py
│   │   ├── _overview.py
│   │   ├── _projects.py
│   │   ├── _settings.py
│   │   ├── _tickets.py
│   │   └── _workflows.py
│   ├── components/
│   │   ├── brand.py
│   │   └── login_form.py
│   ├── __init__.py
│   └── app.py
├── data/                     ← created at runtime, not committed
├── logs/                     ← created at runtime
├── mcp/
│   ├── __init__.py
│   └── server.py
├── memory/
│   ├── db/
│   │   └── migrations/
│   │       ├── 001_initial.sql … 017_agent_conversations.sql
│   ├── __init__.py
│   ├── consolidator.py
│   ├── context_builder.py
│   ├── engine.py
│   ├── retriever.py
│   ├── schemas.py
│   ├── store.py
│   └── vector_store.py
├── notifications/
│   ├── __init__.py
│   └── reminder_job.py
├── outputs/
│   ├── store/
│   ├── __init__.py
│   └── manager.py
├── scripts/
│   ├── create_admin.py
│   ├── migrate.py
│   ├── seed_agents.py
│   ├── seed_namespaces.py
│   ├── seed_workflows.py
│   ├── serve_api.py
│   ├── start.ps1
│   └── start_mcp.ps1
├── sync/
│   ├── __init__.py
│   ├── engine.py
│   ├── schemas.py
│   └── supabase_schema.sql
├── tests/
│   ├── test_agents.py
│   ├── test_memory.py
│   └── test_phase1.py
├── vault/
│   ├── __init__.py
│   └── manager.py
├── workflows/
│   ├── definitions/          ← 7 YAML workflow definitions
│   ├── __init__.py
│   ├── pipeline.py
│   ├── registry.py
│   ├── scheduler.py
│   └── schemas.py
├── .env
├── .env.example
├── .gitignore
├── CLAUDE.md
├── README.md
├── requirements.txt
└── SKILL.md                  ← copy of this file
```

**Implementation:** Copy all source files from the ClaudeOS reference implementation at `C:\Users\rigwe\Desktop\ClaudeOS\`. After copying, apply brand substitution in Step 3.

If the reference implementation is not available (building on a new machine), implement each file from scratch using the specifications in this document.

---

### STEP 3 — Apply Brand Throughout

After scaffolding, perform these exact substitutions. Use find-and-replace across all files.

#### In `dashboard/components/brand.py`:

Replace:
```python
PRIMARY       = "#407E3C"
ACCENT        = "#5a9e56"
PRIMARY_LIGHT = "#5a9e56"
PRIMARY_LT    = "#5a9e56"
PRIMARY_DK    = "#2d5a29"
WHITE         = "#FFFFFF"
```
With:
```python
PRIMARY       = "BRAND_PRIMARY"
ACCENT        = "BRAND_ACCENT"
PRIMARY_LIGHT = "BRAND_ACCENT"
PRIMARY_LT    = "BRAND_ACCENT"
PRIMARY_DK    = "BRAND_DARK"
WHITE         = "BRAND_SECONDARY"
```

Replace all 3 occurrences of `"#407E3C"` in the THEMES dict with `BRAND_PRIMARY`.
Replace all occurrences of `"#5a9e56"` in the THEMES dict with `BRAND_ACCENT`.
Replace `"#2d5a29"` with `BRAND_DARK`.

#### In `dashboard/app.py`:

Replace the page title and icon:
```python
page_title="ClaudeOS",
page_icon="🖥️",
```
With:
```python
page_title="CLIENT_NAME OS",
page_icon="🤖",
```

#### In `dashboard/_pages/_overview.py`:

Replace in `aurora_hero()` call:
```python
title="ClaudeOS",
subtitle="AI Operating System — coordination layer for all agents, memory, and workflows.",
```
With:
```python
title="CLIENT_NAME",
subtitle="CLIENT_DESC",
```

#### In `CLAUDE.md`:

Replace:
```
ClaudeOS — AI Operating System
Brand: #407E3C green + white
```
With:
```
CLIENT_NAME OS — AI Operating System
Brand: BRAND_PRIMARY · BRAND_SECONDARY · BRAND_ACCENT
```

#### In `README.md`:

Replace all occurrences of `ClaudeOS` in headings and descriptions with `CLIENT_NAME OS`.
Replace badge color `407E3C` with the hex of BRAND_PRIMARY (without `#`).

#### In all agent YAML definitions (`agents/definitions/*.yaml`):

In each agent's `system_prompt` field, prepend:
```
You are an AI agent operating within the CLIENT_NAME AI Operating System.
Business context: CLIENT_DESC
```

---

### STEP 4 — Configure .env

Create `.env` with:

```env
# CLIENT_NAME OS — Environment Configuration
# Generated by ClaudeOS Build Skill

ANTHROPIC_API_KEY=REPLACE_WITH_YOUR_KEY
CLAUDEOS_SECRET_KEY=SECRET_KEY
CLAUDEOS_ENV=development
CLAUDEOS_VERSION=1.0.0

SQLITE_PATH=data/claudeos.db
CHROMADB_PATH=data/chromadb

FLASK_PORT=5000
FLASK_DEBUG=false

STREAMLIT_PORT=8501

# Cloud Sync (optional — fill in to activate)
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

# MCP Server (optional)
MCP_PORT=5100

# Email notifications (optional)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
NOTIFY_EMAIL=

LOG_LEVEL=INFO
LOG_PATH=logs
```

Also create `.env.example` — same content but with all secrets as placeholder strings.

---

### STEP 5 — Configure .gitignore

Create `.gitignore`:

```gitignore
# Environment
.env
*.env

# Database & vector store
data/
*.db
*.db-journal

# Vault workspace files
vault/workspaces/

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/

# Logs
logs/
*.log

# Output files
outputs/store/

# Test artifacts
.pytest_cache/
htmlcov/
.coverage

# OS
.DS_Store
Thumbs.db
```

---

### STEP 6 — Create requirements.txt

```
# CLIENT_NAME OS Requirements

# Core
flask==3.0.3
flask-cors==4.0.1
flask-limiter==3.7.0

# AI
anthropic>=0.40.0

# Dashboard
streamlit==1.38.0

# Memory / Vector
chromadb==0.5.5
sentence-transformers==3.1.1

# Hybrid RAG
rank-bm25==0.2.2

# Scheduler
apscheduler==3.10.4

# Data / Validation
pydantic==2.8.2
pydantic-settings==2.4.0
python-dotenv==1.0.1

# WSGI (Windows-compatible)
waitress==3.0.0

# Cloud sync (optional)
supabase==2.7.4

# Output export
markdown2==2.5.0
pdfkit==1.0.0

# Auth
PyJWT>=2.10.1,<3.0.0
bcrypt==4.2.0

# Charts
plotly>=5.18.0

# Optional: voice input
# openai-whisper>=20231117

# Optional: MCP tool server
# mcp>=1.0.0
# uvicorn>=0.30.0

# Dev / testing
pytest==8.3.3
pytest-cov==5.0.0
httpx==0.27.2
```

---

### STEP 7 — Seed Agent YAML Definitions

Create these 12 agent YAML files in `agents/definitions/`. All have `CLIENT_NAME` and `CLIENT_DESC` already injected into system prompts (from Step 3). These are the same agents as the reference ClaudeOS implementation:

1. `meta-agent.yaml` — Orchestrator. Decomposes complex goals into agent chains.
2. `research-agent.yaml` — Deep research with synthesis and source validation.
3. `briefing-agent.yaml` — Daily briefings and market intelligence.
4. `analysis-agent.yaml` — Data analysis and metrics interpretation.
5. `writing-agent.yaml` — Content creation, editing, and refinement.
6. `comms-agent.yaml` — Internal communications and notifications.
7. `memory-curator-agent.yaml` — Memory management and context curation.
8. `client-manager-agent.yaml` — Client-specific data and context.
9. `qa-agent.yaml` — Quality assurance and content review.
10. `scheduling-agent.yaml` — Calendar and task scheduling coordination.
11. `workflow-builder-agent.yaml` — Generate new workflows from natural language.
12. `domain-agent.yaml` — Domain-specific operations (replaces transport-ops-agent; namespace unlocked for new client use).

**YAML structure** (use this template for each agent):
```yaml
name: [agent-name]
display_name: [Display Name]
description: [One-line description]
category: [ops|research|content|analysis|comms|system|engineering|domain]
system_prompt: |
  You are an AI agent operating within the CLIENT_NAME AI Operating System.
  Business context: CLIENT_DESC

  [Agent-specific instructions here]
model: claude-sonnet-4-6
max_tokens: 4096
temperature: 0.7
tools: []
namespace_lock: null
tags: [tag1, tag2]
enabled: true
version: "1.0.0"
```

---

### STEP 8 — Seed Workflow YAML Definitions

Create these 7 workflow YAML files in `workflows/definitions/`:

1. `01-morning-briefing.yaml` — Daily morning briefing (Mon–Fri 7:00 WAT)
2. `02-memory-curation.yaml` — Weekly memory cleanup (Sunday midnight)
3. `03-research-digest.yaml` — Weekly research summary
4. `04-client-report.yaml` — Weekly client reports (Friday 17:00 WAT)
5. `05-analysis-run.yaml` — Scheduled analytics
6. `06-qa-sweep.yaml` — Quality checks (Mon–Fri 6:00 WAT)
7. `07-meta-orchestrate.yaml` — Manual meta-orchestration (3 steps: plan → research → summary)

Update namespace in all workflow definitions from `global` to `CLIENT_NAMESPACE` where appropriate.

---

### STEP 9 — Install Dependencies & Run Migrations

```powershell
Set-Location CLIENT_SLUG
pip install -r requirements.txt
python scripts/migrate.py
python scripts/seed_agents.py
python scripts/seed_workflows.py
python scripts/seed_namespaces.py
```

For `seed_namespaces.py`, create the `CLIENT_NAMESPACE` namespace in addition to the standard `global` namespace. The client namespace should be the primary workspace.

---

### STEP 10 — Create Admin User

```powershell
python scripts/create_admin.py --username CLIENT_ADMIN_USER --password ADMIN_PASSWORD
```

Print the credentials clearly so the user can record them:
```
====================================
  CLIENT_NAME OS — Admin Credentials
====================================
  Dashboard: http://localhost:8501
  API:       http://localhost:5000/api/v1/health
  Username:  CLIENT_ADMIN_USER
  Password:  ADMIN_PASSWORD
  
  IMPORTANT: Change this password after first login.
  The admin will be prompted automatically on next login.
====================================
```

---

### STEP 11 — Start the System

```powershell
.\scripts\start.ps1
```

Verify both services are responding:
```powershell
# Check Flask
Invoke-RestMethod http://localhost:5000/api/v1/health

# Check Streamlit
Invoke-WebRequest http://localhost:8501/healthz -UseBasicParsing
```

If both respond, print:
```
====================================
  CLIENT_NAME OS is LIVE
====================================
  Dashboard:  http://localhost:8501
  API:        http://localhost:5000/api/v1/health
  
  Login with the admin credentials above.
  
  OPTIONAL next steps:
  - Add ANTHROPIC_API_KEY to .env and restart
  - Run .\scripts\start_mcp.ps1 for MCP tool server
  - Add Supabase credentials to .env for cloud sync
  - pip install openai-whisper for voice input
====================================
```

---

### STEP 12 — Generate Client CLAUDE.md

Create a `CLAUDE.md` in the project root with the full ClaudeOS project rules (as in the reference implementation), but with all instances of `ClaudeOS` replaced by `CLIENT_NAME OS`, and the brand colors updated to match the client's brand.

---

### STEP 13 — Commit Initial State

```powershell
git init
git add .
git commit -m "init: CLIENT_NAME OS — ClaudeOS v13.0 base build"
```

---

## What Gets Built (Complete Feature List)

Every deployment built by this skill includes all of the following. Nothing is cut down or simplified.

### Layers 0-9 (Core System)
| Layer | Feature |
|-------|---------|
| 0 | Streamlit dashboard — 10 pages, branded, dark/light theme |
| 1 | Flask REST API — 40+ endpoints, JWT + API key auth |
| 2 | Memory Engine — SQLite FTS5 + ChromaDB vector store |
| 3 | Agent Registry — 12 agents, YAML definitions, enable/disable |
| 4 | Workflow Engine — 7 pipelines, APScheduler, cron + manual |
| 5 | Client Vault — namespace isolation, per-client workspaces |
| 6 | Output Manager — auto-tag, full-text search, Markdown/PDF export |
| 7 | Supabase Cloud Sync — push-only, watermark, 15-min auto |
| 8 | Auth & Security — JWT/bcrypt, 5 roles, lockout, audit log |
| 9 | Ticketing System — SLA tiers P1–P4, staff role, bulk ops |

### Layers 10-13 (Intelligence Layer)
| Layer | Feature |
|-------|---------|
| 10 | Real-Time Intelligence: SSE streaming, LLM-as-Judge eval, Observability dashboard |
| 11 | Advanced Memory: hybrid BM25+vector RAG, tiered context, consolidation engine |
| 12 | Protocols: MCP Tool Server, A2A Agent Cards, webhook triggers |
| 13 | Multimodal: multi-turn chat, image analysis, voice input, live dashboard |

### Authentication & Roles
| Role | Access |
|------|--------|
| admin | Full access — all namespaces, user management, admin panel |
| operator | All namespaces, all resources, no user management |
| client | Own namespace only — memory R/W, run agents, view outputs |
| viewer | Own namespace, read-only |
| staff | Assigned tickets only — can self-assign and advance status |

### Dashboard Pages
- Overview — live activity feed, KPIs, quick dispatch, eval score pills
- Agents — 3-tab UI: Chat (streaming, images, voice), Catalog, Run History
- Memory — FTS search, semantic search, write/edit/delete, bulk ops
- Workflows — manage, trigger, schedule, webhook setup
- Projects — client vault, namespaces, project management
- Outputs — search, view, export, bulk delete
- Tickets — create, assign, comment, SLA tracking
- Observability — quality scores, latency, token cost, memory health
- Settings — env config, sync controls
- Admin Panel — users, API keys, audit log, sessions, security config

### API Endpoints (Key)
| Endpoint | Description |
|----------|-------------|
| `POST /auth/login` | JWT login |
| `GET /agents` | List agents |
| `POST /agents/<name>/run` | Run agent |
| `GET /agents/<name>/stream` | SSE streaming response |
| `GET /agents/<name>/.well-known/agent.json` | A2A Agent Card |
| `GET /memory` | List memory |
| `POST /memory` | Write memory |
| `GET /memory/hybrid-search` | Hybrid BM25+vector search |
| `POST /memory/consolidate` | Trigger consolidation |
| `GET /workflows` | List workflows |
| `POST /workflows/<name>/run` | Run workflow |
| `POST /workflows/<name>/trigger` | Webhook trigger |
| `POST /workflows/<name>/webhook/enable` | Enable webhook |
| `GET /tickets` | List tickets |
| `POST /tickets` | Create ticket |
| `GET /system/status` | System health |
| `GET /health` | Public health check |

### Migrations (017 total)
| Migration | Content |
|-----------|---------|
| 001 | Initial schema (memory, agents, workflows, outputs) |
| 002 | Sync state |
| 003–005 | Performance indexes |
| 006 | Auth users, sessions, events |
| 007 | must_change_password flag |
| 008 | More performance indexes |
| 009 | Ticketing tables |
| 010–012 | More performance indexes |
| 013 | Dashboard sessions |
| 014 | Agent eval scores (eval_score, eval_dimensions, eval_at) |
| 015 | Memory upgrades (context_prefix, is_consolidated, archived) |
| 016 | Webhook triggers on workflows |
| 017 | Agent conversations + turns (multi-turn chat) |

---

## What Is NOT Included (Client Must Provide)

| Item | Notes |
|------|-------|
| `ANTHROPIC_API_KEY` | Required to run agents — client provides from console.anthropic.com |
| Brand colors | Asked in Step 0 — defaults to ClaudeOS green if skipped |
| Client business description | Asked in Step 0 — used in agent prompts |
| Supabase credentials | Optional — for cloud sync only |
| Custom agent YAML content | 12 default agents provided; client can customize system prompts |
| Custom workflow YAML content | 7 default workflows provided; client can add more |
| SMTP credentials | Optional — for email notifications |
| Domain/SSL | Optional — for production deployment beyond localhost |

---

## Optional Extras (Ask After Build)

After the system is running, offer these optional additions:

1. **Custom agents** — "Would you like me to create agents specific to [CLIENT_NAME]'s business?"
2. **Custom workflows** — "Would you like scheduled workflows tailored to your operations?"
3. **Seed initial memory** — "Shall I pre-populate memory with facts about [CLIENT_NAME]?"
4. **MCP server** — "Would you like the MCP Tool Server started? (lets Claude Desktop call your agents)"
5. **Supabase cloud sync** — "Do you have Supabase credentials for cloud backup?"

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `CLAUDEOS_SECRET_KEY` error on startup | Check .env — key must be ≥32 chars and not a placeholder |
| Migrations fail | Run `python scripts/migrate.py` manually; check data/ directory exists |
| Agents not found | Run `python scripts/seed_agents.py` |
| ChromaDB warmup slow (30-60s) | Normal on first start — sentence-transformers model loading |
| Eval scores not appearing | Async — wait ~10s; check ANTHROPIC_API_KEY in .env |
| Streaming not working | Ensure Flask is running; check CORS; verify JWT token valid |
| Voice input error | `pip install openai-whisper`; first use downloads ~140MB model |
| MCP server not found | `pip install mcp uvicorn`; run `.\scripts\start_mcp.ps1` |

---

## Reference Implementation

The canonical ClaudeOS implementation lives at:
```
C:\Users\rigwe\Desktop\ClaudeOS\
```

When building for a new client, copy all source files from this reference, then apply brand substitution as described in Step 3. Do not rebuild from scratch unless the reference is unavailable — copying ensures 100% feature parity.

**To install this skill globally:**
```powershell
Copy-Item "C:\Users\rigwe\Desktop\ClaudeOS\SKILL.md" "$env:USERPROFILE\.claude\skills\claudeos.md"
```

Then invoke in any new directory with `/claudeos`.
