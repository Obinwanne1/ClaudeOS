# ClaudeOS

AI Operating System — coordination layer unifying Claude Code skills, agents, and workflows into a single control center.

## Architecture

| Layer | Component | Tech |
|-------|-----------|------|
| 0 | Streamlit Dashboard | Streamlit :8501 |
| 1 | REST API | Flask + waitress :5000 |
| 2 | Memory Engine | SQLite FTS5 + ChromaDB |
| 3 | Agent Registry | 12 agents, YAML definitions |
| 4 | Workflow Engine | APScheduler, 7 pipelines |
| 5 | Client Vault | Namespace isolation |
| 6 | Output Manager | Auto-tag, FTS, export |
| 7 | Cloud Sync | Supabase push sync |

## Setup

### Requirements
- Python 3.11+
- Windows 10 / PowerShell

### Install
```powershell
git clone https://github.com/Obinwanne1/ClaudeOS.git
cd ClaudeOS
pip install -r requirements.txt
```

### Configure
```powershell
copy .env.example .env
```

Edit `.env`:
```env
ANTHROPIC_API_KEY=your_key_here
CLAUDEOS_SECRET_KEY=change_this

# Optional: Supabase cloud sync
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
```

### Run migrations
```powershell
python scripts/migrate.py
python scripts/seed_agents.py
python scripts/seed_workflows.py
python scripts/seed_namespaces.py
```

### Start
```powershell
.\scripts\start.ps1
```

Opens:
- Dashboard → http://localhost:8501
- API → http://localhost:5000/api/v1/health

## Cloud Sync (Supabase)

1. Create a Supabase project
2. Run `sync/supabase_schema.sql` in the SQL Editor
3. Add `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` to `.env`
4. Restart — auto-sync runs every 15 minutes

Manual sync via dashboard **Settings** tab or:
```bash
curl -X POST http://localhost:5000/api/v1/sync/push
```

## API Endpoints

```
GET  /api/v1/health
GET  /api/v1/memory
POST /api/v1/memory
GET  /api/v1/agents
POST /api/v1/agents/{id}/run
GET  /api/v1/workflows
POST /api/v1/workflows/{id}/trigger
GET  /api/v1/outputs
GET  /api/v1/sync/status
POST /api/v1/sync/push
```

## Stack

- **Backend**: Flask, waitress (Windows-compatible WSGI)
- **Dashboard**: Streamlit
- **AI**: Anthropic SDK, claude-sonnet-4-6
- **Memory**: SQLite FTS5, ChromaDB, sentence-transformers
- **Scheduler**: APScheduler
- **Cloud**: Supabase
- **Testing**: pytest

## Brand

Primary `#407E3C` · Secondary `#FFFFFF` · Accent `#5a9e56`
