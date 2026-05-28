"""
Generate ClaudeOS_Handbook_faiyke-ai.pdf  (v14.0)
Full client-facing handbook for faiyke-ai.
Usage: python scripts/gen_handbook_pdf.py
"""
import io
from datetime import date
from pathlib import Path
from xhtml2pdf import pisa

VERSION = "17.0"
CLIENT  = "faiyke-ai"
TODAY   = date.today().isoformat()

# ── Placeholder values the client fills manually ──────────────────────────────
ADMIN_NAME  = "[ADMIN NAME]"
ADMIN_EMAIL = "[ADMIN EMAIL]"
ADMIN_PHONE = "[ADMIN PHONE]"
SYSTEM_URL  = "[http://YOUR-SERVER-IP:8501]"
API_URL     = "[http://YOUR-SERVER-IP:5000]"
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
@page {
  size: A4;
  margin: 1.4cm 1.8cm 1.8cm 1.8cm;
  @frame footer_frame {
    -pdf-frame-content: footer_content;
    bottom: 0.5cm; left: 1.8cm; right: 1.8cm; height: 0.7cm;
  }
}

body {
  font-family: Arial, sans-serif;
  font-size: 10pt;
  color: #1a1a1a;
  line-height: 1.45;
}

p { margin: 4px 0 7px 0; }

/* ── headings ── */
h1 {
  color: #407E3C;
  font-size: 18pt;
  border-bottom: 3px solid #407E3C;
  padding-bottom: 6px;
  margin-top: 0;
  page-break-before: always;
  page-break-after: avoid;
  -pdf-keep-with-next: true;
}
h1.no-break { page-break-before: avoid; margin-top: 0; }
h2 {
  color: #2d5a29;
  font-size: 12pt;
  border-bottom: 1px solid #c8e0c0;
  padding-bottom: 3px;
  margin-top: 18px;
  margin-bottom: 5px;
  page-break-after: avoid;
  -pdf-keep-with-next: true;
}
h3 {
  color: #2d5a29;
  font-size: 10.5pt;
  margin-top: 12px;
  margin-bottom: 3px;
  page-break-after: avoid;
  -pdf-keep-with-next: true;
}
h4 {
  color: #2d5a29;
  font-size: 10pt;
  margin-top: 8px;
  margin-bottom: 2px;
  page-break-after: avoid;
  -pdf-keep-with-next: true;
}

/* ── tables ── */
table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 9pt; table-layout: fixed; }
th   { background: #407E3C; color: #fff; padding: 5px 9px; text-align: left; word-wrap: break-word; }
td   { padding: 5px 9px; border-bottom: 1px solid #d0e8c8; vertical-align: top; word-wrap: break-word; }
tr:nth-child(even) td { background: #f4faf2; }

/* ── code ── */
code {
  background: #f0f4f0;
  color: #2d5a29;
  padding: 0 4px;
  font-family: "Courier New", monospace;
  font-size: 8.5pt;
  word-break: break-all;
}
pre {
  background: #1e2a1e;
  color: #c8e8c8;
  border-left: 4px solid #407E3C;
  padding: 8px 12px;
  font-family: "Courier New", monospace;
  font-size: 7.5pt;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 8px 0;
  page-break-inside: avoid;
}

/* ── lists ── */
ul, ol { margin: 4px 0; padding-left: 20px; }
li     { margin: 2px 0; }

/* ── misc ── */
hr     { border: none; border-top: 1px solid #d0e8c8; margin: 14px 0; }
strong { color: #2d5a29; }

/* ── callout boxes ── */
.note  { background: #e8f5e4; border-left: 4px solid #407E3C; padding: 8px 12px; margin: 8px 0; font-size: 9.5pt; page-break-inside: avoid; }
.warn  { background: #fff8e0; border-left: 4px solid #f9a825; padding: 8px 12px; margin: 8px 0; font-size: 9.5pt; page-break-inside: avoid; }
.tip   { background: #e8f4e8; border-left: 4px solid #5a9e56; padding: 8px 12px; margin: 8px 0; font-size: 9.5pt; page-break-inside: avoid; }

/* ── cover ── */
.cover {
  background: #1a3a18;
  width: 100%;
  min-height: 100%;
  padding: 90px 70px 70px 70px;
  color: white;
}
.cover-logo   { font-size: 42pt; font-weight: bold; color: #ffffff; letter-spacing: 2px; margin-bottom: 4px; }
.cover-tagline { font-size: 14pt; color: #a8d4a0; margin-bottom: 6px; }
.cover-divider { border-top: 2px solid #407E3C; margin: 24px 0 20px 0; }
.cover-client { font-size: 12pt; color: #ffffff; margin-bottom: 4px; }
.cover-version { font-size: 11pt; color: #c8e0c0; margin-bottom: 60px; }
.cover-geo-bar { background: #407E3C; height: 6px; margin: 30px 0; }
.cover-footer  { font-size: 9pt; color: #6a9e66; margin-top: 40px; }
.cover-new-badge { background: #5a9e56; color: white; padding: 3px 10px; font-size: 9pt; margin-bottom: 12px; display: inline-block; }

/* ── pill ── */
.pill-green { background:#2e7d32; color:white; padding:1px 7px; font-size:8pt; }
.pill-amber { background:#f57f17; color:white; padding:1px 7px; font-size:8pt; }
.pill-red   { background:#c62828; color:white; padding:1px 7px; font-size:8pt; }
.pill-gray  { background:#757575; color:white; padding:1px 7px; font-size:8pt; }

/* ── badge ── */
.badge      { background: #407E3C; color: white; padding: 2px 8px; font-size: 8pt; margin-right: 4px; }
.badge-new  { background: #5a9e56; color: white; padding: 2px 8px; font-size: 8pt; margin-right: 4px; }
.badge-gray { background: #888;    color: white; padding: 2px 8px; font-size: 8pt; margin-right: 4px; }

/* ── gauge block ── */
.gauge-block { background: #f4faf2; border: 1px solid #c8e0c0; padding: 10px 14px; margin: 8px 0; font-size: 9pt; page-break-inside: avoid; }

/* ── page footer ── */
#footer_content { text-align: center; font-size: 8pt; color: #888; font-family: Arial, sans-serif; }
"""


# ═══════════════════════════════════════════════════════════════════════════════
# COVER PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def cover_page() -> str:
    return f"""
<div class="cover">
  <div class="cover-logo">ClaudeOS</div>
  <div class="cover-tagline">AI Operating System — Client Handbook</div>
  <div class="cover-geo-bar"></div>
  <div class="cover-new-badge">Version {VERSION} — Commercial Release</div>
  <div class="cover-client"><strong>Prepared for:</strong> {CLIENT}</div>
  <div class="cover-version"><strong>Date:</strong> {TODAY} &nbsp;|&nbsp; <strong>Edition:</strong> v{VERSION} Commercial</div>
  <div class="cover-divider"></div>
  <div class="cover-footer">
    Confidential &mdash; For authorised users of ClaudeOS only.<br/>
    Do not distribute outside your organisation.<br/>
    Powered by faiyke-ai &nbsp;&middot;&nbsp; ClaudeOS &copy; 2026
  </div>
</div>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE OF CONTENTS
# ═══════════════════════════════════════════════════════════════════════════════

def toc() -> str:
    entries = [
        ("1",  "s1",  "Introduction",                         "What ClaudeOS Is and What It Does"),
        ("2",  "s2",  "System Requirements",                  "Hardware, Software, and Network"),
        ("3",  "s3",  "Installation &amp; First-Run Setup",   "From Zero to Running in 15 Minutes"),
        ("4",  "s4",  "Logging In &amp; First-Time Experience","Auth, Roles, Onboarding Modal"),
        ("5",  "s5",  "Dashboard Tour",                       "Every Page Explained incl. Usage &amp; Bg Colour"),
        ("6",  "s6",  "Working with AI Agents",               "Chat, Catalog, Run History"),
        ("7",  "s7",  "Memory System",                        "How ClaudeOS Remembers Things"),
        ("8",  "s8",  "Workflows &amp; Automation",           "Pipelines, Scheduling, Webhooks"),
        ("9",  "s9",  "Client Vault",                         "Namespaces, Projects, Context Files"),
        ("10", "s10", "Outputs &amp; Reports",                "Saving, Searching, Exporting"),
        ("11", "s11", "Ticketing System",                     "Tickets + Email Notifications"),
        ("12", "s12", "Quality Scoring",                      "LLM-as-Judge Automatic Evaluation"),
        ("13", "s13", "Observability",                        "Quality, Latency, Token Cost, Memory Health, Namespace Usage (NEW)"),
        ("14", "s14", "Namespace Branding &amp; Customisation","Per-Namespace Brand Config (NEW)"),
        ("15", "s15", "Custom Background Colors",             "Per-User Page Background (NEW)"),
        ("16", "s16", "Advanced Features",                    "Images, Voice, MCP, A2A, Pulse Score"),
        ("17", "s17", "API Reference",                        "REST API for Developers"),
        ("18", "s18", "Security Model",                       "Auth, CORS, Rate Limits, Isolation"),
        ("19", "s19", "Cloud Sync",                           "Supabase Backup"),
        ("20", "s20", "Troubleshooting &amp; Support",        "Common Problems, Fixes, and Contacts"),
    ]
    rows = "".join(
        f"<tr>"
        f"<td style='width:6%;color:#407E3C;font-weight:bold;'>{n}</td>"
        f"<td style='width:34%;'><a href='#{anchor}' style='color:#407E3C;text-decoration:none;'>"
        f"<strong>{title}</strong></a></td>"
        f"<td style='color:#555;'>{desc}</td>"
        f"</tr>"
        for n, anchor, title, desc in entries
    )
    return f"""
<h1 class="no-break">Contents</h1>
<table>
<tr><th style="width:6%;">#</th><th style="width:34%;">Section</th><th>What You Will Find</th></tr>
{rows}
</table>
<p style="margin-top:10px;font-size:9pt;color:#555;">
  <strong>New in v14.0:</strong> Namespace White-Labeling (Sec 14), Custom Background Colors (Sec 15),
  Client Usage Dashboard with Pulse Score (Sec 5 &amp; 16), Email Notifications for Tickets (Sec 11),
  Onboarding Modal (Sec 4), CORS &amp; Rate Limiting (Sec 18), namespace-scoped KPIs, page URL persistence.<br/>
  <strong>New in v15.0:</strong> Namespace Usage tab in Observability (Sec 13), Client Onboarding tab in Admin Panel
  (14-field schema seed), onboarding_done DB persistence (migration 018), admin context-aware unlock UI,
  voice widget reset on Clear Conversation, agent failure logging to global memory.<br/>
  <strong>New in v16.0:</strong> Agent hallucination guard — agents ask clarifying questions instead of fabricating results;
  output delete SQLite compatibility fix; timestamps shown as YYYY-MM-DD HH:MM in all output views;
  activity feed now shows human-readable agent names (no more UUIDs); context builder 4s timeout for
  faster responses when ChromaDB is slow; agents page 30s namespace cache for reduced load latency.<br/>
  <strong>New in v17.0:</strong> Agent NO TRAINING KNOWLEDGE rule — analysis-agent and client-manager-agent
  explicitly blocked from using training data for business-specific facts (cities, clients, revenue, routes);
  empty context triggers MISSING INPUT PROTOCOL instead of a fabricated answer; client-manager out-of-scope
  requests (email drafts, analysis) return a one-line redirect only. Evaluator rubric fix — correct scope
  refusals now score task_completion=5.0 (agents enforcing their own boundaries are never penalised);
  factual_grounding=5.0 when no factual claims are made. Test suite expanded to 115 tests — legacy test
  files (test_agents, test_memory, test_phase1) updated with auth fixtures and APScheduler mock.
</p>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — INTRODUCTION
# ═══════════════════════════════════════════════════════════════════════════════

def s1_intro() -> str:
    return f"""
<h1><a name="s1"></a>1 &mdash; Introduction</h1>

<h2>What Is ClaudeOS?</h2>
<p>ClaudeOS is an AI Operating System &mdash; a secure, multi-user coordination layer that brings
together AI agents, a long-term memory engine, automated workflows, project management, and
a full ticketing system into one authenticated control centre. It runs as a private web
application on your own infrastructure, so your data never leaves your environment.</p>

<p>Think of it as a team of 12 specialist AI assistants, all sharing the same memory, working
from the same context, and all governed by the same security and quality rules &mdash; accessible
from any browser. Version 14.0 adds per-namespace white-labeling, custom background colours,
a dedicated client usage dashboard with a Pulse Score, and email notifications for tickets.</p>

<h2>Core Capabilities</h2>
<table>
<tr><th style="width:28%;">Capability</th><th>What It Does for You</th></tr>
<tr><td><strong>AI Agents</strong></td>
    <td>12 specialist agents covering research, writing, analysis, scheduling, QA, client
    management, comms, and more. Run via chat, one-shot dispatch, or automated pipeline.</td></tr>
<tr><td><strong>Long-Term Memory</strong></td>
    <td>Every fact, preference, reminder, and task you store is available to every agent.
    Memory persists between sessions and is scoped per namespace.</td></tr>
<tr><td><strong>Workflow Automation</strong></td>
    <td>7 built-in pipelines (morning briefing, memory curation, research digest, client
    report, analysis run, QA sweep, meta-orchestration) on a schedule or on demand.</td></tr>
<tr><td><strong>Ticketing</strong></td>
    <td>Full support and task lifecycle with email notifications &mdash; create, assign,
    prioritise, comment, resolve, and bulk-manage tickets without leaving ClaudeOS.</td></tr>
<tr><td><strong>Quality Scoring</strong></td>
    <td>Every agent response is automatically scored on 4 dimensions by a fast AI judge.</td></tr>
<tr><td><strong>Observability</strong></td>
    <td>Real-time dashboards for response quality, latency, token spend, and memory health.</td></tr>
<tr><td><strong>Namespace Branding</strong></td>
    <td>Per-namespace company name, colours, icon, and background. Clients see their own brand.</td></tr>
<tr><td><strong>Client Usage Dashboard</strong></td>
    <td>KPIs, Namespace Pulse Score, AI activity feed, and memory summary for client/viewer roles.</td></tr>
</table>

<h2>Architecture at a Glance</h2>
<pre>Browser  ──►  Streamlit Dashboard  (:8501)
                      │
              Login Gate (JWT) + Onboarding Modal
                      │
              Flask REST API  (:5000)
              ├─ Auth &amp; Roles  (CORS, rate limits, security headers)
              ├─ Agent Dispatcher  (30/min run, 20/min stream)
              ├─ Memory Engine  (SQLite FTS5 + ChromaDB + hybrid BM25)
              ├─ Workflow Scheduler  (APScheduler + webhook triggers)
              ├─ Output Manager
              ├─ Ticketing + Email Notifications
              ├─ Namespace Branding (per-namespace metadata)
              └─ Observability

Optional:  MCP Tool Server  (:5100)  — exposes agents to external AI clients</pre>

<div class="note"><strong>Note:</strong> ClaudeOS runs entirely on your own server. No agent
prompts, memory entries, or outputs are sent to any third party except the Anthropic Claude
API (for agent inference) and optionally Supabase (for cloud backup, if enabled).</div>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — SYSTEM REQUIREMENTS
# ═══════════════════════════════════════════════════════════════════════════════

def s2_requirements() -> str:
    return """
<h1><a name="s2"></a>2 &mdash; System Requirements</h1>

<h2>Server (where ClaudeOS runs)</h2>
<table>
<tr><th style="width:28%;">Component</th><th>Minimum</th><th>Recommended</th></tr>
<tr><td>OS</td><td>Windows 10 64-bit</td><td>Windows 10/11 64-bit</td></tr>
<tr><td>CPU</td><td>2 cores</td><td>4+ cores</td></tr>
<tr><td>RAM</td><td>4 GB</td><td>8 GB+</td></tr>
<tr><td>Disk</td><td>10 GB free</td><td>20 GB+ SSD</td></tr>
<tr><td>Python</td><td>3.11</td><td>3.11 or 3.12</td></tr>
<tr><td>Internet</td><td>Required for Claude API calls</td><td>Stable broadband</td></tr>
</table>

<h2>Client Devices (browsers)</h2>
<p>Any modern browser (Chrome, Edge, Firefox, Safari). No installation required on client
devices. Mobile browsers are supported but a desktop screen is recommended for the
Observability and Admin panels.</p>

<h2>Required Accounts &amp; Keys</h2>
<table>
<tr><th style="width:28%;">Service</th><th>Purpose</th><th>Cost</th></tr>
<tr><td>Anthropic Claude API</td>
    <td>Powers all AI agent inference. Required.</td>
    <td>Pay-per-token (see anthropic.com/pricing)</td></tr>
<tr><td>SMTP Email Server</td>
    <td>Email notifications for tickets. Optional.</td>
    <td>Free (Gmail, Outlook) or paid SMTP relay</td></tr>
<tr><td>Supabase (optional)</td>
    <td>Cloud backup of memory and outputs.</td>
    <td>Free tier available</td></tr>
</table>

<div class="warn"><strong>Important:</strong> Keep your <code>ANTHROPIC_API_KEY</code>
secure. Never share it. If compromised, rotate it immediately in the Anthropic console
and update your <code>.env</code> file.</div>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════════

def s3_install() -> str:
    return f"""
<h1><a name="s3"></a>3 &mdash; Installation &amp; First-Run Setup</h1>

<h2>Step 1 &mdash; Get the Code</h2>
<p>Copy the ClaudeOS project folder to your server. Top-level layout:</p>
<pre>ClaudeOS/
├─ agents/       ├─ core/        ├─ dashboard/   ├─ docs/
├─ memory/       ├─ mcp/         ├─ scripts/     ├─ workflows/
├─ requirements.txt              └─ .env.example</pre>

<h2>Step 2 &mdash; Create Your Environment File</h2>
<p>Copy <code>.env.example</code> to <code>.env</code> and fill in your values:</p>
<pre># .env
ANTHROPIC_API_KEY=sk-ant-...           # required
FLASK_SECRET_KEY=change-this-secret    # any long random string
FLASK_PORT=5000
STREAMLIT_PORT=8501
ALLOWED_ORIGINS=http://localhost:8501  # CORS whitelist (comma-separated)

# Optional — Email notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=no-reply@yourdomain.com

# Optional — Supabase cloud backup
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key</pre>

<div class="warn"><strong>Never commit <code>.env</code> to version control.</strong>
The <code>.gitignore</code> already excludes it.</div>

<h2>Step 3 &mdash; Install Python Dependencies</h2>
<pre>pip install -r requirements.txt</pre>
<p>Installs Flask, Streamlit, Anthropic SDK, ChromaDB, sentence-transformers, APScheduler,
waitress, plotly, PyJWT, bcrypt, and all other required packages.</p>
<pre># Optional — Voice input (~140 MB model on first use)
pip install openai-whisper

# Optional — MCP Tool Server
pip install mcp uvicorn</pre>

<h2>Step 4 &mdash; Initialise the Database</h2>
<pre>python scripts/migrate.py</pre>
<p>Creates <code>data/claudeos.db</code> with all tables including auth, memory, agents,
workflows, tickets, branding metadata, and observability columns.</p>

<h2>Step 5 &mdash; Seed Default Data</h2>
<pre>python scripts/seed_agents.py       # loads 12 agent definitions
python scripts/seed_workflows.py    # loads 7 default pipelines
python scripts/seed_namespaces.py   # creates the global namespace

# Optional — pre-populate client onboarding fields (14 fields, skips existing)
python scripts/seed_client_schema.py --namespace faiyke-ai</pre>
<p><code>seed_client_schema.py</code> creates blank placeholder memory entries for a client namespace
(business name, industry, primary goals, brand tone, SLA tier, contact details, timezone, etc.).
Agents read these automatically. Run after creating the namespace; safe to run multiple times.</p>

<h2>Step 6 &mdash; Create the Admin Account</h2>
<pre>python scripts/create_admin.py --username admin --password Admin123!</pre>
<div class="warn">Minimum password: 10 characters, at least one uppercase, one lowercase, one digit.</div>

<h2>Step 7 &mdash; Start the System</h2>
<pre>.\\scripts\\start.ps1</pre>
<p>Kills existing processes on ports 5000 and 8501, starts Flask via waitress, verifies
<code>/health</code>, then starts Streamlit. After 5&ndash;10 seconds, open your browser
to <strong>{SYSTEM_URL}</strong>.</p>

<h2>Optional &mdash; Start the MCP Server</h2>
<pre>.\\scripts\\start_mcp.ps1</pre>

<h2>Stopping the System</h2>
<pre>netstat -ano | findstr :5000   # get PID
taskkill /F /PID &lt;PID&gt;         # kill it  (repeat for 8501)</pre>

<div class="tip"><strong>After any change to <code>.env</code>:</strong> always restart the
server. Running processes do not pick up environment changes automatically.</div>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — LOGGING IN & FIRST-TIME EXPERIENCE
# ═══════════════════════════════════════════════════════════════════════════════

def s4_login() -> str:
    return """
<h1><a name="s4"></a>4 &mdash; Logging In &amp; First-Time Experience</h1>

<h2>First Login</h2>
<p>Navigate to the dashboard URL in your browser. You will see the ClaudeOS login screen
with two tabs: <strong>Login</strong> and <strong>Register</strong>. Your namespace branding
(logo, colours, background) is applied to the login page automatically.</p>
<p>Enter the username and temporary password provided by your administrator, then press
<strong>Enter</strong> or click <strong>Login</strong>. If the admin set the
<em>must change password</em> flag, you will be prompted to set a new password immediately.</p>

<h2>Password Requirements</h2>
<ul>
<li>Minimum 10 characters</li>
<li>At least one uppercase letter (A&ndash;Z)</li>
<li>At least one lowercase letter (a&ndash;z)</li>
<li>At least one digit (0&ndash;9)</li>
</ul>

<h2>Onboarding Modal (Client &amp; Viewer Roles) <span class="badge-new">NEW v14.0</span></h2>
<p>The very first time a <strong>client</strong> or <strong>viewer</strong> logs in, a
5-slide onboarding modal appears automatically. It walks through the key features:</p>
<table>
<tr><th style="width:12%;">Slide</th><th>Title</th><th>What It Covers</th></tr>
<tr><td>1</td><td>Welcome</td><td>What ClaudeOS is, your namespace, and how to navigate.</td></tr>
<tr><td>2</td><td>AI Agents</td><td>How to run agents via chat and catalog. Streaming explained.</td></tr>
<tr><td>3</td><td>Memory</td><td>Writing memory entries, categories, and how memory helps agents.</td></tr>
<tr><td>4</td><td>Tickets</td><td>Creating and tracking tickets. Email notification opt-in.</td></tr>
<tr><td>5</td><td>Usage Dashboard</td><td>KPIs, Pulse Score, AI activity feed, and memory summary.</td></tr>
</table>
<p>A progress bar and <strong>Next / Dismiss</strong> buttons control the modal. After dismissal,
it does not appear again for that account. Admin and Operator roles do not see the onboarding modal.</p>

<h2>Self-Registration (if enabled)</h2>
<ol>
<li>Click the <strong>Register</strong> tab on the login screen</li>
<li>Enter username, email, password, and select your namespace</li>
<li>Click <strong>Register</strong> &mdash; you are returned to the Login tab</li>
<li>Log in with your new credentials</li>
</ol>

<h2>User Roles</h2>
<table>
<tr><th style="width:15%;">Role</th><th>What They Can Do</th></tr>
<tr><td><strong>Admin</strong></td>
    <td>Full access &mdash; all namespaces, user management, branding config, admin panel, all features.</td></tr>
<tr><td><strong>Operator</strong></td>
    <td>All namespaces and features except user management and the Admin panel.</td></tr>
<tr><td><strong>Client</strong></td>
    <td>Own namespace only &mdash; Usage dashboard, memory, agents, outputs, tickets.
    Sees namespace branding on login.</td></tr>
<tr><td><strong>Viewer</strong></td>
    <td>Own namespace, read-only. Cannot write memory or run agents.</td></tr>
<tr><td><strong>Staff</strong></td>
    <td>Support role &mdash; only sees tickets assigned to them. Can self-assign open tickets.</td></tr>
</table>

<h2>Account Security</h2>
<ul>
<li><strong>Account lockout:</strong> 5 failed attempts triggers a 15-minute lockout.</li>
<li><strong>Session tokens:</strong> JWT access tokens expire after 60 minutes and are
    silently refreshed while you are active.</li>
<li><strong>Case-insensitive usernames:</strong> <code>Alice</code> and <code>alice</code>
    refer to the same account.</li>
<li><strong>Page persistence:</strong> your active page is saved in the URL query param
    <code>?page=PageName</code> &mdash; browser refresh returns you to the same page.</li>
</ul>

<h2>Theme Toggle</h2>
<p>A dark/light mode button sits in the <strong>bottom-left corner</strong> of every page.
Your theme preference persists for the current session.</p>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — DASHBOARD TOUR
# ═══════════════════════════════════════════════════════════════════════════════

def s5_dashboard() -> str:
    return """
<h1><a name="s5"></a>5 &mdash; Dashboard Tour</h1>

<h2>Overview Page</h2>
<p>The home page shows current system health and recent activity at a glance. KPIs are
now <strong>namespace-scoped</strong>: admin/operator see global counts; client/viewer
see only their namespace data.</p>
<table>
<tr><th style="width:30%;">Element</th><th>What It Shows</th></tr>
<tr><td>System Status strip</td><td>Green/red indicators for the API and database.</td></tr>
<tr><td>KPI Cards</td><td>Memory entries, registered agents, runs, workflows, outputs &mdash; scoped to your namespace.</td></tr>
<tr><td>Recent Events feed</td><td>Last 8 agent run results with agent name, namespace, timestamp, and quality score pill.</td></tr>
<tr><td>Quick Dispatch</td><td>Run any agent against any namespace with a one-off prompt.</td></tr>
<tr><td>Memory by Namespace</td><td>Count of active memory entries per namespace.</td></tr>
<tr><td>Auto-refresh toggle</td><td>Refreshes every 8 seconds &mdash; useful for monitoring live runs.</td></tr>
<tr><td>Error alert strip</td><td>Red banner when any recent run failed.</td></tr>
<tr><td>Running-now indicator</td><td>Yellow banner listing agents currently executing.</td></tr>
</table>

<h2>Eval Score Pills</h2>
<table>
<tr><th style="width:20%;">Colour</th><th>Score Range</th><th>Meaning</th></tr>
<tr><td><span class="pill-green">Green</span></td><td>4.0 &ndash; 5.0</td><td>High quality.</td></tr>
<tr><td><span class="pill-amber">Amber</span></td><td>2.5 &ndash; 3.9</td><td>Acceptable &mdash; review before sending to client.</td></tr>
<tr><td><span class="pill-red">Red</span></td><td>0 &ndash; 2.4</td><td>Low quality &mdash; re-run with a more specific prompt.</td></tr>
</table>

<h2>Usage Page (Client &amp; Viewer Only) <span class="badge-new">NEW v14.0</span></h2>
<p>A dedicated page for client and viewer roles providing a full activity overview for their namespace.</p>

<h3>KPI Cards (30-day rolling)</h3>
<table>
<tr><th style="width:28%;">KPI</th><th>Description</th></tr>
<tr><td>AI Runs (30d)</td><td>Total agent runs in the last 30 days for this namespace.</td></tr>
<tr><td>Tokens In / Out</td><td>Total input and output tokens consumed.</td></tr>
<tr><td>Est. Cost (USD)</td><td>Estimated spend based on current claude-sonnet-4-6 pricing.</td></tr>
<tr><td>Avg Quality</td><td>Rolling average eval score across all scored runs.</td></tr>
<tr><td>Outputs</td><td>Total saved outputs for this namespace.</td></tr>
</table>

<h3>Namespace Pulse Score</h3>
<p>A composite 0&ndash;100 health score for the namespace, shown as a circular gauge.</p>
<div class="gauge-block">
<strong>Formula:</strong> (Avg Quality &times; 0.40) + (Ticket Resolution Rate &times; 0.30) + (Memory Freshness &times; 0.20) + (Workflow Success &times; 0.10)<br/>
<strong>Colour:</strong> &ge;75 = <span class="pill-green">Excellent / Good</span> &nbsp;
&ge;50 = <span class="pill-amber">Fair</span> &nbsp;
&lt;50 = <span class="pill-red">Needs Attention</span> &nbsp;
No data = <span class="pill-gray">Getting Started</span>
</div>

<h3>Recent AI Activity Feed</h3>
<p>Last 10 agent runs for this namespace showing: agent name, status, eval score, duration, and timestamp.</p>

<h3>Memory Summary</h3>
<p>Total memory entries, fresh entries (written in the last 7 days), and date of last consolidation run.</p>

<h2>Memory Page</h2>
<ul>
<li>Full-text search across keys and values</li>
<li>Filter by namespace, category, and minimum confidence</li>
<li>Write entries with category, TTL, and confidence score</li>
<li>Toggle <strong>Hybrid Search</strong> for BM25 + vector semantic retrieval</li>
<li>Bulk delete via checkbox selection</li>
</ul>

<h2>Agents Page</h2>
<p>Three tabs &mdash; Chat, Catalog, and Run History. Covered in detail in Section 6.</p>

<h2>Workflows Page</h2>
<p>7 pipelines, manual triggers, run history, and a Webhooks tab. Covered in Section 8.</p>

<h2>Client Vault Page</h2>
<p>Namespace stats, project list, context file upload. Covered in Section 9.</p>

<h2>Outputs Page</h2>
<p>All AI-generated content. Full-text search, date and type filters, per-output export. Covered in Section 10.</p>

<h2>Tickets Page</h2>
<p>Full ticket lifecycle with email notifications. Covered in Section 11.</p>

<h2>Observability Page (Admin / Operator)</h2>
<p>Five tabs: Quality Scores, Latency, Token Cost, Memory Health, and <strong>Namespace Usage</strong>
(cross-namespace run/token/cost/quality comparison with stacked bar chart). Covered in Section 13.</p>

<h2>Settings Page (Admin / Operator)</h2>
<p>System config, Supabase sync controls, Email Notification settings, environment info.</p>

<h2>Admin Panel (Admin only)</h2>
<p>Six tabs: Users (context-aware unlock &mdash; Unlock button only shown for locked accounts),
API Keys, Audit Log, Sessions, Security config, and <strong>Client Onboarding</strong>
(fill 14 standard fields per namespace so agents have rich context from day one).
Covered in Sections 14 and 18.</p>

<h2>Page Persistence <span class="badge-new">NEW v14.0</span></h2>
<p>The active page is stored in the URL query parameter <code>?page=PageName</code>. Refreshing
the browser returns you to the same page. Bookmarking a URL opens that page directly after login.</p>

<h2>Background Colour Picker</h2>
<p>The sidebar contains a <strong>&#127912; Background color</strong> expander. Any logged-in
user can set a custom page background. Covered in detail in Section 15.</p>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — WORKING WITH AI AGENTS
# ═══════════════════════════════════════════════════════════════════════════════

def s6_agents() -> str:
    return """
<h1><a name="s6"></a>6 &mdash; Working with AI Agents</h1>

<h2>The 12 Built-In Agents</h2>
<table>
<tr><th style="width:28%;">Agent</th><th style="width:15%;">Category</th><th>What It Does</th></tr>
<tr><td><strong>Analysis Agent</strong></td><td>Analysis</td>
    <td>Structured reports, key findings, and recommendations from raw data or context.</td></tr>
<tr><td><strong>Morning Briefing Agent</strong></td><td>Ops</td>
    <td>Synthesises overnight context into a daily briefing: reminders, client updates, priorities.</td></tr>
<tr><td><strong>Client Manager Agent</strong></td><td>Ops</td>
    <td>Per-client project status cards with deadlines, blockers, and action items.</td></tr>
<tr><td><strong>Communications Agent</strong></td><td>Comms</td>
    <td>Client-facing emails, messages, and proposals &mdash; tone-matched to each client.</td></tr>
<tr><td><strong>Memory Curator Agent</strong></td><td>System</td>
    <td>Reviews, deduplicates, and consolidates memory entries.</td></tr>
<tr><td><strong>Meta Orchestrator Agent</strong></td><td>System</td>
    <td>Decomposes complex goals into ordered chains of agent invocations.</td></tr>
<tr><td><strong>QA Agent</strong></td><td>Engineering</td>
    <td>Code review against OWASP, platform compatibility, and brand compliance rules.</td></tr>
<tr><td><strong>Research Agent</strong></td><td>Research</td>
    <td>Deep research with synthesis and source validation across a given topic.</td></tr>
<tr><td><strong>Scheduling Agent</strong></td><td>Ops</td>
    <td>Converts natural language scheduling requests into memory reminder entries.</td></tr>
<tr><td><strong>Transport Ops Agent</strong></td><td>Domain</td>
    <td>Domain-specific fleet and booking analysis &mdash; namespace-locked.</td></tr>
<tr><td><strong>Workflow Builder Agent</strong></td><td>System</td>
    <td>Converts plain-English automation descriptions into ClaudeOS workflow YAML.</td></tr>
<tr><td><strong>Writing Agent</strong></td><td>Content</td>
    <td>Drafts reports, emails, and proposals with voice matched to the active namespace.</td></tr>
</table>

<h2>Running an Agent &mdash; Three Ways</h2>

<h3>1. Chat (Recommended for iterative work)</h3>
<p>Go to <strong>Agents &rarr; Chat</strong>. Select agent and namespace, type your request,
press Enter. The response streams back in real time. Follow up with additional messages.</p>
<div class="tip"><strong>Best practice:</strong> be specific. &ldquo;Write a 2-page executive summary
of Q2 analysis results for the mobile app project, highlighting the top 3 risks&rdquo; scores
significantly higher than &ldquo;write a report&rdquo;.</div>

<h3>2. Catalog (For one-shot tasks)</h3>
<p>Go to <strong>Agents &rarr; Catalog</strong>. Find the agent, fill in prompt and namespace,
click <strong>Run</strong>. Polled every 3 seconds until complete.</p>

<h3>3. Quick Dispatch (From Overview)</h3>
<p>The Overview page Quick Dispatch widget &mdash; select agent, namespace, enter prompt, run.</p>

<h2>Namespace Scoping</h2>
<p>Every agent run is scoped to a namespace. The namespace controls which memory entries are
injected into context and where output is stored. Client and Viewer roles only see their own namespace.</p>

<h2>Image Analysis</h2>
<ul>
<li>Attach a screenshot, chart, or document for visual analysis in the Chat tab</li>
<li>Agent receives the image as a content block alongside your prompt</li>
<li>Uses: dashboard analysis, UI review, chart interpretation, document extraction</li>
</ul>

<h2>Voice Input</h2>
<p>Click the microphone in the Chat tab. Record your request (up to 30 seconds). ClaudeOS
transcribes locally using Whisper &mdash; nothing sent to external services. Review transcription,
edit if needed, then submit. Requires <code>pip install openai-whisper</code>.</p>

<h2>Understanding Token Usage</h2>
<p>Each response shows input tokens (context sent) and output tokens (response generated).
To keep costs low:</p>
<ul>
<li>Use specific prompts (less context padding needed)</li>
<li>Clear conversation history when starting a new topic</li>
<li>Use lighter agents for simple tasks (e.g. Scheduling Agent vs. Research Agent)</li>
</ul>

<h2>Rate Limits</h2>
<table>
<tr><th style="width:30%;">Endpoint</th><th>Limit</th></tr>
<tr><td>Agent <code>/run</code></td><td>30 requests per minute per IP</td></tr>
<tr><td>Agent <code>/stream</code></td><td>20 requests per minute per IP</td></tr>
<tr><td>Workflow <code>/trigger</code></td><td>10 requests per minute per IP</td></tr>
</table>
<p>If a rate limit is hit, the API returns <code>429 Too Many Requests</code>. Wait and retry.</p>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — MEMORY SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

def s7_memory() -> str:
    return """
<h1><a name="s7"></a>7 &mdash; Memory System</h1>

<h2>What Is Memory?</h2>
<p>Memory is ClaudeOS's persistent knowledge store. When you or an agent writes a memory
entry, it is stored in the database and automatically injected into every subsequent agent
run in that namespace. Agents remember facts, preferences, context, and reminders across
sessions &mdash; without you having to repeat yourself.</p>

<h2>Memory Categories</h2>
<table>
<tr><th style="width:18%;">Category</th><th>Use For</th><th>Example</th></tr>
<tr><td><strong>Fact</strong></td><td>Stable information about a client or project</td>
    <td>&ldquo;Client prefers invoices in GBP&rdquo;</td></tr>
<tr><td><strong>Preference</strong></td><td>Tone, style, or format preferences</td>
    <td>&ldquo;Reports should start with an executive summary&rdquo;</td></tr>
<tr><td><strong>Reminder</strong></td><td>Time-sensitive items that expire automatically</td>
    <td>&ldquo;Follow up on proposal by 2026-06-01&rdquo;</td></tr>
<tr><td><strong>Task</strong></td><td>Action items for agents or team members</td>
    <td>&ldquo;Prepare Q3 analysis before board meeting&rdquo;</td></tr>
</table>

<h2>Writing a Memory Entry</h2>
<ol>
<li>Go to <strong>Memory</strong> page &rarr; click <strong>Add Entry</strong></li>
<li>Fill in: key (short identifier), value (content), category, TTL (optional expiry in days), confidence (0&ndash;1)</li>
<li>For reminders: use the date/time picker to set the exact expiry</li>
<li>Click <strong>Save</strong></li>
</ol>

<h2>Searching Memory</h2>
<p>Full-text search across keys and values. Toggle <strong>Hybrid Search</strong> for
BM25 + semantic vector retrieval &mdash; better recall for conceptual queries (e.g. &ldquo;client
payment terms&rdquo; finds entries about invoicing even without exact keyword match).</p>

<h2>How Memory Is Injected into Agents</h2>
<p>When an agent runs, ClaudeOS retrieves the most relevant memory entries using hybrid
search and injects them into the agent's system prompt as structured context. The tiered
context system reduces token usage by ~40% versus injecting all memory.</p>

<h2>Memory Consolidation</h2>
<p>An automated job runs every 4 hours. It finds groups of similar entries, uses Claude
to synthesise each cluster into one concise entry, and archives the originals. Original
entries are never hard-deleted &mdash; they are archived (<code>archived=1</code>).</p>
<p>Trigger consolidation immediately: <strong>Observability &rarr; Memory Health &rarr; Trigger Consolidation</strong>.</p>

<div class="tip"><strong>Tip:</strong> write memory entries in full sentences.
&ldquo;The client's primary contact is James Brown, james@example.com, +44 7700 900000&rdquo;
is far more useful to an agent than &ldquo;james contact&rdquo;.</div>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — WORKFLOWS & AUTOMATION
# ═══════════════════════════════════════════════════════════════════════════════

def s8_workflows() -> str:
    return f"""
<h1><a name="s8"></a>8 &mdash; Workflows &amp; Automation</h1>

<h2>What Are Workflows?</h2>
<p>Workflows are multi-step AI pipelines that chain agent calls, passing output from one
step as input to the next. They run on a cron schedule or are triggered manually or via webhook.</p>

<h2>Built-In Workflows</h2>
<table>
<tr><th style="width:30%;">Workflow</th><th>What It Does</th><th style="width:20%;">Default Schedule</th></tr>
<tr><td><strong>Morning Briefing</strong></td>
    <td>Synthesises overnight memory into a daily briefing.</td><td>Mon&ndash;Fri 07:00</td></tr>
<tr><td><strong>Memory Curation</strong></td>
    <td>Deduplicates and consolidates memory entries.</td><td>Every 4 hours</td></tr>
<tr><td><strong>Research Digest</strong></td>
    <td>Research Agent deep-dive and structured digest.</td><td>On demand</td></tr>
<tr><td><strong>Client Report</strong></td>
    <td>Client Manager Agent generates status cards for all active projects.</td><td>Weekly</td></tr>
<tr><td><strong>Analysis Run</strong></td>
    <td>Analysis Agent processes queued data and produces findings.</td><td>On demand</td></tr>
<tr><td><strong>QA Sweep</strong></td>
    <td>QA Agent reviews recent outputs against quality and compliance rules.</td><td>On demand</td></tr>
<tr><td><strong>Meta-Orchestrate</strong></td>
    <td>Meta Orchestrator decomposes a complex goal into a chain of agent calls.</td><td>On demand</td></tr>
</table>

<h2>Running a Workflow Manually</h2>
<ol>
<li>Go to <strong>Workflows</strong> page</li>
<li>Find the workflow &rarr; click <strong>Run Now</strong></li>
<li>The run appears in Recent Events on the Overview page</li>
</ol>

<h2>Webhook Triggers</h2>
<p>Any workflow can be triggered by an external system without a login token.
Rate limit: <strong>10 requests per minute</strong> per IP.</p>

<h3>Enable a Webhook</h3>
<ol>
<li>Workflows page &rarr; select workflow &rarr; <strong>Webhooks</strong> tab</li>
<li>Click <strong>Enable Webhook</strong> &mdash; a unique URL and HMAC secret are generated</li>
<li>Copy both. The secret is shown once &mdash; store it safely.</li>
</ol>

<h3>Fire the Webhook</h3>
<pre>curl -X POST {API_URL}/api/v1/workflows/morning-briefing/trigger \\
  -H "X-Webhook-Secret: your-secret" \\
  -H "Content-Type: application/json" \\
  -d '{{"context": {{"namespace": "global", "topic": "AI news"}}}}'</pre>

<h2>Viewing Workflow Run History</h2>
<p>Each workflow card shows its last run timestamp and status. Expand to see the
step-by-step run log.</p>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — CLIENT VAULT
# ═══════════════════════════════════════════════════════════════════════════════

def s9_vault() -> str:
    return """
<h1><a name="s9"></a>9 &mdash; Client Vault</h1>

<h2>Namespaces</h2>
<p>A namespace is a fully isolated workspace. All memory, outputs, and agent context is
scoped per namespace &mdash; nothing leaks between namespaces. The Client Vault page shows:</p>
<ul>
<li>Namespace name, description, and icon (set in Admin &rarr; Branding)</li>
<li>Workspace statistics: number of files, total size in KB</li>
<li>Number of active projects</li>
</ul>

<h2>Projects</h2>
<ul>
<li>List all projects in your namespace</li>
<li>Update a project's status: <strong>Active</strong> / <strong>Paused</strong> / <strong>Archived</strong></li>
<li>See project descriptions and creation dates</li>
</ul>

<h2>Context Files</h2>
<p>Documents uploaded per namespace that are automatically injected into every agent
system prompt for that namespace. Use for:</p>
<ul>
<li>Brand guidelines and tone-of-voice documents</li>
<li>Standard operating procedures</li>
<li>Client briefs or background documents</li>
<li>Technical specifications that agents should always be aware of</li>
</ul>
<p>Supported formats: plain text, Markdown, PDF.</p>

<div class="note"><strong>Note:</strong> Keep context files concise. Very large files increase
token usage on every agent call. Split large documents into smaller topical files.</div>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — OUTPUTS & REPORTS
# ═══════════════════════════════════════════════════════════════════════════════

def s10_outputs() -> str:
    return """
<h1><a name="s10"></a>10 &mdash; Outputs &amp; Reports</h1>

<h2>What Are Outputs?</h2>
<p>Every time an agent produces a response with <code>save_output: true</code> (the default),
the full output is saved to the database and filesystem, auto-tagged with agent name,
namespace, output type, and timestamp.</p>

<h2>Browsing Outputs</h2>
<ul>
<li>Search by keyword across all output content (full-text)</li>
<li>Filter by namespace, output type (report / summary / plan / analysis / code / other), and date range</li>
<li>Click any output to expand and read the full content</li>
</ul>

<h2>Exporting an Output</h2>
<table>
<tr><th style="width:20%;">Format</th><th>Notes</th></tr>
<tr><td><strong>Markdown</strong></td>
    <td>Raw text with Markdown formatting. Opens in any text editor. Always available.</td></tr>
<tr><td><strong>PDF</strong></td>
    <td>Rendered PDF with ClaudeOS branding. Requires wkhtmltopdf installed on the server.</td></tr>
</table>

<h2>Bulk Delete</h2>
<p>Select multiple outputs with checkboxes and click the bulk delete button. Permanent &mdash;
not recoverable unless Supabase cloud sync is enabled.</p>

<div class="tip"><strong>Tip:</strong> use type and date filters to find old or low-quality
outputs before bulk deleting.</div>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — TICKETING SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

def s11_tickets() -> str:
    return """
<h1><a name="s11"></a>11 &mdash; Ticketing System</h1>

<h2>Overview</h2>
<p>The ticketing system provides a full support and task lifecycle inside ClaudeOS.
Version 14.0 adds <strong>email notifications</strong> for ticket events.</p>

<h2>Priority / SLA Tiers</h2>
<table>
<tr><th style="width:10%;">Priority</th><th style="width:20%;">Label</th><th>Meaning</th></tr>
<tr><td>P1</td><td><strong>Critical</strong></td><td>System down or blocking. Immediate response required.</td></tr>
<tr><td>P2</td><td><strong>High</strong></td><td>Major issue, significant business impact.</td></tr>
<tr><td>P3</td><td><strong>Medium</strong></td><td>Important but not blocking.</td></tr>
<tr><td>P4</td><td><strong>Low</strong></td><td>Nice-to-have, enhancement, or minor issue.</td></tr>
</table>

<h2>Ticket Lifecycle</h2>
<pre>Open  &rarr;  In Progress  &rarr;  Resolved  &rarr;  Closed</pre>
<ul>
<li><strong>Open:</strong> created, not yet assigned or started</li>
<li><strong>In Progress:</strong> assigned and being worked on</li>
<li><strong>Resolved:</strong> work complete, awaiting confirmation</li>
<li><strong>Closed:</strong> confirmed resolved, resolution note recorded</li>
</ul>

<h2>Creating a Ticket</h2>
<ol>
<li>Go to <strong>Tickets</strong> page &rarr; click <strong>New Ticket</strong></li>
<li>Fill in title, description, priority, namespace, and optionally assign users</li>
<li>Click <strong>Create</strong></li>
</ol>

<h2>Assignment</h2>
<ul>
<li><strong>Admin / Operator:</strong> can assign any ticket to any user</li>
<li><strong>Staff:</strong> can self-assign any open ticket</li>
<li><strong>Client / Viewer:</strong> cannot assign tickets</li>
</ul>

<h2>Email Notifications <span class="badge-new">NEW v14.0</span></h2>
<p>ClaudeOS sends automatic email notifications for key ticket events when SMTP is configured.
Configure in <strong>Settings &rarr; Email Notifications</strong>.</p>

<h3>Configuring SMTP</h3>
<table>
<tr><th style="width:28%;">Setting</th><th>Description</th></tr>
<tr><td>SMTP Host</td><td>Your email server (e.g. <code>smtp.gmail.com</code>)</td></tr>
<tr><td>SMTP Port</td><td>Usually 587 (TLS) or 465 (SSL)</td></tr>
<tr><td>SMTP User</td><td>Email address used for sending</td></tr>
<tr><td>SMTP Password</td><td>App password or SMTP credential</td></tr>
<tr><td>From Address</td><td>Displayed sender (e.g. <code>no-reply@yourcompany.com</code>)</td></tr>
</table>

<h3>Notification Events</h3>
<table>
<tr><th style="width:35%;">Event</th><th>Who Receives It</th></tr>
<tr><td>Ticket created with assignees</td><td>All assigned users receive a notification email</td></tr>
<tr><td>Ticket resolved or closed</td><td>Ticket creator receives a resolution email</td></tr>
<tr><td>SLA breach</td><td>Assignees and admin receive an SLA alert email</td></tr>
</table>

<h3>Global Toggle &amp; Test Send</h3>
<p>A <strong>global enable/disable toggle</strong> controls all email notifications at once.
Use the <strong>Test Send</strong> button to verify your SMTP configuration is working
before enabling live notifications.</p>

<div class="note"><strong>Gmail users:</strong> use an App Password (not your account password)
if 2-factor authentication is enabled. Generate one at myaccount.google.com &rarr; Security &rarr; App Passwords.</div>

<h2>Comments</h2>
<p>Expand a ticket and click the <strong>Comments</strong> toggle to load threaded comments.
Comments load on demand to keep the page fast.</p>

<h2>Resolution Notes &amp; Bulk Delete</h2>
<p>Record what was done in the resolution note field when moving a ticket to Resolved or Closed.
Bulk delete is available to Admin / Operator only.</p>

<h2>Stats Panel</h2>
<p>Ticket counts broken down by status and priority at the top of the Tickets page.</p>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — QUALITY SCORING
# ═══════════════════════════════════════════════════════════════════════════════

def s12_quality() -> str:
    return """
<h1><a name="s12"></a>12 &mdash; Quality Scoring</h1>

<h2>How It Works</h2>
<p>Every agent run is automatically scored by Claude Haiku (fast, low-cost) on 4 dimensions.
Scoring happens asynchronously in the background &mdash; no added latency. Scores appear
5&ndash;15 seconds after a run completes.</p>

<h2>Scoring Dimensions</h2>
<table>
<tr><th style="width:25%;">Dimension</th><th style="width:10%;">Scale</th><th style="width:10%;">Weight</th><th>What It Measures</th></tr>
<tr><td><strong>Task Completion</strong></td><td>0&ndash;5</td><td>40%</td>
    <td>Did the output fully address the prompt?</td></tr>
<tr><td><strong>Factual Grounding</strong></td><td>0&ndash;5</td><td>30%</td>
    <td>Are claims grounded in the injected memory context? Penalises hallucination.</td></tr>
<tr><td><strong>Conciseness</strong></td><td>0&ndash;5</td><td>20%</td>
    <td>Is the output the right length? Penalises padding and repetition.</td></tr>
<tr><td><strong>Safety</strong></td><td>pass/fail</td><td>10%</td>
    <td>Does output contain harmful content? Fail caps overall score at 1.0.</td></tr>
</table>
<p><strong>Overall score</strong> = (Task &times; 0.40) + (Factual &times; 0.30) + (Concise &times; 0.20) + (Safety &times; 0.10)</p>

<h2>Where Scores Appear</h2>
<ul>
<li><strong>Run History:</strong> colour-coded pill per run</li>
<li><strong>Overview:</strong> pill on each recent event</li>
<li><strong>Chat:</strong> badge below each assistant response (~10s delay)</li>
<li><strong>Usage Dashboard:</strong> 30-day average in Avg Quality KPI card</li>
<li><strong>Observability &rarr; Quality Scores:</strong> aggregated analytics</li>
</ul>

<h2>Improving Scores</h2>
<table>
<tr><th style="width:30%;">Low score on...</th><th>What to do</th></tr>
<tr><td>Task Completion</td>
    <td>Be more specific. State exactly what you want, the format, and the desired length.</td></tr>
<tr><td>Factual Grounding</td>
    <td>Add more relevant facts to Memory before running the agent.</td></tr>
<tr><td>Conciseness</td>
    <td>Add &ldquo;be concise&rdquo; or &ldquo;maximum 3 paragraphs&rdquo; to your prompt.</td></tr>
<tr><td>Safety</td>
    <td>Review the output for any problematic content. Adjust the prompt.</td></tr>
</table>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 13 — OBSERVABILITY
# ═══════════════════════════════════════════════════════════════════════════════

def s13_observability() -> str:
    return """
<h1><a name="s13"></a>13 &mdash; Observability</h1>

<p>Available to <strong>Admin</strong> and <strong>Operator</strong> roles only. Five sub-tabs.</p>

<h2>Quality Scores Tab</h2>
<ul>
<li>Per-agent average eval scores in a ranked table</li>
<li>Score distribution chart (0.5-step buckets across all runs)</li>
<li>Dimension breakdown: task completion, factual grounding, conciseness, safety</li>
<li>Red alert when any agent's average drops below 2.5</li>
</ul>

<h2>Latency Tab</h2>
<ul>
<li>p50, p95, and p99 latency across all runs</li>
<li>Per-agent average latency table sorted by slowest</li>
<li>Time-series chart over the past 7 days</li>
</ul>
<table>
<tr><th>Response length</th><th>Typical latency (claude-sonnet-4-6)</th></tr>
<tr><td>Short (under 200 tokens)</td><td>2&ndash;6 seconds</td></tr>
<tr><td>Medium (200&ndash;800 tokens)</td><td>6&ndash;20 seconds</td></tr>
<tr><td>Long (800+ tokens)</td><td>20&ndash;60 seconds</td></tr>
</table>

<h2>Token Cost Tab</h2>
<ul>
<li>Total input and output token counts across all runs</li>
<li>Estimated USD cost based on current claude-sonnet-4-6 pricing</li>
<li>Per-agent breakdown: tokens used, cost, run count, average cost per run</li>
</ul>
<div class="note">Token cost estimates are approximate based on list pricing at ClaudeOS release.
Check Anthropic's pricing page for current rates.</div>

<h2>Memory Health Tab</h2>
<ul>
<li>Entry counts per namespace: total, active, consolidated, expired</li>
<li>Storage size estimate per namespace</li>
<li><strong>Trigger Consolidation</strong> button &mdash; runs the consolidation job immediately</li>
<li>Visual indicator when any namespace has not been consolidated in over 24 hours</li>
</ul>

<h2>Namespace Usage Tab <span class="badge-new">NEW v15.0</span></h2>
<p>Cross-namespace comparison for admins and operators. Shows, for each namespace:</p>
<ul>
<li>Total agent runs, input tokens, output tokens, estimated USD cost</li>
<li>Average quality score and memory entry count</li>
<li>Stacked bar chart (plotly) comparing token consumption across all namespaces</li>
</ul>
<p>Based on up to 500 most recent runs. Helps identify which namespaces are most active
and where token spend is concentrated.</p>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 14 — NAMESPACE BRANDING & CUSTOMISATION (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

def s14_branding() -> str:
    return """
<h1><a name="s14"></a>14 &mdash; Namespace Branding &amp; Customisation <span class="badge-new">NEW v14.0</span></h1>

<h2>Overview</h2>
<p>ClaudeOS supports full per-namespace white-labeling. Each namespace can have its own
company name, icon, primary colour, accent colour, and background colour. Clients see
their own brand applied to the login screen, sidebar, and dashboard headers &mdash; creating
a personalised experience without any code changes.</p>

<h2>Configuring Namespace Branding</h2>
<p>Only the <strong>Admin</strong> role can configure branding. Go to <strong>Admin Panel &rarr; Branding</strong> tab.</p>

<h3>Available Brand Settings</h3>
<table>
<tr><th style="width:28%;">Setting</th><th>Description</th><th style="width:20%;">Example</th></tr>
<tr><td><strong>Company Name</strong></td>
    <td>Replaces &ldquo;ClaudeOS&rdquo; in the sidebar header for users of this namespace</td>
    <td>Acme Corp AI</td></tr>
<tr><td><strong>Icon Emoji</strong></td>
    <td>Emoji shown next to the company name in the sidebar</td>
    <td>&#128170; &#128640; &#127757;</td></tr>
<tr><td><strong>Primary Color</strong></td>
    <td>Used for buttons, active highlights, headings, and progress bars</td>
    <td>#1565C0 (blue)</td></tr>
<tr><td><strong>Accent Color</strong></td>
    <td>Used for hover states, secondary actions, and links</td>
    <td>#42A5F5 (light blue)</td></tr>
<tr><td><strong>Background Color</strong></td>
    <td>Default page background for all users in this namespace. Overrideable per-user (Sec 15).</td>
    <td>#F0F4FF</td></tr>
</table>

<h2>Live Preview</h2>
<p>The Branding tab shows a live preview panel as you adjust settings. Sample text, a button,
and a card are rendered using the chosen colours with auto-computed contrast text, so you can
verify readability before saving.</p>

<div class="warn"><strong>Auto-contrast:</strong> ClaudeOS automatically derives readable text
colours from your chosen primary and background colours using the WCAG luminance formula.
You cannot set a colour combination that fails basic contrast requirements &mdash; the UI
will warn you if a colour is too similar to the background.</div>

<h2>Where Branding Appears</h2>
<ul>
<li><strong>Login screen:</strong> company name, icon, and background colour applied before login</li>
<li><strong>Sidebar:</strong> company name and icon replace &ldquo;ClaudeOS&rdquo; header</li>
<li><strong>Dashboard headers:</strong> primary colour used for heading accents</li>
<li><strong>Buttons and highlights:</strong> accent colour used for interactive elements</li>
</ul>

<h2>White-Label Footer</h2>
<p>All white-labeled deployments show a subtle <em>&ldquo;Powered by ClaudeOS&rdquo;</em>
note in the page footer. This attribution cannot be removed in the standard licence.</p>

<h2>Background Color for Namespace</h2>
<p>The background colour set in the Branding tab becomes the default for all users in that
namespace. Individual users can override it using the personal background colour picker
(see Section 15). The namespace default persists across sessions; the personal override is
session-only and resets on logout.</p>

<h2>Resetting to Default</h2>
<p>Click <strong>Reset to Defaults</strong> in the Branding tab to restore ClaudeOS green
(<code>#407E3C</code>) and white for that namespace. This takes effect on the next page load
for all users in the namespace.</p>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 15 — CUSTOM BACKGROUND COLORS (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

def s15_bgcolor() -> str:
    return """
<h1><a name="s15"></a>15 &mdash; Custom Background Colors <span class="badge-new">NEW v14.0</span></h1>

<h2>Overview</h2>
<p>Any logged-in user can change the page background colour for their current session using a
colour picker in the sidebar. Text, surface, and border colours are automatically derived
from the chosen background to ensure readability.</p>

<h2>How to Set a Custom Background</h2>
<ol>
<li>Log in and look at the left sidebar</li>
<li>Find the <strong>&#127912; Background color</strong> expander and click to expand it</li>
<li>Check the <strong>Use custom background</strong> checkbox &mdash; a colour picker appears</li>
<li>Choose any colour using the picker</li>
<li>The page background updates immediately with auto-derived surface and text colours</li>
</ol>

<h2>Auto-Derived Colour Logic</h2>
<p>ClaudeOS uses the WCAG relative luminance formula to compute readability:</p>
<table>
<tr><th style="width:35%;">Background luminance</th><th>Derived text colour</th><th>Derived surface colour</th></tr>
<tr><td>Light background (luminance &gt; 0.5)</td>
    <td><code>#1A1A1A</code> (near-black)</td>
    <td>Slightly darker shade of background</td></tr>
<tr><td>Dark background (luminance &le; 0.5)</td>
    <td><code>#E8F5E8</code> (light green-white)</td>
    <td>Slightly lighter shade of background</td></tr>
</table>
<p>This ensures that regardless of the chosen colour, text remains readable and UI surfaces
remain visually distinct from the page background.</p>

<h2>Priority Order</h2>
<table>
<tr><th style="width:5%;">#</th><th style="width:25%;">Source</th><th>Notes</th></tr>
<tr><td>1</td><td>Personal override</td><td>Colour chosen by the user in the sidebar picker. Session-only.</td></tr>
<tr><td>2</td><td>Namespace default</td><td>Background colour set by admin in Admin &rarr; Branding. Persists for all namespace users.</td></tr>
<tr><td>3</td><td>Theme default</td><td>Standard dark/light theme background (&ldquo;Dim&rdquo; dark or white light).</td></tr>
</table>

<h2>Resetting to Default</h2>
<p>Uncheck <strong>Use custom background</strong> in the sidebar expander. The background
reverts to the namespace default (if set) or the current theme default.</p>

<h2>Session Scope</h2>
<p>Personal background colour choices are <strong>session-only</strong>. They reset when
you log out or close the browser. The namespace background (set by admin) persists permanently
until the admin changes it.</p>

<div class="tip"><strong>Accessibility tip:</strong> choose backgrounds with sufficient contrast
from your primary colour. Avoid mid-range greys that create ambiguity for both light-text and
dark-text rendering. Saturated pastels and deep rich tones tend to work best.</div>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 16 — ADVANCED FEATURES
# ═══════════════════════════════════════════════════════════════════════════════

def s16_advanced() -> str:
    return f"""
<h1><a name="s16"></a>16 &mdash; Advanced Features</h1>

<h2>Multi-Turn Conversation History</h2>
<p>Each agent in Chat mode maintains its own conversation session stored in the database.
Refreshing the page does not lose the conversation within the same session. Click
<strong>Clear Conversation</strong> when moving to a new topic to avoid stale context.</p>

<h2>Image and Screenshot Analysis</h2>
<p>In the Chat tab, attach any image file. The image is encoded as a base64 content block
and sent alongside your prompt to Claude's vision API. Practical uses:</p>
<ul>
<li>Summarise or critique a report screenshot</li>
<li>Interpret chart trends with the Analysis Agent</li>
<li>Quick UI compliance check with the QA Agent</li>
<li>Extract data from document photos</li>
</ul>

<h2>Voice Input</h2>
<p>Requires <code>pip install openai-whisper</code>. First use downloads ~140 MB model.
Subsequent starts are fast (model cached in memory). All transcription is done locally.</p>
<ol>
<li>Click the microphone button in the Chat tab</li>
<li>Record your request (up to 30 seconds recommended)</li>
<li>Review the transcription in the prompt field, edit if needed, then submit</li>
</ol>

<h2>Namespace Pulse Score</h2>
<p>The Pulse Score (shown on the Usage page for client/viewer roles) gives a 0&ndash;100
composite health indicator for a namespace.</p>
<div class="gauge-block">
<strong>Formula:</strong><br/>
&nbsp;&nbsp;(Average eval quality &divide; 5) &times; 100 &times; 0.40<br/>
&nbsp;&nbsp;+ (Ticket resolution rate) &times; 100 &times; 0.30<br/>
&nbsp;&nbsp;+ (Memory freshness score) &times; 100 &times; 0.20<br/>
&nbsp;&nbsp;+ (Workflow success rate) &times; 100 &times; 0.10<br/>
<br/>
<strong>Colour thresholds:</strong>
<span class="pill-green">&ge;75 Excellent/Good</span> &nbsp;
<span class="pill-amber">&ge;50 Fair</span> &nbsp;
<span class="pill-red">&lt;50 Needs Attention</span> &nbsp;
<span class="pill-gray">No data: Getting Started</span>
</div>

<h2>MCP Tool Server</h2>
<p>The Model Context Protocol (MCP) server exposes all 12 ClaudeOS agents as native tools
to any MCP-compatible AI client &mdash; Claude Desktop, Cursor, or custom agents.</p>
<pre>.\\scripts\\start_mcp.ps1     # starts on port 5100
curl http://localhost:5100/mcp  # verify it is running</pre>

<h3>Connecting Claude Desktop</h3>
<p>Add to <code>%APPDATA%\\Claude\\claude_desktop_config.json</code>:</p>
<pre>{{
  "mcpServers": {{
    "claudeos": {{
      "url": "http://localhost:5100/mcp"
    }}
  }}
}}</pre>
<p>Restart Claude Desktop. All 12 agents appear as available tools in the tool picker.</p>

<h2>A2A Agent Cards</h2>
<p>Each agent exposes a machine-readable capability card for agent-to-agent discovery:</p>
<pre>GET {API_URL}/api/v1/agents/writing-agent/.well-known/agent.json</pre>
<p>The card describes name, description, input/output schema, and streaming / multi-turn
capabilities. External AI orchestrators use this to auto-discover and delegate to ClaudeOS agents.</p>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 17 — API REFERENCE
# ═══════════════════════════════════════════════════════════════════════════════

def s17_api() -> str:
    return f"""
<h1><a name="s17"></a>17 &mdash; API Reference</h1>

<p>The ClaudeOS REST API runs at <strong>{API_URL}/api/v1/</strong>. All endpoints require
authentication (JWT Bearer or X-API-Key) except <code>/health</code> and webhook triggers.
Rate limits are enforced on all agent and workflow endpoints (see Section 6).</p>

<h2>Authentication</h2>

<h3>JWT (Interactive Users)</h3>
<pre># 1. Login
curl -X POST {API_URL}/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{{"username":"your_user","password":"your_pass"}}'

# Response
{{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {{"id": 1, "username": "your_user", "role": "operator"}}
}}

# 2. Use the access token
curl {API_URL}/api/v1/agents \\
  -H "Authorization: Bearer eyJ..."</pre>
<p>Access tokens expire after 60 minutes. Refresh:</p>
<pre>curl -X POST {API_URL}/api/v1/auth/refresh \\
  -H "Authorization: Bearer &lt;refresh_token&gt;"</pre>

<h3>API Key (Scripts and Automation)</h3>
<pre>curl {API_URL}/api/v1/memory \\
  -H "X-API-Key: your_api_key"</pre>

<h2>Core Endpoint Reference</h2>
<table>
<tr><th style="width:10%;">Method</th><th style="width:42%;">Endpoint</th><th>Description</th></tr>
<tr><td>POST</td><td><code>/auth/login</code></td><td>Login, returns access + refresh tokens</td></tr>
<tr><td>POST</td><td><code>/auth/refresh</code></td><td>Renew access token</td></tr>
<tr><td>POST</td><td><code>/auth/logout</code></td><td>Revoke current session</td></tr>
<tr><td>GET</td><td><code>/auth/me</code></td><td>Current user info and role</td></tr>
<tr><td>GET</td><td><code>/health</code></td><td>Public health check (no auth)</td></tr>
<tr><td>GET</td><td><code>/memory</code></td><td>List memory entries (filterable)</td></tr>
<tr><td>POST</td><td><code>/memory</code></td><td>Write a memory entry</td></tr>
<tr><td>DELETE</td><td><code>/memory/&lt;id&gt;</code></td><td>Delete a memory entry</td></tr>
<tr><td>GET</td><td><code>/memory/hybrid-search</code></td><td>Hybrid BM25+vector search with RRF reranking</td></tr>
<tr><td>POST</td><td><code>/memory/consolidate</code></td><td>Trigger memory consolidation immediately</td></tr>
<tr><td>GET</td><td><code>/agents</code></td><td>List all registered agents</td></tr>
<tr><td>POST</td><td><code>/agents/&lt;name&gt;/run</code></td><td>Dispatch async agent run &mdash; 30/min limit</td></tr>
<tr><td>GET</td><td><code>/agents/runs/&lt;id&gt;</code></td><td>Poll run status and output</td></tr>
<tr><td>GET</td><td><code>/agents/runs</code></td><td>List all runs (filterable)</td></tr>
<tr><td>GET</td><td><code>/agents/&lt;name&gt;/stream</code></td><td>SSE streaming &mdash; 20/min limit</td></tr>
<tr><td>GET</td><td><code>/agents/&lt;name&gt;/.well-known/agent.json</code></td><td>A2A Agent Card</td></tr>
<tr><td>GET</td><td><code>/outputs</code></td><td>List outputs</td></tr>
<tr><td>DELETE</td><td><code>/outputs/bulk</code></td><td>Bulk delete outputs</td></tr>
<tr><td>GET</td><td><code>/tickets</code></td><td>List tickets</td></tr>
<tr><td>POST</td><td><code>/tickets</code></td><td>Create a ticket (triggers email if configured)</td></tr>
<tr><td>PUT</td><td><code>/tickets/&lt;id&gt;</code></td><td>Update ticket (triggers email on resolve/close)</td></tr>
<tr><td>DELETE</td><td><code>/tickets/bulk</code></td><td>Bulk delete tickets</td></tr>
<tr><td>GET</td><td><code>/tickets/stats</code></td><td>Ticket counts by status and priority</td></tr>
<tr><td>GET</td><td><code>/workflows</code></td><td>List workflows</td></tr>
<tr><td>POST</td><td><code>/workflows/&lt;name&gt;/run</code></td><td>Trigger workflow (JWT required)</td></tr>
<tr><td>POST</td><td><code>/workflows/&lt;name&gt;/trigger</code></td><td>Webhook trigger (X-Webhook-Secret, 10/min limit)</td></tr>
<tr><td>POST</td><td><code>/workflows/&lt;name&gt;/webhook/enable</code></td><td>Enable webhook, generate secret</td></tr>
<tr><td>GET</td><td><code>/system/status</code></td><td>System health detail</td></tr>
<tr><td>GET</td><td><code>/system/namespace-stats</code></td><td>Per-namespace KPIs for Usage dashboard</td></tr>
<tr><td>GET</td><td><code>/admin/branding/&lt;namespace&gt;</code></td><td>Get namespace branding config (admin)</td></tr>
<tr><td>PUT</td><td><code>/admin/branding/&lt;namespace&gt;</code></td><td>Update namespace branding (admin)</td></tr>
</table>

<h2>Async Run &mdash; Full Example</h2>
<pre># Dispatch
curl -X POST {API_URL}/api/v1/agents/writing-agent/run \\
  -H "Authorization: Bearer &lt;token&gt;" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "prompt": "Write a 1-page executive summary of Q2 results",
    "namespace": "my-namespace",
    "save_output": true
  }}'

# Response 202
{{"run_id": "abc123", "status": "pending", "poll_url": "/api/v1/agents/runs/abc123"}}

# Poll until done
curl {API_URL}/api/v1/agents/runs/abc123 -H "Authorization: Bearer &lt;token&gt;"

# Response when complete
{{
  "run_id": "abc123", "status": "done",
  "output": "Q2 Executive Summary\\n...",
  "tokens_in": 1420, "tokens_out": 380, "eval_score": 4.2
}}</pre>

<h2>SSE Streaming &mdash; Full Example</h2>
<pre>curl -N "{API_URL}/api/v1/agents/writing-agent/stream?prompt=Hello&amp;namespace=my-ns" \\
  -H "X-API-Key: your_api_key"

data: {{"type": "token", "text": "Hello"}}
data: {{"type": "token", "text": " there"}}
data: {{"type": "done", "run_id": "xyz", "tokens_in": 900, "tokens_out": 12}}
data: {{"type": "error", "message": "Rate limit exceeded"}}</pre>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 18 — SECURITY MODEL
# ═══════════════════════════════════════════════════════════════════════════════

def s18_security() -> str:
    return """
<h1><a name="s18"></a>18 &mdash; Security Model</h1>

<h2>Authentication</h2>
<table>
<tr><th style="width:28%;">Mechanism</th><th>Details</th></tr>
<tr><td>JWT access tokens</td>
    <td>60-minute TTL. Silently refreshed while active. Never stored in plaintext.</td></tr>
<tr><td>Refresh tokens</td>
    <td>7-day TTL. Stored as SHA-256 hash. Revokable per-session from Admin Panel.</td></tr>
<tr><td>API keys</td>
    <td>For scripts and automation. Created in Admin Panel. Shown once. Stored as hash.</td></tr>
<tr><td>Webhook secrets</td>
    <td>32-byte random hex, compared using HMAC constant-time comparison (timing-attack safe).</td></tr>
</table>

<h2>Password Policy</h2>
<ul>
<li>Minimum 10 characters; at least one uppercase, one lowercase, one digit</li>
<li>Hashed with bcrypt (12 rounds) &mdash; never stored in plaintext</li>
<li>Admin can force password change on next login per user</li>
</ul>

<h2>Account Lockout</h2>
<p>5 consecutive failed login attempts triggers a 15-minute lockout. Configurable via
<strong>Admin Panel &rarr; Security</strong>. Admin can manually unlock immediately from
<strong>Admin Panel &rarr; Users</strong>.</p>

<h2>CORS Restriction <span class="badge-new">NEW v14.0</span></h2>
<p>The Flask API enforces Cross-Origin Resource Sharing (CORS) restrictions. Only origins
listed in the <code>ALLOWED_ORIGINS</code> environment variable are permitted to make
cross-origin requests. Default: <code>http://localhost:8501</code>.</p>
<pre># .env
ALLOWED_ORIGINS=http://localhost:8501,https://your-dashboard.company.com</pre>
<p>Requests from unlisted origins receive a <code>403 Forbidden</code> response at the
CORS preflight stage, before any authentication is checked.</p>

<h2>Rate Limiting <span class="badge-new">NEW v14.0</span></h2>
<table>
<tr><th style="width:35%;">Endpoint</th><th>Limit</th><th>Response on breach</th></tr>
<tr><td>Agent <code>/run</code></td><td>30 / minute per IP</td><td>429 Too Many Requests</td></tr>
<tr><td>Agent <code>/stream</code></td><td>20 / minute per IP</td><td>429 Too Many Requests</td></tr>
<tr><td>Workflow <code>/trigger</code></td><td>10 / minute per IP</td><td>429 Too Many Requests</td></tr>
</table>

<h2>Security Response Headers <span class="badge-new">NEW v14.0</span></h2>
<p>All API responses include the following security headers:</p>
<table>
<tr><th style="width:40%;">Header</th><th>Value</th></tr>
<tr><td><code>X-Content-Type-Options</code></td><td><code>nosniff</code></td></tr>
<tr><td><code>X-Frame-Options</code></td><td><code>DENY</code></td></tr>
<tr><td><code>X-XSS-Protection</code></td><td><code>1; mode=block</code></td></tr>
</table>

<h2>Namespace Isolation</h2>
<p>Client and Viewer role users are hard-scoped to their assigned namespace. Every API
endpoint enforces namespace access in the application layer &mdash; a client user cannot
read, write, or search memory from another namespace regardless of API parameters sent.</p>

<h2>Namespace KPI Scoping <span class="badge-new">NEW v14.0</span></h2>
<p>Overview KPIs and Usage dashboard data are now filtered by the logged-in user's namespace
for client and viewer roles. Admin and Operator continue to see global counts. This prevents
information leakage across namespaces in shared dashboard views.</p>

<h2>Audit Log</h2>
<p>Every significant action is recorded: login success/failure, lockout, logout, token refresh,
user creation/deactivation/password reset, API key creation/revocation.</p>
<p>View in <strong>Admin Panel &rarr; Audit Log</strong>. Each entry records event type,
username, IP address, user agent, and timestamp.</p>

<h2>Admin Panel Controls</h2>
<table>
<tr><th style="width:25%;">Control</th><th>What It Does</th></tr>
<tr><td>Users</td><td>Create, deactivate, unlock, and reset passwords.</td></tr>
<tr><td>API Keys</td><td>Create and revoke API keys. Raw key shown once.</td></tr>
<tr><td>Sessions</td><td>View all active refresh token sessions. Revoke any immediately.</td></tr>
<tr><td>Security Config</td><td>Lockout threshold/duration, token TTLs, self-registration toggle.</td></tr>
<tr><td>Audit Log</td><td>Paginated full event log with filtering.</td></tr>
<tr><td>Branding</td><td>Per-namespace company name, colours, icon, background (see Sec 14).</td></tr>
</table>

<h2>What ClaudeOS Does NOT Store</h2>
<ul>
<li>Plaintext passwords &mdash; only bcrypt hashes</li>
<li>Raw refresh tokens &mdash; only SHA-256 hashes</li>
<li>Raw API keys beyond the initial response &mdash; only hashes</li>
<li>Anthropic API key in the database &mdash; only in the server's <code>.env</code></li>
</ul>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 19 — CLOUD SYNC
# ═══════════════════════════════════════════════════════════════════════════════

def s19_sync() -> str:
    return """
<h1><a name="s19"></a>19 &mdash; Cloud Sync (Supabase)</h1>

<h2>Overview</h2>
<p>ClaudeOS can sync outputs and memory entries to a Supabase PostgreSQL database for
cloud backup and off-site storage. Sync is push-only &mdash; SQLite on your server is
always the source of truth. Supabase is a mirror.</p>

<h2>Setup</h2>
<ol>
<li>Create a free account at <strong>supabase.com</strong> and create a new project</li>
<li>In the Supabase SQL Editor, run <code>sync/supabase_schema.sql</code></li>
<li>Copy your Supabase project URL and service role key from project settings (API section)</li>
<li>Add to <code>.env</code>:
<pre>SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key</pre></li>
<li>Restart the server &mdash; auto-sync starts, firing every 15 minutes</li>
</ol>

<h2>Manual Sync</h2>
<p>Go to <strong>Settings</strong> &rarr; click <strong>Sync Now</strong> to push immediately.</p>

<h2>What Is Synced</h2>
<ul>
<li>Memory entries</li>
<li>Agent runs and outputs</li>
<li>Namespaces and projects</li>
<li>System events</li>
</ul>

<div class="note"><strong>Note:</strong> Auth data (users, sessions, passwords) is
<em>not</em> synced to Supabase. It stays on your server only.</div>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 20 — TROUBLESHOOTING & SUPPORT
# ═══════════════════════════════════════════════════════════════════════════════

def s20_troubleshoot_support() -> str:
    return f"""
<h1><a name="s20"></a>20 &mdash; Troubleshooting &amp; Support</h1>

<h2>Common Problems and Fixes</h2>
<table>
<tr><th style="width:33%;">Problem</th><th>Solution</th></tr>
<tr><td>Cannot reach the dashboard</td>
    <td>Run <code>.\\scripts\\start.ps1</code>. Check ports 5000 and 8501. Verify no firewall blocks them.</td></tr>
<tr><td>Login fails</td>
    <td>Login is case-insensitive for username. After 5 failures, wait 15 minutes or ask admin to unlock.</td></tr>
<tr><td>&ldquo;Must change password&rdquo; shown</td>
    <td>Enter current password then your new password in the prompt.</td></tr>
<tr><td>API returns 401 Unauthorized</td>
    <td>Access token expired. Log out and back in. If using API key, verify it is not revoked.</td></tr>
<tr><td>API returns 403 Forbidden</td>
    <td>Check <code>ALLOWED_ORIGINS</code> in <code>.env</code> includes your dashboard URL (CORS).</td></tr>
<tr><td>API returns 429 Too Many Requests</td>
    <td>You have exceeded the rate limit. Wait 60 seconds before retrying.</td></tr>
<tr><td>Agent runs are slow</td>
    <td>Expected for long responses (~40 tokens/second). Check latency in Observability.</td></tr>
<tr><td>Eval scores not appearing</td>
    <td>Wait 10&ndash;15 seconds after run completes. Scores are async. Check logs for Haiku eval errors.</td></tr>
<tr><td>Streaming returns an error</td>
    <td>Ensure only one Flask process is running on port 5000. Restart with <code>.\\scripts\\start.ps1</code>.</td></tr>
<tr><td>Voice input not working</td>
    <td>Run <code>pip install openai-whisper</code>. First use downloads ~140 MB &mdash; wait for completion.</td></tr>
<tr><td>MCP server not found</td>
    <td>Run <code>pip install mcp uvicorn</code> then <code>.\\scripts\\start_mcp.ps1</code>.</td></tr>
<tr><td>Runs stuck as &ldquo;running&rdquo;</td>
    <td>Restart the server. Stuck runs are auto-cleaned on the next health check.</td></tr>
<tr><td>Agents not responding</td>
    <td>Check <code>ANTHROPIC_API_KEY</code> in <code>.env</code>. Verify not expired in Anthropic console.</td></tr>
<tr><td>ChromaDB slow on first start</td>
    <td>Normal &mdash; sentence-transformers model loads on first request (30&ndash;60 second cold start).</td></tr>
<tr><td>Ticket email notifications not sending</td>
    <td>Verify SMTP settings in Settings &rarr; Email Notifications. Use Test Send button to debug.
    Gmail requires an App Password, not your account password.</td></tr>
<tr><td>Ticket comments not loading</td>
    <td>Click the <strong>Comments</strong> toggle &mdash; comments load on demand.</td></tr>
<tr><td>Supabase sync fails</td>
    <td>Verify <code>SUPABASE_URL</code> and <code>SUPABASE_SERVICE_KEY</code>. Restart after changes.</td></tr>
<tr><td>Output PDF export fails</td>
    <td>Try Markdown export instead. PDF export requires wkhtmltopdf installed on the server.</td></tr>
<tr><td>Memory entries not in agent context</td>
    <td>Entries may be archived or expired. Check Memory page with all filters cleared.
    Verify namespace matches between memory write and agent run.</td></tr>
<tr><td>Namespace branding not appearing</td>
    <td>Confirm branding was saved in Admin &rarr; Branding. Log out and back in to force a brand refresh.</td></tr>
<tr><td>Background colour not applying</td>
    <td>Ensure &ldquo;Use custom background&rdquo; checkbox is checked in sidebar expander.
    Note: session-only &mdash; resets on logout.</td></tr>
<tr><td>Onboarding modal not showing</td>
    <td>Modal only shows once per account (persisted via <code>onboarding_done</code> DB column, migration 018).
    Admin accounts skip the onboarding tour. If the tour should re-appear, reset with:
    <code>UPDATE users SET onboarding_done=0 WHERE username='...'</code></td></tr>
<tr><td>Onboarding shows every login (not persisting)</td>
    <td>Migration 018 may not be applied. Run <code>python scripts/migrate.py</code>.
    Also verify <code>POST /auth/onboarding-done</code> is called on skip/complete in
    <code>dashboard/components/onboarding.py</code>.</td></tr>
<tr><td>Voice input widget not clearing after conversation reset</td>
    <td>The <code>st.audio_input</code> session state key must be reset alongside conversation history.
    Verify <code>dashboard/_pages/_agents.py</code> clears the audio key on Clear Conversation click.</td></tr>
<tr><td>Images not received by agent in chat</td>
    <td>The SSE stream endpoint must forward the <code>images=</code> parameter to <code>execute_stream()</code>.
    Verify <code>core/api/routes/agents.py</code> <code>stream_agent()</code> passes images through.</td></tr>
<tr><td>Admin Unlock button always visible (not context-aware)</td>
    <td>The Unlock button should only appear when the user is actually locked.
    Verify <code>dashboard/_pages/_admin.py</code> checks <code>locked_until</code> before rendering the button.</td></tr>
<tr><td>Namespace Usage tab not showing data</td>
    <td>Requires at least one agent run to exist. Zero values are normal for new deployments.
    Tab is only visible to Admin and Operator roles.</td></tr>
<tr><td>Client Onboarding tab missing in Admin Panel</td>
    <td>Run <code>python scripts/seed_client_schema.py --namespace &lt;slug&gt;</code> to seed blank fields.
    The tab is in Admin Panel (6th tab) &mdash; visible to Admin role only.</td></tr>
<tr><td>Output delete button does nothing</td>
    <td>SQLite versions older than 3.35 do not support the RETURNING clause.
    Upgrade SQLite or update <code>outputs/manager.py</code> to use SELECT-then-DELETE pattern.</td></tr>
<tr><td>Output timestamps show date only (no time)</td>
    <td>Upgrade to v16.0. Timestamps now display as YYYY-MM-DD HH:MM in all output views.</td></tr>
<tr><td>Activity feed shows garbled IDs instead of agent names</td>
    <td>Upgrade to v16.0. The dispatcher now JOINs the agents table so human-readable names
    are always returned. If on latest version, check <code>agents/dispatcher.py</code>
    <code>list_runs()</code> includes the JOIN clause.</td></tr>
<tr><td>Agent gives confident wrong answers when no data is supplied</td>
    <td>This is the hallucination guard working correctly after v16.0. The agents
    (analysis, briefing, research, writing) will now ask you for specific inputs
    rather than generating fabricated content. Supply the requested data and re-run.</td></tr>
<tr><td>Agent response slow when ChromaDB is indexing</td>
    <td>After v16.0 a 4-second timeout protects against slow ChromaDB/hybrid-search.
    The agent falls back to fast FTS context automatically. Performance warning may appear in logs
    &mdash; this is informational, not an error.</td></tr>
<tr><td>Page not preserved after browser refresh</td>
    <td>Ensure you are on the latest v14.0. The URL should show <code>?page=PageName</code>.
    Clear browser cache if the behaviour persists.</td></tr>
<tr><td>Pulse Score shows &ldquo;Getting Started&rdquo;</td>
    <td>Normal for new namespaces. The score appears once there are agent runs, tickets, and memory entries.</td></tr>
</table>

<h2>Contact Your Administrator</h2>
<table>
<tr><th style="width:25%;">Detail</th><th>Value</th></tr>
<tr><td>Name</td><td>{ADMIN_NAME}</td></tr>
<tr><td>Email</td><td>{ADMIN_EMAIL}</td></tr>
<tr><td>Phone</td><td>{ADMIN_PHONE}</td></tr>
<tr><td>Dashboard URL</td><td><code>{SYSTEM_URL}</code></td></tr>
</table>

<h2>Before Contacting Support</h2>
<ol>
<li>Check this section for your exact error</li>
<li>Note the error message shown in the dashboard or browser</li>
<li>Note what you were doing (which page, which agent, which prompt)</li>
<li>Note whether the error is reproducible</li>
<li>Check Observability for any system-wide alerts</li>
</ol>

<h2>Useful Information to Provide</h2>
<ul>
<li>Your username and role</li>
<li>Your namespace</li>
<li>The run ID (visible in Run History) if the issue is with a specific agent run</li>
<li>Approximate time the issue occurred</li>
</ul>

"""


# ═══════════════════════════════════════════════════════════════════════════════
# ASSEMBLE AND RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_html() -> str:
    body = "".join([
        cover_page(),
        toc(),
        s1_intro(),
        s2_requirements(),
        s3_install(),
        s4_login(),
        s5_dashboard(),
        s6_agents(),
        s7_memory(),
        s8_workflows(),
        s9_vault(),
        s10_outputs(),
        s11_tickets(),
        s12_quality(),
        s13_observability(),
        s14_branding(),
        s15_bgcolor(),
        s16_advanced(),
        s17_api(),
        s18_security(),
        s19_sync(),
        s20_troubleshoot_support(),
    ])
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>ClaudeOS v{VERSION} &mdash; Client Handbook &mdash; {CLIENT}</title>
  <style>{CSS}</style>
</head>
<body>
<div id="footer_content">ClaudeOS v{VERSION} &nbsp;&#183;&nbsp; faiyke-ai &nbsp;&#183;&nbsp; Page <pdf:pagenumber> of <pdf:pagecount> &nbsp;&#183;&nbsp; Confidential</div>
{body}
</body>
</html>"""


if __name__ == "__main__":
    out_path = Path(f"docs/ClaudeOS_Handbook_{CLIENT}.pdf")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Building ClaudeOS v{VERSION} Handbook HTML ...")
    html = build_html()

    print(f"Rendering PDF -> {out_path} ...")
    with open(out_path, "wb") as f:
        result = pisa.CreatePDF(io.StringIO(html), dest=f)

    if result.err:
        print(f"PDF errors: {result.err}")
    else:
        size_kb = out_path.stat().st_size // 1024
        print(f"Done: {out_path} ({size_kb} KB)")
