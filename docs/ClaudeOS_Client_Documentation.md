# ClaudeOS — Client Documentation

**Version:** 8.0  
**Last Updated:** 2026-05-16  
**Brand:** #407E3C Green · White · #5a9e56 Accent

---

## What Is ClaudeOS?

ClaudeOS is an AI Operating System — a secure, multi-user coordination layer that unifies AI agents, memory, workflows, and project management into a single authenticated control center. It runs on your local machine (Windows 10) and exposes a polished dashboard at `http://localhost:8501`.

---

## Getting Access

### Admin Creates Your Account
Your admin will create your account and provide:
- **Username** and temporary **password**
- Your assigned **namespace** (e.g. `reci-transport`, `ivycandy-hair`)
- Your **role**: client or viewer

You will be prompted to change your password on first login.

### Self-Registration (if enabled)
If self-registration is enabled by the admin:
1. Open the dashboard at `http://localhost:8501`
2. Click the **Register** tab on the login screen
3. Enter username, email, password, and select your namespace
4. Log in separately after registration

**Password requirements:** minimum 10 characters, at least one uppercase letter, one lowercase letter, and one digit.

---

## Roles & Permissions

| Feature | Admin | Operator | Client | Viewer |
|---------|-------|----------|--------|--------|
| All namespaces | ✅ | ✅ | Own only | Own only |
| Memory read | ✅ | ✅ | ✅ | ✅ |
| Memory write | ✅ | ✅ | ✅ | ❌ |
| Run agents | ✅ | ✅ | ✅ | ❌ |
| View outputs | ✅ | ✅ | ✅ | ✅ |
| Manage workflows | ✅ | ✅ | ❌ | ❌ |
| Admin Panel | ✅ | ❌ | ❌ | ❌ |

---

## Dashboard Pages

### Overview
The home page shows:
- **System Status** — API and database health at a glance
- **KPI Cards** — memory entries, agents, runs, workflows, outputs
- **Recent Events** — last 8 agent run results with timestamps
- **Quick Dispatch** — run any agent against any namespace with a prompt
- **Memory by Namespace** — count of active memory entries per namespace

### Memory
Browse, search, write, and delete memory entries.
- Full-text search across keys and values
- Filter by namespace, category, and minimum confidence
- Write entries with category (fact, preference, reminder, task), TTL, and confidence score
- Reminder entries use a date/time picker for expiry
- Search via FTS5 for instant keyword matching

### Agents
- View all 12 registered agents with their descriptions and capabilities
- Run any agent directly with a custom prompt and namespace
- Live output polling — results auto-refresh every 3 seconds until done
- Full run history with status, duration, and output preview

### Workflows
- View all 7 configured pipelines
- Trigger workflows manually
- See last-run timestamps and schedules
- Monitor pipeline steps and their statuses

### Client Vault
- **Namespaces** — view your namespace details, workspace stats (files, KB), and project count
- **Projects** — list projects in your namespace, update status (active/paused/archived)
- **Context Files** — upload per-namespace context files injected into agent system prompts

### Outputs
- Browse all AI-generated outputs: reports, summaries, plans, analyses, code
- Full-text search across output content
- Filter by namespace, type, and date
- Export individual outputs as Markdown or PDF

### Settings (Admin/Operator)
- System configuration
- Supabase sync controls — trigger manual push or view sync status
- View environment and runtime info

### Admin Panel (Admin only)
- **Users** — create, deactivate, unlock, and reset passwords for all users
- **API Keys** — create and revoke API keys; raw key shown once on creation
- **Audit Log** — paginated event log: logins, failures, lockouts, user actions
- **Sessions** — view active refresh token sessions, revoke any session
- **Security** — configure lockout threshold, lockout duration, token TTLs, enable/disable self-registration

---

## Theme

A dark/light mode toggle sits in the **bottom-left corner** of every page, including the login screen. Your theme preference persists for your current session.

---

## Security Features

- **JWT-based authentication** — tokens expire after 60 minutes, auto-refreshed silently
- **Account lockout** — 5 failed login attempts triggers a 15-minute lockout (admin-configurable)
- **Audit log** — every login, logout, failure, user action, and password change is logged with IP and timestamp
- **Namespace isolation** — clients can only read and write within their assigned namespace
- **Bcrypt password hashing** — 12 rounds, never stored in plaintext
- **Forced password change** — admin can flag accounts requiring a new password on next login

---

## API Access (Developers)

The REST API runs at `http://localhost:5000/api/v1/`.

**Authenticate with JWT:**
```bash
# Login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_user","password":"your_pass"}'

# Use token
curl http://localhost:5000/api/v1/agents \
  -H "Authorization: Bearer <access_token>"
```

**Or use an API key (legacy/scripts):**
```bash
curl http://localhost:5000/api/v1/memory \
  -H "X-API-Key: your_api_key"
```

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Login, get access + refresh tokens |
| POST | `/auth/refresh` | Renew access token using refresh token |
| POST | `/auth/logout` | Revoke current session |
| GET | `/auth/me` | Current user info |
| GET | `/memory` | List memory entries |
| POST | `/memory` | Write a memory entry |
| GET | `/agents` | List all agents |
| POST | `/agents/{id}/run` | Run agent with prompt |
| GET | `/agents/runs/{id}` | Poll run status and output |
| GET | `/outputs` | List outputs |
| GET | `/workflows` | List workflows |
| POST | `/workflows/{id}/trigger` | Trigger a workflow |
| GET | `/system/status` | System health |
| GET | `/health` | Public health check (no auth) |

---

## Starting the System

```powershell
.\scripts\start.ps1
```

This kills any existing processes on :5000 and :8501, starts the Flask API via waitress, verifies `/health`, then starts the Streamlit dashboard.

**First-time setup:**
```powershell
pip install -r requirements.txt
python scripts/migrate.py
python scripts/seed_agents.py
python scripts/seed_workflows.py
python scripts/seed_namespaces.py
python scripts/create_admin.py --username admin --password Admin123!
.\scripts\start.ps1
```

---

## Cloud Sync (Supabase)

Outputs and memory can be synced to Supabase for cloud backup and sharing.

1. Create a [Supabase](https://supabase.com) project
2. Run `sync/supabase_schema.sql` in the Supabase SQL Editor
3. Add credentials to `.env`:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your_service_role_key
   ```
4. Restart the server — auto-sync fires every 15 minutes
5. Or trigger manually from the **Settings** tab

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| Can't reach dashboard | Run `.\scripts\start.ps1` — check both ports are alive |
| Login fails | Check username/password; after 5 failures wait 15 min or ask admin to unlock |
| "Must change password" shown | Enter current password + new password in the prompt |
| API returns 401 | Token expired — log out and log back in |
| Output won't export | Try Markdown export; PDF may need wkhtmltopdf installed |
| Sync fails | Verify SUPABASE_URL and SUPABASE_SERVICE_KEY in .env; restart after changes |
| Eye icon not visible | Light mode CSS — this is a known Streamlit quirk, fixed in latest build |

---

## Support

Contact your admin (Romanus Igwe) or open an issue in the project repository.

**Stack versions:** Python 3.11+ · Flask 3.0 · Streamlit 1.38 · SQLite FTS5 · claude-sonnet-4-6
