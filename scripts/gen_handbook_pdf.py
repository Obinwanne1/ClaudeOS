"""
Generate ClaudeOS_Handbook_faiyke-ai.pdf
Full client-facing handbook for faiyke-ai.
Usage: python scripts/gen_handbook_pdf.py
"""
import io
from datetime import date
from pathlib import Path
from xhtml2pdf import pisa

VERSION = "13.1"
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
@page cover  { size: A4; margin: 0; }
@page normal { size: A4; margin: 2.2cm 2cm 2.2cm 2cm; }
@page        { size: A4; margin: 2.2cm 2cm 2.8cm 2cm;
               @frame footer_frame {
                 -pdf-frame-content: footer_content;
                 bottom: 0.6cm; left: 2cm; right: 2cm; height: 0.8cm;
               }
             }

body { font-family: Arial, sans-serif; font-size: 10.5pt; color: #1a1a1a; line-height: 1.7; }

/* ── headings ── */
h1 { color: #407E3C; font-size: 20pt; border-bottom: 3px solid #407E3C;
     padding-bottom: 8px; margin-top: 32px; page-break-before: always; }
h1.no-break { page-break-before: avoid; margin-top: 0; }
h2 { color: #407E3C; font-size: 14pt; border-bottom: 1px solid #5a9e56;
     padding-bottom: 4px; margin-top: 26px; }
h3 { color: #2d5a29; font-size: 11.5pt; margin-top: 16px; margin-bottom: 4px; }
h4 { color: #2d5a29; font-size: 10.5pt; margin-top: 10px; margin-bottom: 2px; }

/* ── tables ── */
table { width: 100%; border-collapse: collapse; margin: 12px 0;
        font-size: 9.5pt; table-layout: fixed; }
th   { background: #407E3C; color: #fff; padding: 7px 10px;
       text-align: left; word-wrap: break-word; }
td   { padding: 6px 10px; border-bottom: 1px solid #d0e8c8;
       vertical-align: top; word-wrap: break-word; }
tr:nth-child(even) td { background: #f4faf2; }

/* ── code ── */
code { background: #f0f0f0; padding: 1px 5px;
       font-family: "Courier New", monospace; font-size: 8.5pt;
       word-break: break-all; }
pre  { background: #f4faf2; border-left: 4px solid #407E3C;
       padding: 10px 14px; font-family: "Courier New", monospace;
       font-size: 8pt; white-space: pre-wrap; word-wrap: break-word;
       margin: 10px 0; }

/* ── lists ── */
ul, ol { margin: 6px 0; padding-left: 22px; }
li     { margin: 3px 0; }

/* ── misc ── */
hr     { border: none; border-top: 1px solid #c8e0c0; margin: 20px 0; }
strong { color: #2d5a29; }
p      { margin: 6px 0 10px 0; }

/* ── callout boxes ── */
.note  { background: #f0f9ee; border-left: 4px solid #407E3C;
         padding: 10px 14px; margin: 12px 0; font-size: 10pt; }
.warn  { background: #fff8e1; border-left: 4px solid #f9a825;
         padding: 10px 14px; margin: 12px 0; font-size: 10pt; }
.tip   { background: #e8f5e9; border-left: 4px solid #5a9e56;
         padding: 10px 14px; margin: 12px 0; font-size: 10pt; }

/* ── cover ── */
.cover { background: #407E3C; width: 100%; padding: 80px 60px 60px 60px;
         color: white; }
.cover-title  { font-size: 34pt; font-weight: bold; color: white;
                margin-bottom: 6px; letter-spacing: 1px; }
.cover-sub    { font-size: 16pt; color: #c8e0c0; margin-bottom: 40px; }
.cover-client { font-size: 13pt; color: white; margin-bottom: 6px; }
.cover-meta   { font-size: 10pt; color: #a8d4a0; margin-top: 60px; }
.cover-line   { border-top: 1px solid #5a9e56; margin: 20px 0; }

/* ── section badge ── */
.badge { background: #407E3C; color: white; padding: 2px 9px;
         font-size: 8.5pt; margin-right: 5px; }
.badge-gray { background: #888; color: white; padding: 2px 9px;
              font-size: 8.5pt; margin-right: 5px; }

/* ── pill ── */
.pill-green { background:#2e7d32; color:white; padding:1px 7px; font-size:8pt; }
.pill-amber { background:#f57f17; color:white; padding:1px 7px; font-size:8pt; }
.pill-red   { background:#c62828; color:white; padding:1px 7px; font-size:8pt; }

/* ── page header bar ── */
.header-bar { background: #407E3C; color: white; padding: 14px 20px;
              margin: -2.2cm -2cm 22px -2cm; }

/* ── page footer ── */
#footer_content { text-align: center; font-size: 8.5pt; color: #888;
                  font-family: Arial, sans-serif; }
"""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def header_bar(title: str, subtitle: str = "") -> str:
    sub = f"<span style='float:right;color:#c8e0c0;font-size:9.5pt;'>{subtitle}</span>" if subtitle else ""
    return f'<div class="header-bar"><strong style="font-size:13pt;">{title}</strong>{sub}</div>'


def cover_page() -> str:
    return f"""
<div class="cover">
  <div class="cover-title">ClaudeOS</div>
  <div class="cover-sub">AI Operating System — Client Handbook</div>
  <div class="cover-line"></div>
  <div class="cover-client"><strong>Prepared for:</strong> {CLIENT}</div>
  <div class="cover-client"><strong>Version:</strong> {VERSION} &nbsp;·&nbsp; {TODAY}</div>
  <div class="cover-meta">
    Confidential — For authorised users of ClaudeOS only.<br/>
    Do not distribute outside your organisation.
  </div>
</div>
"""


def toc() -> str:
    entries = [
        ("1",  "s1",  "Introduction",               "What ClaudeOS Is and What It Does"),
        ("2",  "s2",  "System Requirements",         "Hardware, Software, and Network"),
        ("3",  "s3",  "Installation &amp; First-Run Setup", "From Zero to Running in 15 Minutes"),
        ("4",  "s4",  "Logging In",                  "Authentication, Roles, and Password Rules"),
        ("5",  "s5",  "Dashboard Tour",               "Every Page Explained"),
        ("6",  "s6",  "Working with AI Agents",       "Chat, Catalog, Run History"),
        ("7",  "s7",  "Memory System",                "How ClaudeOS Remembers Things"),
        ("8",  "s8",  "Workflows &amp; Automation",   "Pipelines, Scheduling, Webhooks"),
        ("9",  "s9",  "Client Vault",                 "Namespaces, Projects, Context Files"),
        ("10", "s10", "Outputs &amp; Reports",        "Saving, Searching, Exporting"),
        ("11", "s11", "Ticketing System",             "Support and Task Lifecycle"),
        ("12", "s12", "Quality Scoring",              "LLM-as-Judge Automatic Evaluation"),
        ("13", "s13", "Observability",                "Performance, Latency, Token Cost"),
        ("14", "s14", "Advanced Features",            "Images, Voice, MCP, A2A"),
        ("15", "s15", "API Reference",                "REST API for Developers"),
        ("16", "s16", "Security Model",               "Auth, Isolation, Audit Log"),
        ("17", "s17", "Cloud Sync",                   "Supabase Backup"),
        ("18", "s18", "Troubleshooting",              "Common Problems and Fixes"),
        ("19", "s19", "Support",                      "How to Get Help"),
    ]
    rows = "".join(
        f"<tr>"
        f"<td style='width:8%;color:#407E3C;font-weight:bold;'>{n}</td>"
        f"<td style='width:30%;'><a href='#{anchor}' style='color:#407E3C;text-decoration:none;'>"
        f"<strong>{title}</strong></a></td>"
        f"<td style='color:#555;'>{desc}</td>"
        f"</tr>"
        for n, anchor, title, desc in entries
    )
    return f"""
<h1 class="no-break">Contents</h1>
<table>
<tr><th style="width:8%;">#</th><th style="width:30%;">Section</th><th>What You Will Find</th></tr>
{rows}
</table>
"""


def s1_intro() -> str:
    return """
<h1><a name="s1"></a>1 — Introduction</h1>
{hdr}

<h2>What Is ClaudeOS?</h2>
<p>ClaudeOS is an AI Operating System — a secure, multi-user coordination layer that brings
together AI agents, a long-term memory engine, automated workflows, project management, and
a full ticketing system into one authenticated control centre. It runs as a private web
application on your own infrastructure, so your data never leaves your environment.</p>

<p>Think of it as a team of 12 specialist AI assistants, all sharing the same memory, working
from the same context, and all governed by the same security and quality rules — accessible
from any browser.</p>

<h2>Core Capabilities</h2>
<table>
<tr><th style="width:28%;">Capability</th><th>What It Does for You</th></tr>
<tr><td><strong>AI Agents</strong></td>
    <td>12 specialist agents covering research, writing, analysis, scheduling, QA, client
    management, comms, and more. Run them via chat, one-shot dispatch, or automated pipeline.</td></tr>
<tr><td><strong>Long-Term Memory</strong></td>
    <td>Every fact, preference, reminder, and task you store is available to every agent.
    Memory persists between sessions and is scoped per namespace so each client or project
    only sees its own data.</td></tr>
<tr><td><strong>Workflow Automation</strong></td>
    <td>7 built-in pipelines (morning briefing, memory curation, research digest, client
    report, analysis run, QA sweep, meta-orchestration) that run on a schedule or on
    demand.</td></tr>
<tr><td><strong>Ticketing</strong></td>
    <td>Full support and task lifecycle — create, assign, prioritise, comment, resolve, and
    bulk-manage tickets without leaving ClaudeOS.</td></tr>
<tr><td><strong>Quality Scoring</strong></td>
    <td>Every agent response is automatically scored on 4 dimensions by a fast AI judge.
    Low-quality runs are flagged before they reach your workflow.</td></tr>
<tr><td><strong>Observability</strong></td>
    <td>Real-time dashboards for response quality, latency, token spend, and memory health
    — so you always know how the system is performing.</td></tr>
</table>

<h2>Architecture at a Glance</h2>
<pre>Browser  ──►  Streamlit Dashboard  (:8501)
                      │
              Login Gate (JWT)
                      │
              Flask REST API  (:5000)
              ├─ Auth &amp; Roles
              ├─ Agent Dispatcher
              ├─ Memory Engine  (SQLite FTS5 + ChromaDB)
              ├─ Workflow Scheduler  (APScheduler)
              ├─ Output Manager
              ├─ Ticketing
              └─ Observability

Optional:  MCP Tool Server  (:5100)  — exposes agents to external AI clients</pre>

<div class="note"><strong>Note:</strong> ClaudeOS runs entirely on your own server. No agent
prompts, memory entries, or outputs are sent to any third party except the Anthropic Claude
API (for agent inference) and optionally Supabase (for cloud backup, if you choose to enable
it).</div>
""".format(hdr=header_bar("ClaudeOS — AI Operating System", f"v{VERSION} · {TODAY}"))


def s2_requirements() -> str:
    return """
<h1><a name="s2"></a>2 — System Requirements</h1>

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
<tr><td>Supabase (optional)</td>
    <td>Cloud backup of memory and outputs.</td>
    <td>Free tier available</td></tr>
</table>

<div class="warn"><strong>Important:</strong> Keep your <code>ANTHROPIC_API_KEY</code>
secure. Never share it. If it is compromised, rotate it immediately in the Anthropic
console and update your <code>.env</code> file.</div>
"""


def s3_install() -> str:
    return f"""
<h1><a name="s3"></a>3 — Installation &amp; First-Run Setup</h1>

<h2>Step 1 — Get the Code</h2>
<p>Copy the ClaudeOS project folder to your server. You should have a folder named
<code>ClaudeOS</code> with the following top-level layout:</p>
<pre>ClaudeOS/
├─ agents/
├─ core/
├─ dashboard/
├─ docs/
├─ memory/
├─ mcp/
├─ scripts/
├─ workflows/
├─ requirements.txt
└─ .env.example</pre>

<h2>Step 2 — Create Your Environment File</h2>
<p>Copy <code>.env.example</code> to <code>.env</code> and fill in your values:</p>
<pre># .env
ANTHROPIC_API_KEY=sk-ant-...           # required
FLASK_SECRET_KEY=change-this-secret    # any long random string
FLASK_PORT=5000
STREAMLIT_PORT=8501

# Optional — Supabase cloud backup
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key</pre>

<div class="warn"><strong>Never commit <code>.env</code> to version control.</strong> It
contains secrets. The <code>.gitignore</code> already excludes it.</div>

<h2>Step 3 — Install Python Dependencies</h2>
<pre>pip install -r requirements.txt</pre>
<p>This installs Flask, Streamlit, the Anthropic SDK, ChromaDB, sentence-transformers,
APScheduler, waitress, plotly, PyJWT, bcrypt, and all other required packages.</p>
<p>For optional features:</p>
<pre># Voice input (downloads ~140 MB model on first use)
pip install openai-whisper

# MCP Tool Server (for external AI client integration)
pip install mcp uvicorn</pre>

<h2>Step 4 — Initialise the Database</h2>
<pre>python scripts/migrate.py</pre>
<p>Creates <code>data/claudeos.db</code> with all tables including auth, memory, agents,
workflows, tickets, and observability columns.</p>

<h2>Step 5 — Seed Default Data</h2>
<pre>python scripts/seed_agents.py       # loads 12 agent definitions
python scripts/seed_workflows.py    # loads 7 default pipelines
python scripts/seed_namespaces.py   # creates the global namespace</pre>

<h2>Step 6 — Create the Admin Account</h2>
<pre>python scripts/create_admin.py --username admin --password Admin123!</pre>
<div class="warn">Use a strong password. Password rules: minimum 10 characters, at least
one uppercase, one lowercase, one digit.</div>

<h2>Step 7 — Start the System</h2>
<pre>.\\scripts\\start.ps1</pre>
<p>This script kills any existing processes on ports 5000 and 8501, starts the Flask API
via waitress, verifies <code>/health</code>, then starts the Streamlit dashboard.</p>

<p>After 5–10 seconds, open your browser to <strong>{SYSTEM_URL}</strong> — you should
see the ClaudeOS login screen.</p>

<h2>Optional — Start the MCP Server</h2>
<pre>.\\scripts\\start_mcp.ps1</pre>
<p>Starts the MCP Tool Server on port 5100. Only needed if you want to connect Claude
Desktop or other MCP-compatible AI clients to ClaudeOS agents.</p>

<h2>Stopping the System</h2>
<p>Close the PowerShell windows running the API and dashboard, or kill the processes on
ports 5000 and 8501:</p>
<pre>netstat -ano | findstr :5000   # get PID
taskkill /F /PID &lt;PID&gt;         # kill it
# repeat for 5001, 8501</pre>

<div class="tip"><strong>After any change to <code>.env</code>:</strong> always restart the
server. Running processes do not pick up environment changes automatically.</div>
"""


def s4_login() -> str:
    return """
<h1><a name="s4"></a>4 — Logging In</h1>

<h2>First Login</h2>
<p>Navigate to the dashboard URL in your browser. You will see the ClaudeOS login screen
with two tabs: <strong>Login</strong> and <strong>Register</strong>.</p>

<p>Enter the username and temporary password provided by your administrator, then press
<strong>Enter</strong> or click <strong>Login</strong>. If the admin set the
<em>must change password</em> flag on your account, you will be prompted to set a new
password immediately before continuing.</p>

<h2>Password Requirements</h2>
<ul>
<li>Minimum 10 characters</li>
<li>At least one uppercase letter (A–Z)</li>
<li>At least one lowercase letter (a–z)</li>
<li>At least one digit (0–9)</li>
</ul>

<h2>Self-Registration (if enabled)</h2>
<p>If your admin has enabled self-registration:</p>
<ol>
<li>Click the <strong>Register</strong> tab on the login screen</li>
<li>Enter username, email, password, and select your namespace</li>
<li>Click <strong>Register</strong> — you are returned to the Login tab</li>
<li>Log in with your new credentials</li>
</ol>

<h2>User Roles</h2>
<table>
<tr><th style="width:15%;">Role</th><th>What They Can Do</th></tr>
<tr><td><strong>Admin</strong></td>
    <td>Full access — all namespaces, user management, admin panel, all features.</td></tr>
<tr><td><strong>Operator</strong></td>
    <td>All namespaces and features except user management and the Admin panel.</td></tr>
<tr><td><strong>Client</strong></td>
    <td>Own namespace only — memory, agents, outputs, tickets. Cannot manage workflows
    or see the Observability dashboard.</td></tr>
<tr><td><strong>Viewer</strong></td>
    <td>Own namespace, read-only — cannot write memory or run agents.</td></tr>
<tr><td><strong>Staff</strong></td>
    <td>Support role — only sees tickets assigned to them. Can self-assign open tickets
    and advance status.</td></tr>
</table>

<h2>Account Security</h2>
<ul>
<li><strong>Account lockout:</strong> 5 failed login attempts triggers a 15-minute lockout.
    Ask your admin to unlock if needed.</li>
<li><strong>Session tokens:</strong> JWT access tokens expire after 60 minutes and are
    silently refreshed while you are active. Closing the browser logs you out.</li>
<li><strong>Case-insensitive usernames:</strong> <code>Alice</code>, <code>ALICE</code>,
    and <code>alice</code> all refer to the same account.</li>
</ul>

<h2>Theme Toggle</h2>
<p>A dark/light mode button sits in the <strong>bottom-left corner</strong> of every page,
including the login screen. Click it to switch themes. Your preference persists for the
current session.</p>
"""


def s5_dashboard() -> str:
    return """
<h1><a name="s5"></a>5 — Dashboard Tour</h1>

<h2>Overview Page</h2>
<p>The home page. Shows the current health of the system and recent activity at a glance.</p>
<table>
<tr><th style="width:30%;">Element</th><th>What It Shows</th></tr>
<tr><td>System Status strip</td>
    <td>Green/red indicators for the API and database.</td></tr>
<tr><td>KPI Cards</td>
    <td>Total memory entries, registered agents, total runs, workflows, and outputs.</td></tr>
<tr><td>Recent Events</td>
    <td>Last 8 agent run results with agent name, namespace, timestamp, and quality
    score pill.</td></tr>
<tr><td>Quick Dispatch</td>
    <td>Run any agent against any namespace with a one-off prompt — no need to open the
    Agents page.</td></tr>
<tr><td>Memory by Namespace</td>
    <td>Count of active memory entries per namespace.</td></tr>
<tr><td>Auto-refresh toggle</td>
    <td>When enabled the feed refreshes every 8 seconds — useful for monitoring live
    runs.</td></tr>
<tr><td>Error alert strip</td>
    <td>Red banner shown when any recent run failed. Clears when errors are gone.</td></tr>
<tr><td>Running-now indicator</td>
    <td>Yellow banner listing agents currently executing.</td></tr>
</table>

<h2>Eval Score Pills</h2>
<p>Each run entry in the Recent Events feed shows a colour-coded quality pill:</p>
<table>
<tr><th style="width:20%;">Colour</th><th>Score Range</th><th>Meaning</th></tr>
<tr><td><span class="pill-green">&#9632; Green</span></td>
    <td>4.0 – 5.0</td><td>High quality — output addressed the prompt well.</td></tr>
<tr><td><span class="pill-amber">&#9632; Amber</span></td>
    <td>2.5 – 3.9</td><td>Acceptable — review if output is going to a client.</td></tr>
<tr><td><span class="pill-red">&#9632; Red</span></td>
    <td>0 – 2.4</td><td>Low quality — re-run with a more specific prompt.</td></tr>
</table>

<h2>Memory Page</h2>
<p>Browse, search, write, and delete memory entries.</p>
<ul>
<li>Full-text search across keys and values</li>
<li>Filter by namespace, category (fact / preference / reminder / task), and minimum
    confidence</li>
<li>Write entries with category, TTL, and confidence score</li>
<li>Reminder entries use a date/time picker for scheduled expiry</li>
<li>Toggle <strong>Hybrid Search</strong> for BM25 + vector semantic retrieval
    (higher recall, slightly slower)</li>
<li>Bulk delete: select entries with checkboxes, then use the bulk toolbar</li>
</ul>

<h2>Agents Page</h2>
<p>Three tabs — Chat, Catalog, and Run History.</p>

<h3>Chat Tab</h3>
<p>Conversational multi-turn interface. Select an agent and namespace, type your message,
press Enter. Responses stream token-by-token as they arrive.</p>
<ul>
<li><strong>Image upload:</strong> attach a screenshot, chart, or document for visual
    analysis</li>
<li><strong>Voice input:</strong> click the microphone, record, auto-transcribed into
    the prompt field (requires Whisper)</li>
<li><strong>Conversation history:</strong> full back-and-forth shown per agent per session</li>
<li><strong>Clear conversation:</strong> resets history and starts a new session</li>
<li><strong>Eval badge:</strong> appears below each response ~10 seconds after completion</li>
<li><strong>Token count:</strong> shown after each response</li>
</ul>

<h3>Catalog Tab</h3>
<p>Grid of all registered agents with descriptions and a one-shot run form. Good for
quick single-task dispatches where you do not need conversation history.</p>

<h3>Run History Tab</h3>
<p>Complete record of every run across all agents:</p>
<ul>
<li>Quality score pill per run</li>
<li>Expandable eval dimension breakdown (task completion, factual grounding, conciseness,
    safety)</li>
<li>Per-agent average score in the summary header</li>
<li>Bulk delete via checkbox selection</li>
</ul>

<h2>Workflows Page</h2>
<p>See all 7 configured pipelines, trigger them manually, and monitor run history.
The <strong>Webhooks</strong> tab lets you generate a secret URL so external systems
can fire a workflow with a single HTTP POST — no login required.</p>

<h2>Client Vault Page</h2>
<ul>
<li><strong>Namespaces:</strong> view your namespace details, workspace stats (files, KB),
    project count</li>
<li><strong>Projects:</strong> list projects in your namespace, update status
    (active / paused / archived)</li>
<li><strong>Context Files:</strong> upload files that are automatically injected into every
    agent system prompt for your namespace — ideal for brand guidelines, SOPs, or client
    briefs</li>
</ul>

<h2>Outputs Page</h2>
<p>All AI-generated content saved by agents — reports, summaries, plans, analyses, code.
Full-text search, date and type filters, and per-output export to Markdown or PDF.
Bulk delete via checkbox selection.</p>

<h2>Tickets Page</h2>
<p>Full support and task lifecycle. Covered in detail in Section 11.</p>

<h2>Observability Page (Admin / Operator)</h2>
<p>Four sub-tabs: Quality Scores, Latency, Token Cost, Memory Health. Covered in
Section 13.</p>

<h2>Settings Page (Admin / Operator)</h2>
<p>System configuration, Supabase sync controls, environment and runtime info.</p>

<h2>Admin Panel (Admin only)</h2>
<p>User management, API key management, audit log, session management, and security
configuration. Covered in Section 16.</p>
"""


def s6_agents() -> str:
    return """
<h1><a name="s6"></a>6 — Working with AI Agents</h1>

<h2>The 12 Built-In Agents</h2>
<table>
<tr><th style="width:25%;">Agent</th><th style="width:15%;">Category</th><th>What It Does</th></tr>
<tr><td><strong>Analysis Agent</strong></td><td>Analysis</td>
    <td>Data analysis — structured reports, key findings, and recommendations from
    raw data or context.</td></tr>
<tr><td><strong>Morning Briefing Agent</strong></td><td>Ops</td>
    <td>Synthesises overnight context into a structured morning briefing: news,
    reminders, client updates, priority actions.</td></tr>
<tr><td><strong>Client Manager Agent</strong></td><td>Ops</td>
    <td>Per-client project status cards with deadlines, blockers, and action items.</td></tr>
<tr><td><strong>Communications Agent</strong></td><td>Comms</td>
    <td>Client-facing emails, messages, and proposals — tone-matched to each client.</td></tr>
<tr><td><strong>Memory Curator Agent</strong></td><td>System</td>
    <td>Reviews, deduplicates, and consolidates memory entries to keep the store lean
    and coherent.</td></tr>
<tr><td><strong>Meta Orchestrator Agent</strong></td><td>System</td>
    <td>Decomposes complex goals into ordered chains of agent invocations.</td></tr>
<tr><td><strong>QA Agent</strong></td><td>Engineering</td>
    <td>Code review against OWASP, platform compatibility, and brand compliance
    rules.</td></tr>
<tr><td><strong>Research Agent</strong></td><td>Research</td>
    <td>Deep research with synthesis and source validation across a given topic.</td></tr>
<tr><td><strong>Scheduling Agent</strong></td><td>Ops</td>
    <td>Converts natural language scheduling requests into memory reminder entries
    with expiry timestamps.</td></tr>
<tr><td><strong>Transport Ops Agent</strong></td><td>Domain</td>
    <td>Domain-specific fleet and booking analysis — namespace-locked to its assigned
    project.</td></tr>
<tr><td><strong>Workflow Builder Agent</strong></td><td>System</td>
    <td>Converts plain-English automation descriptions into ClaudeOS workflow YAML
    definitions.</td></tr>
<tr><td><strong>Writing Agent</strong></td><td>Content</td>
    <td>Drafts reports, emails, and proposals with voice matched to the active
    namespace.</td></tr>
</table>

<h2>Running an Agent — Three Ways</h2>

<h3>1. Chat (Recommended for iterative work)</h3>
<p>Go to <strong>Agents → Chat</strong>. Select the agent and namespace from the dropdowns,
type your request, and press Enter. The response streams back in real time. You can follow
up with additional messages in the same conversation.</p>

<div class="tip"><strong>Best practice:</strong> be specific. Instead of "write a report",
say "write a 2-page executive summary of the Q2 analysis results for the mobile app
project, highlighting the top 3 risks". Specific prompts score higher on eval.</div>

<h3>2. Catalog (For one-shot tasks)</h3>
<p>Go to <strong>Agents → Catalog</strong>. Find the agent, fill in the prompt and namespace,
click <strong>Run</strong>. The run is polled every 3 seconds until complete.</p>

<h3>3. Quick Dispatch (From Overview)</h3>
<p>The Overview page has a Quick Dispatch widget — select agent, namespace, enter prompt,
run. Good for fast one-off tasks without navigating away from the dashboard.</p>

<h2>Namespace Scoping</h2>
<p>Every agent run is scoped to a <em>namespace</em>. The namespace controls which memory
entries are injected into the agent's context and where the output is stored. If you are
an admin or operator you can select any namespace. If you are a client you only see your
own.</p>

<h2>Image Analysis</h2>
<p>In the Chat tab, use the image uploader below the prompt field to attach a file. The
agent receives the image as a content block alongside your prompt. Useful for:</p>
<ul>
<li>Analysing screenshots of dashboards or reports</li>
<li>Reviewing UI designs or wireframes</li>
<li>Extracting data from charts or tables in images</li>
</ul>

<h2>Voice Input</h2>
<p>Click the microphone button in the Chat tab. Record your request. ClaudeOS transcribes
the audio locally using Whisper and populates the prompt field. Review the transcription,
edit if needed, then submit as normal. Requires <code>pip install openai-whisper</code>.</p>

<h2>Understanding Token Usage</h2>
<p>Each agent response shows input tokens (context sent) and output tokens (response
generated). Tokens drive API cost. To keep costs low:</p>
<ul>
<li>Use specific prompts (less context padding needed)</li>
<li>Clear conversation history when starting a new topic</li>
<li>Use lighter agents (e.g. Scheduling Agent) for simple tasks</li>
</ul>
"""


def s7_memory() -> str:
    return """
<h1><a name="s7"></a>7 — Memory System</h1>

<h2>What Is Memory?</h2>
<p>Memory is ClaudeOS's persistent knowledge store. When you or an agent writes a memory
entry, it is stored in the database and automatically injected into every subsequent agent
run in that namespace. This means agents remember facts, preferences, context, and
reminders across sessions — without you having to repeat yourself.</p>

<h2>Memory Categories</h2>
<table>
<tr><th style="width:20%;">Category</th><th>Use For</th><th>Example</th></tr>
<tr><td><strong>Fact</strong></td>
    <td>Stable information about a client, project, or domain</td>
    <td>"Client prefers invoices in GBP"</td></tr>
<tr><td><strong>Preference</strong></td>
    <td>Tone, style, or format preferences</td>
    <td>"Reports should start with an executive summary"</td></tr>
<tr><td><strong>Reminder</strong></td>
    <td>Time-sensitive items that expire automatically</td>
    <td>"Follow up on proposal by 2026-06-01"</td></tr>
<tr><td><strong>Task</strong></td>
    <td>Action items for agents or team members</td>
    <td>"Prepare Q3 analysis before board meeting"</td></tr>
</table>

<h2>Writing a Memory Entry</h2>
<ol>
<li>Go to <strong>Memory</strong> page</li>
<li>Click <strong>Add Entry</strong></li>
<li>Fill in: key (short identifier), value (the content), category, TTL (optional
    expiry in days), confidence score (0–1)</li>
<li>For reminders: use the date/time picker to set the exact expiry</li>
<li>Click <strong>Save</strong></li>
</ol>

<h2>Searching Memory</h2>
<p>The search bar at the top of the Memory page performs full-text search across keys
and values. Toggle <strong>Hybrid Search</strong> for BM25 + semantic vector retrieval
— better recall for conceptual queries (e.g. "client payment terms" finds entries about
invoicing even if they do not contain those exact words).</p>

<h2>How Memory Is Injected into Agents</h2>
<p>When an agent runs, ClaudeOS retrieves the most relevant memory entries for the
current query using hybrid search, then injects them into the agent's system prompt as
structured context. This is done automatically — you do not need to do anything. The
tiered context system reduces token usage by ~40% versus injecting all memory.</p>

<h2>Memory Consolidation</h2>
<p>An automated job runs every 4 hours. It finds groups of similar memory entries,
uses Claude to synthesise each cluster into a single concise entry, and archives the
originals. This keeps the memory store lean and prevents duplicates building up over
time. Original entries are never hard-deleted — they are archived and can be reviewed
in the Observability → Memory Health tab.</p>

<p>You can also trigger consolidation immediately: go to
<strong>Observability → Memory Health → Trigger Consolidation</strong>.</p>

<div class="tip"><strong>Tip:</strong> write memory entries in full sentences, not just
keywords. "The client's primary contact is James Brown, james@example.com, +44 7700 900000"
is far more useful to an agent than "james contact".</div>
"""


def s8_workflows() -> str:
    return """
<h1><a name="s8"></a>8 — Workflows &amp; Automation</h1>

<h2>What Are Workflows?</h2>
<p>Workflows are multi-step AI pipelines. Each workflow chains together one or more
agent calls, passing the output of one step as input to the next. They can run on a
cron schedule or be triggered manually from the dashboard or via webhook from an external
system.</p>

<h2>Built-In Workflows</h2>
<table>
<tr><th style="width:30%;">Workflow</th><th>What It Does</th><th style="width:20%;">Default Schedule</th></tr>
<tr><td><strong>Morning Briefing</strong></td>
    <td>Synthesises overnight memory and context into a structured daily briefing.</td>
    <td>Mon–Fri 07:00</td></tr>
<tr><td><strong>Memory Curation</strong></td>
    <td>Runs the Memory Curator Agent to deduplicate and consolidate memory entries.</td>
    <td>Every 4 hours</td></tr>
<tr><td><strong>Research Digest</strong></td>
    <td>Research Agent deep-dives a topic and produces a structured digest.</td>
    <td>On demand</td></tr>
<tr><td><strong>Client Report</strong></td>
    <td>Client Manager Agent generates status cards for all active projects.</td>
    <td>Weekly</td></tr>
<tr><td><strong>Analysis Run</strong></td>
    <td>Analysis Agent processes queued data and produces findings.</td>
    <td>On demand</td></tr>
<tr><td><strong>QA Sweep</strong></td>
    <td>QA Agent reviews recent outputs against quality and compliance rules.</td>
    <td>On demand</td></tr>
<tr><td><strong>Meta-Orchestrate</strong></td>
    <td>Meta Orchestrator decomposes a complex goal into a chain of agent calls.</td>
    <td>On demand</td></tr>
</table>

<h2>Running a Workflow Manually</h2>
<ol>
<li>Go to <strong>Workflows</strong> page</li>
<li>Find the workflow you want</li>
<li>Click <strong>Run Now</strong></li>
<li>The run appears in Recent Events on the Overview page</li>
</ol>

<h2>Webhook Triggers</h2>
<p>Any workflow can be triggered by an external system (a CRM, a website form, a script)
without a login token. The webhook is authenticated by a secret header.</p>

<h3>Enable a Webhook</h3>
<ol>
<li>Open the Workflows page, select a workflow, click the <strong>Webhooks</strong> tab</li>
<li>Click <strong>Enable Webhook</strong> — a unique URL and HMAC secret are generated</li>
<li>Copy both the URL and the secret. The secret is shown once — store it safely.</li>
</ol>

<h3>Fire the Webhook</h3>
<pre>curl -X POST {api_url}/api/v1/workflows/morning-briefing/trigger \\
  -H "X-Webhook-Secret: your-secret" \\
  -H "Content-Type: application/json" \\
  -d '{{"context": {{"namespace": "global", "topic": "AI news"}}}}'</pre>
<p>The context object is passed as input to the first pipeline step.</p>

<h2>Viewing Workflow Run History</h2>
<p>Each workflow card shows its last run timestamp and status. Click a workflow to expand
its step-by-step run log.</p>
""".format(api_url=API_URL)


def s9_vault() -> str:
    return """
<h1><a name="s9"></a>9 — Client Vault</h1>

<h2>Namespaces</h2>
<p>A namespace is a fully isolated workspace. All memory, outputs, and agent context is
scoped per namespace — nothing leaks between namespaces. The Client Vault page shows:</p>
<ul>
<li>Namespace name and description</li>
<li>Workspace statistics: number of files, total size in KB</li>
<li>Number of active projects</li>
</ul>

<h2>Projects</h2>
<p>Projects live inside a namespace and represent discrete engagements or work streams.
From the Client Vault you can:</p>
<ul>
<li>List all projects in your namespace</li>
<li>Update a project's status: <strong>Active</strong> / <strong>Paused</strong> /
    <strong>Archived</strong></li>
<li>See project descriptions and creation dates</li>
</ul>

<h2>Context Files</h2>
<p>Context files are documents uploaded per namespace that are automatically injected
into every agent system prompt for that namespace. Use this for:</p>
<ul>
<li>Brand guidelines and tone-of-voice documents</li>
<li>Standard operating procedures</li>
<li>Client briefs or background documents</li>
<li>Technical specifications that agents should always be aware of</li>
</ul>
<p>Upload a file on the Client Vault page under the <strong>Context Files</strong> section.
Supported formats: plain text, Markdown, PDF. The file is stored in the namespace workspace
and picked up on the next agent run.</p>

<div class="note"><strong>Note:</strong> Keep context files concise and focused. Very large
context files increase token usage on every agent call. Split large documents into smaller
topical files where possible.</div>
"""


def s10_outputs() -> str:
    return """
<h1><a name="s10"></a>10 — Outputs &amp; Reports</h1>

<h2>What Are Outputs?</h2>
<p>Every time an agent produces a response with <code>save_output: true</code> (the default),
the full output is saved to the database and the filesystem. Outputs are automatically tagged
with agent name, namespace, output type, and timestamp.</p>

<h2>Browsing Outputs</h2>
<p>Go to the <strong>Outputs</strong> page. You can:</p>
<ul>
<li>Search by keyword across all output content (full-text)</li>
<li>Filter by namespace, output type (report / summary / plan / analysis / code /
    other), and date range</li>
<li>Click any output to expand and read the full content</li>
</ul>

<h2>Exporting an Output</h2>
<p>Two export formats are available per output:</p>
<table>
<tr><th style="width:20%;">Format</th><th>Notes</th></tr>
<tr><td><strong>Markdown</strong></td>
    <td>Raw text with Markdown formatting. Opens in any text editor or Markdown
    renderer. Always available.</td></tr>
<tr><td><strong>PDF</strong></td>
    <td>Rendered PDF with ClaudeOS branding. Requires wkhtmltopdf installed on the
    server.</td></tr>
</table>

<h2>Bulk Delete</h2>
<p>Select multiple outputs using the checkboxes and click the bulk delete button. This is
permanent — deleted outputs are not recoverable unless Supabase cloud sync is enabled.</p>

<div class="tip"><strong>Tip:</strong> use the type and date filters to find old or
low-quality outputs before bulk deleting to avoid accidentally removing important
content.</div>
"""


def s11_tickets() -> str:
    return """
<h1><a name="s11"></a>11 — Ticketing System</h1>

<h2>Overview</h2>
<p>The ticketing system provides a full support and task lifecycle inside ClaudeOS. Tickets
can represent bugs, feature requests, client tasks, internal work items, or support
requests.</p>

<h2>Priority / SLA Tiers</h2>
<table>
<tr><th style="width:15%;">Priority</th><th style="width:20%;">Label</th><th>Meaning</th></tr>
<tr><td>P1</td><td><strong>Critical</strong></td>
    <td>System down or blocking. Immediate response required.</td></tr>
<tr><td>P2</td><td><strong>High</strong></td>
    <td>Major issue, significant business impact.</td></tr>
<tr><td>P3</td><td><strong>Medium</strong></td>
    <td>Important but not blocking.</td></tr>
<tr><td>P4</td><td><strong>Low</strong></td>
    <td>Nice-to-have, enhancement, or minor issue.</td></tr>
</table>

<h2>Ticket Lifecycle</h2>
<pre>Open  →  In Progress  →  Resolved  →  Closed</pre>
<ul>
<li><strong>Open:</strong> ticket created, not yet assigned or started</li>
<li><strong>In Progress:</strong> assigned and being worked on</li>
<li><strong>Resolved:</strong> work complete, awaiting confirmation</li>
<li><strong>Closed:</strong> confirmed resolved, resolution note recorded</li>
</ul>

<h2>Creating a Ticket</h2>
<ol>
<li>Go to <strong>Tickets</strong> page</li>
<li>Click <strong>New Ticket</strong></li>
<li>Fill in title, description, priority, and namespace</li>
<li>Click <strong>Create</strong></li>
</ol>

<h2>Assignment</h2>
<ul>
<li><strong>Admin / Operator:</strong> can assign any ticket to any user</li>
<li><strong>Staff:</strong> can self-assign any open ticket</li>
<li><strong>Client / Viewer:</strong> cannot assign tickets</li>
</ul>

<h2>Comments</h2>
<p>Expand a ticket and click the <strong>Comments</strong> toggle to load threaded comments.
Comments load on demand (not preloaded) to keep the page fast.</p>

<h2>Resolution Notes</h2>
<p>When moving a ticket to Resolved or Closed, record what was done in the resolution note
field. This creates an audit trail and a knowledge base of past solutions.</p>

<h2>Bulk Delete</h2>
<p>Select multiple tickets with checkboxes and delete in one action. Admin / Operator only.</p>

<h2>Stats Panel</h2>
<p>The top of the Tickets page shows ticket counts broken down by status and priority at
a glance.</p>
"""


def s12_quality() -> str:
    return """
<h1><a name="s12"></a>12 — Quality Scoring</h1>

<h2>How It Works</h2>
<p>Every agent run is automatically scored by Claude Haiku (a fast, low-cost AI model) on
4 dimensions. Scoring happens asynchronously in the background — it does not add any
latency to the agent response. Scores typically appear 5–15 seconds after the run
completes.</p>

<h2>Scoring Dimensions</h2>
<table>
<tr><th style="width:25%;">Dimension</th><th style="width:12%;">Scale</th><th style="width:12%;">Weight</th><th>What It Measures</th></tr>
<tr><td><strong>Task Completion</strong></td><td>0–5</td><td>40%</td>
    <td>Did the output fully address the prompt? Is the task actually done?</td></tr>
<tr><td><strong>Factual Grounding</strong></td><td>0–5</td><td>30%</td>
    <td>Are claims in the output grounded in the memory context that was injected?
    Penalises hallucination.</td></tr>
<tr><td><strong>Conciseness</strong></td><td>0–5</td><td>20%</td>
    <td>Is the output the right length? Penalises padding, repetition, and unnecessary
    waffle.</td></tr>
<tr><td><strong>Safety</strong></td><td>pass/fail</td><td>10%</td>
    <td>Does the output contain harmful, biased, or dangerous content? A fail caps the
    overall score at 1.0 regardless of other scores.</td></tr>
</table>

<p><strong>Overall score</strong> = (Task × 0.40) + (Factual × 0.30) + (Concise × 0.20)
+ (Safety × 0.10)</p>

<h2>Where Scores Appear</h2>
<ul>
<li><strong>Run History:</strong> colour-coded pill next to each run</li>
<li><strong>Overview:</strong> pill on each recent event entry</li>
<li><strong>Chat:</strong> badge below each assistant response (~10s delay)</li>
<li><strong>Observability → Quality Scores:</strong> aggregated analytics, per-agent
    averages, score distribution chart</li>
</ul>

<h2>Low-Quality Threshold</h2>
<p>Any run scoring below <strong>2.5</strong> is flagged as low quality. The Observability
dashboard shows a red alert when any agent's rolling average drops below this threshold.
Re-run with a more specific prompt if you see this.</p>

<h2>Improving Scores</h2>
<table>
<tr><th style="width:30%;">Low score on...</th><th>What to do</th></tr>
<tr><td>Task Completion</td>
    <td>Make your prompt more specific. State exactly what you want, the format, and
    the desired length.</td></tr>
<tr><td>Factual Grounding</td>
    <td>Add more relevant facts to Memory before running the agent. The agent can only
    ground claims in what it has been given.</td></tr>
<tr><td>Conciseness</td>
    <td>Add "be concise" or "maximum 3 paragraphs" to your prompt. Or use an agent with
    lower <code>max_tokens</code>.</td></tr>
<tr><td>Safety</td>
    <td>Review the output for any problematic content. Adjust the prompt to avoid
    triggering safety filters.</td></tr>
</table>
"""


def s13_observability() -> str:
    return """
<h1><a name="s13"></a>13 — Observability</h1>

<p>The Observability page is available to <strong>Admin</strong> and
<strong>Operator</strong> roles only. It has four sub-tabs.</p>

<h2>Quality Scores Tab</h2>
<ul>
<li>Per-agent average eval scores in a ranked table</li>
<li>Score distribution chart showing how scores are spread across all runs (0.5-step
    buckets)</li>
<li>Dimension breakdown: task completion, factual grounding, conciseness, safety</li>
<li>Red alert when any agent's average drops below 2.5</li>
</ul>

<h2>Latency Tab</h2>
<ul>
<li>p50, p95, and p99 latency across all runs (percentile-based)</li>
<li>Per-agent average latency table sorted by slowest</li>
<li>Time-series chart showing latency trends over the past 7 days</li>
</ul>
<p>Expected latency ranges (claude-sonnet-4-6):</p>
<table>
<tr><th>Response length</th><th>Typical latency</th></tr>
<tr><td>Short (under 200 tokens)</td><td>2–6 seconds</td></tr>
<tr><td>Medium (200–800 tokens)</td><td>6–20 seconds</td></tr>
<tr><td>Long (800+ tokens)</td><td>20–60 seconds</td></tr>
</table>

<h2>Token Cost Tab</h2>
<ul>
<li>Total input and output token counts across all runs</li>
<li>Estimated USD cost based on current claude-sonnet-4-6 pricing</li>
<li>Per-agent breakdown: tokens used, cost, run count, average cost per run</li>
</ul>
<div class="note">Token cost estimates are approximate and based on list pricing at the
time of the ClaudeOS release. Check Anthropic's pricing page for current rates.</div>

<h2>Memory Health Tab</h2>
<ul>
<li>Entry counts per namespace: total, active, consolidated, expired</li>
<li>Storage size estimate per namespace</li>
<li><strong>Trigger Consolidation</strong> button — runs the consolidation job immediately</li>
<li>Visual indicator when any namespace has not been consolidated in over 24 hours</li>
</ul>
"""


def s14_advanced() -> str:
    return """
<h1><a name="s14"></a>14 — Advanced Features</h1>

<h2>Multi-Turn Conversation History</h2>
<p>Each agent in Chat mode maintains its own conversation session. The full back-and-forth
is stored in the database — not just in browser memory. This means:</p>
<ul>
<li>Refreshing the page does not lose the conversation (within the same session)</li>
<li>The agent has access to everything said earlier in the conversation as context</li>
<li>Each conversation session gets a unique ID stored in <code>agent_conversations</code></li>
</ul>
<p>Click <strong>Clear Conversation</strong> to start a fresh session when moving to a
new topic — this avoids stale context polluting new requests.</p>

<h2>Image and Screenshot Analysis</h2>
<p>Any Chat session supports image uploads. The image is encoded as a base64 content block
and sent alongside your prompt to Claude's vision API. Practical uses:</p>
<ul>
<li>Paste a screenshot of a report and ask the agent to summarise or critique it</li>
<li>Upload a chart and ask the Analysis Agent to interpret the trends</li>
<li>Send a UI screenshot to the QA Agent for a quick compliance check</li>
<li>Share a document photo for text extraction and analysis</li>
</ul>

<h2>Voice Input</h2>
<p>Requires Whisper: <code>pip install openai-whisper</code>. The model downloads on first
use (~140 MB). Subsequent starts are fast (model cached in memory).</p>
<ol>
<li>Click the microphone button in the Chat tab</li>
<li>Record your request (up to 30 seconds recommended)</li>
<li>ClaudeOS transcribes the audio locally — nothing is sent to any external service</li>
<li>The transcription populates the prompt field — review, edit if needed, then submit</li>
</ol>

<h2>MCP Tool Server</h2>
<p>The Model Context Protocol (MCP) server exposes all 12 ClaudeOS agents as native tools
to any MCP-compatible AI client — Claude Desktop, Cursor, or custom agents.</p>

<h3>Starting the MCP Server</h3>
<pre>.\\scripts\\start_mcp.ps1</pre>
<p>Starts on port 5100. Verify it is running:</p>
<pre>curl http://localhost:5100/mcp</pre>

<h3>Connecting Claude Desktop</h3>
<p>Add the following to <code>%APPDATA%\\Claude\\claude_desktop_config.json</code>:</p>
<pre>{{
  "mcpServers": {{
    "claudeos": {{
      "url": "http://localhost:5100/mcp"
    }}
  }}
}}</pre>
<p>Restart Claude Desktop. All 12 agents will appear as available tools in the tool picker.
You can now ask Claude Desktop to "use the Writing Agent to draft a proposal" and it will
call your ClaudeOS instance directly.</p>

<h2>A2A Agent Cards</h2>
<p>Each agent exposes a machine-readable capability card for agent-to-agent discovery:</p>
<pre>GET {api_url}/api/v1/agents/writing-agent/.well-known/agent.json</pre>
<p>The card describes the agent's name, description, input/output schema, and streaming
and multi-turn capabilities. External AI orchestrators can use this endpoint to
automatically discover and delegate to ClaudeOS agents.</p>
""".format(api_url=API_URL)


def s15_api() -> str:
    return """
<h1><a name="s15"></a>15 — API Reference</h1>

<p>The ClaudeOS REST API runs at <strong>{api_url}/api/v1/</strong>. All endpoints
require authentication (JWT Bearer token or X-API-Key header) except
<code>/health</code> and webhook trigger endpoints.</p>

<h2>Authentication</h2>

<h3>JWT (Interactive Users)</h3>
<pre># 1. Login
curl -X POST {api_url}/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{{"username":"your_user","password":"your_pass"}}'

# Response
{{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": {{"id": 1, "username": "your_user", "role": "operator"}}
}}

# 2. Use the access token
curl {api_url}/api/v1/agents \\
  -H "Authorization: Bearer eyJ..."</pre>

<p>Access tokens expire after 60 minutes. Refresh them:</p>
<pre>curl -X POST {api_url}/api/v1/auth/refresh \\
  -H "Authorization: Bearer &lt;refresh_token&gt;"</pre>

<h3>API Key (Scripts and Automation)</h3>
<pre>curl {api_url}/api/v1/memory \\
  -H "X-API-Key: your_api_key"</pre>
<p>API keys are created in the Admin Panel (admin only) and shown once on creation.</p>

<h2>Core Endpoint Reference</h2>
<table>
<tr><th style="width:12%;">Method</th><th style="width:40%;">Endpoint</th><th>Description</th></tr>
<tr><td>POST</td><td><code>/auth/login</code></td>
    <td>Login, returns access + refresh tokens</td></tr>
<tr><td>POST</td><td><code>/auth/refresh</code></td>
    <td>Renew access token using refresh token</td></tr>
<tr><td>POST</td><td><code>/auth/logout</code></td>
    <td>Revoke current session</td></tr>
<tr><td>GET</td><td><code>/auth/me</code></td>
    <td>Current user info and role</td></tr>
<tr><td>GET</td><td><code>/health</code></td>
    <td>Public health check (no auth)</td></tr>
<tr><td>GET</td><td><code>/memory</code></td>
    <td>List memory entries (filterable)</td></tr>
<tr><td>POST</td><td><code>/memory</code></td>
    <td>Write a memory entry</td></tr>
<tr><td>DELETE</td><td><code>/memory/&lt;id&gt;</code></td>
    <td>Delete a memory entry</td></tr>
<tr><td>GET</td><td><code>/memory/hybrid-search</code></td>
    <td>Hybrid BM25+vector search with RRF reranking</td></tr>
<tr><td>POST</td><td><code>/memory/consolidate</code></td>
    <td>Trigger memory consolidation immediately</td></tr>
<tr><td>GET</td><td><code>/agents</code></td>
    <td>List all registered agents</td></tr>
<tr><td>POST</td><td><code>/agents/&lt;name&gt;/run</code></td>
    <td>Dispatch async agent run, returns run_id</td></tr>
<tr><td>GET</td><td><code>/agents/runs/&lt;id&gt;</code></td>
    <td>Poll run status and output</td></tr>
<tr><td>GET</td><td><code>/agents/runs</code></td>
    <td>List all runs (filterable by namespace/status)</td></tr>
<tr><td>GET</td><td><code>/agents/&lt;name&gt;/stream</code></td>
    <td>SSE streaming response (token-by-token)</td></tr>
<tr><td>GET</td><td><code>/agents/&lt;name&gt;/.well-known/agent.json</code></td>
    <td>A2A Agent Card</td></tr>
<tr><td>GET</td><td><code>/outputs</code></td>
    <td>List outputs</td></tr>
<tr><td>DELETE</td><td><code>/outputs/bulk</code></td>
    <td>Bulk delete outputs</td></tr>
<tr><td>GET</td><td><code>/tickets</code></td>
    <td>List tickets</td></tr>
<tr><td>POST</td><td><code>/tickets</code></td>
    <td>Create a ticket</td></tr>
<tr><td>PUT</td><td><code>/tickets/&lt;id&gt;</code></td>
    <td>Update ticket (status, assignee, resolution)</td></tr>
<tr><td>DELETE</td><td><code>/tickets/bulk</code></td>
    <td>Bulk delete tickets</td></tr>
<tr><td>GET</td><td><code>/tickets/stats</code></td>
    <td>Ticket counts by status and priority</td></tr>
<tr><td>GET</td><td><code>/workflows</code></td>
    <td>List workflows</td></tr>
<tr><td>POST</td><td><code>/workflows/&lt;name&gt;/run</code></td>
    <td>Trigger workflow manually (JWT required)</td></tr>
<tr><td>POST</td><td><code>/workflows/&lt;name&gt;/trigger</code></td>
    <td>Webhook trigger (public, X-Webhook-Secret auth)</td></tr>
<tr><td>POST</td><td><code>/workflows/&lt;name&gt;/webhook/enable</code></td>
    <td>Enable webhook and generate secret</td></tr>
<tr><td>GET</td><td><code>/system/status</code></td>
    <td>System health detail</td></tr>
</table>

<h2>Async Run — Full Example</h2>
<pre># Dispatch
curl -X POST {api_url}/api/v1/agents/writing-agent/run \\
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
curl {api_url}/api/v1/agents/runs/abc123 \\
  -H "Authorization: Bearer &lt;token&gt;"

# Response when complete
{{
  "run_id": "abc123",
  "status": "done",
  "output": "Q2 Executive Summary\\n...",
  "tokens_in": 1420,
  "tokens_out": 380,
  "eval_score": 4.2
}}</pre>

<h2>SSE Streaming — Full Example</h2>
<pre>curl -N "{api_url}/api/v1/agents/writing-agent/stream?prompt=Hello&amp;namespace=my-ns" \\
  -H "X-API-Key: your_api_key"

# Stream events arrive as:
data: {{"type": "token", "text": "Hello"}}
data: {{"type": "token", "text": " there"}}
data: {{"type": "done", "run_id": "xyz", "tokens_in": 900, "tokens_out": 12}}

# On error:
data: {{"type": "error", "message": "Rate limit exceeded"}}</pre>
""".format(api_url=API_URL)


def s16_security() -> str:
    return """
<h1><a name="s16"></a>16 — Security Model</h1>

<h2>Authentication</h2>
<table>
<tr><th style="width:30%;">Mechanism</th><th>Details</th></tr>
<tr><td>JWT access tokens</td>
    <td>60-minute TTL. Silently refreshed while the session is active. Never stored in
    plaintext — sent as a Bearer header.</td></tr>
<tr><td>Refresh tokens</td>
    <td>7-day TTL. Stored as a SHA-256 hash in the database. Used only to renew access
    tokens. Revokable per-session from the Admin Panel.</td></tr>
<tr><td>API keys</td>
    <td>For script and automation access. Created in the Admin Panel. Shown once on
    creation. Stored as a hash.</td></tr>
<tr><td>Webhook secrets</td>
    <td>32-byte random hex, compared using HMAC constant-time comparison to prevent
    timing attacks.</td></tr>
</table>

<h2>Password Policy</h2>
<ul>
<li>Minimum 10 characters</li>
<li>At least one uppercase, one lowercase, one digit</li>
<li>Hashed with bcrypt (12 rounds) — never stored in plaintext</li>
<li>Admin can force a password change on next login per user</li>
</ul>

<h2>Account Lockout</h2>
<p>5 consecutive failed login attempts triggers a 15-minute lockout. Configurable by
admin via <strong>Admin Panel → Security</strong>. Admin can manually unlock accounts
immediately from <strong>Admin Panel → Users</strong>.</p>

<h2>Namespace Isolation</h2>
<p>Client and Viewer role users are hard-scoped to their assigned namespace. Every API
endpoint enforces namespace access in the application layer — a client user cannot
read, write, or search memory from another namespace regardless of the API parameters
they send.</p>

<h2>Audit Log</h2>
<p>Every significant action is recorded in the audit log:</p>
<ul>
<li>Login success and failure</li>
<li>Account lockout triggered</li>
<li>Logout</li>
<li>Token refresh</li>
<li>User creation, deactivation, and password reset</li>
<li>API key creation and revocation</li>
</ul>
<p>The audit log is viewable in <strong>Admin Panel → Audit Log</strong>. Each entry
records the event type, username, IP address, user agent, and timestamp.</p>

<h2>Admin Panel Controls</h2>
<table>
<tr><th style="width:28%;">Control</th><th>What It Does</th></tr>
<tr><td>Users</td>
    <td>Create, deactivate, unlock, and reset passwords for all users.</td></tr>
<tr><td>API Keys</td>
    <td>Create and revoke API keys. Raw key shown once on creation.</td></tr>
<tr><td>Sessions</td>
    <td>View all active refresh token sessions (IP, user agent, expiry). Revoke any
    session immediately.</td></tr>
<tr><td>Security Config</td>
    <td>Lockout threshold, lockout duration, access token TTL, refresh token TTL,
    enable/disable self-registration.</td></tr>
<tr><td>Audit Log</td>
    <td>Paginated full event log with filtering.</td></tr>
</table>

<h2>What ClaudeOS Does NOT Store</h2>
<ul>
<li>Plaintext passwords — only bcrypt hashes</li>
<li>Raw refresh tokens — only SHA-256 hashes</li>
<li>Raw API keys beyond the initial response — only hashes</li>
<li>Anthropic API key in the database — only in the server's <code>.env</code> file</li>
</ul>
"""


def s17_sync() -> str:
    return """
<h1><a name="s17"></a>17 — Cloud Sync (Supabase)</h1>

<h2>Overview</h2>
<p>ClaudeOS can sync outputs and memory entries to a Supabase PostgreSQL database for
cloud backup and off-site storage. Sync is push-only — SQLite on your server is always
the source of truth. Supabase is a mirror.</p>

<h2>Setup</h2>
<ol>
<li>Create a free account at <strong>supabase.com</strong> and create a new project</li>
<li>In the Supabase SQL Editor, run the contents of <code>sync/supabase_schema.sql</code>
    — this creates the required tables</li>
<li>Copy your Supabase project URL and service role key from the Supabase project
    settings (API section)</li>
<li>Add to <code>.env</code>:
    <pre>SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key</pre></li>
<li>Restart the server — auto-sync starts immediately, firing every 15 minutes</li>
</ol>

<h2>Manual Sync</h2>
<p>Go to <strong>Settings</strong> and click <strong>Sync Now</strong> to push
immediately rather than waiting for the next scheduled run.</p>

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


def s18_troubleshoot() -> str:
    return """
<h1><a name="s18"></a>18 — Troubleshooting</h1>

<table>
<tr><th style="width:35%;">Problem</th><th>Solution</th></tr>
<tr><td>Cannot reach the dashboard</td>
    <td>Run <code>.\\scripts\\start.ps1</code>. Check both ports (5000 and 8501) are
    alive. Verify no firewall is blocking them.</td></tr>
<tr><td>Login fails</td>
    <td>Check username and password (login is case-insensitive for username). After 5
    failures, wait 15 minutes or ask admin to unlock your account.</td></tr>
<tr><td>"Must change password" shown</td>
    <td>Enter your current password then your new password in the prompt that
    appears.</td></tr>
<tr><td>API returns 401 Unauthorized</td>
    <td>Your access token has expired. Log out and log back in. If using an API key,
    verify it has not been revoked in the Admin Panel.</td></tr>
<tr><td>Agent runs are slow</td>
    <td>Expected for long responses — Claude Sonnet processes ~40 tokens/second. For
    short tasks, use an agent with lower <code>max_tokens</code>. Check latency in
    Observability.</td></tr>
<tr><td>Eval scores not appearing</td>
    <td>Scores are async — wait 10–15 seconds after the run completes. If they still
    don't appear, check API logs for Haiku eval errors.</td></tr>
<tr><td>Streaming returns an error</td>
    <td>Ensure only one Flask process is running on port 5000. Restart with
    <code>.\\scripts\\start.ps1</code>.</td></tr>
<tr><td>Voice input not working</td>
    <td>Run <code>pip install openai-whisper</code>. The first use downloads the model
    (~140 MB) — wait for the download to complete.</td></tr>
<tr><td>MCP server not found</td>
    <td>Run <code>pip install mcp uvicorn</code> then
    <code>.\\scripts\\start_mcp.ps1</code>.</td></tr>
<tr><td>Runs stuck as "running"</td>
    <td>Restart the server. Stuck runs from crashed sessions are auto-cleaned on the
    next health check.</td></tr>
<tr><td>Agents not responding</td>
    <td>Check <code>ANTHROPIC_API_KEY</code> in <code>.env</code>. Verify it is not
    expired or rate-limited in the Anthropic console.</td></tr>
<tr><td>ChromaDB slow on first start</td>
    <td>Normal — the sentence-transformers model loads on first request (30–60 second
    cold start). Subsequent requests are fast.</td></tr>
<tr><td>Ticket comments not loading</td>
    <td>Click the <strong>Comments</strong> toggle — comments load on demand, not
    automatically.</td></tr>
<tr><td>Supabase sync fails</td>
    <td>Verify <code>SUPABASE_URL</code> and <code>SUPABASE_SERVICE_KEY</code> in
    <code>.env</code>. Restart after any changes. Check the Settings page for
    error detail.</td></tr>
<tr><td>Output PDF export fails</td>
    <td>Try Markdown export instead. PDF export may require wkhtmltopdf installed on
    the server.</td></tr>
<tr><td>Memory entries not appearing in agent context</td>
    <td>Entries may be archived or expired. Check the Memory page with all filters
    cleared. Ensure the namespace selected when running the agent matches the namespace
    where you wrote the entries.</td></tr>
</table>
"""


def s19_support() -> str:
    return f"""
<h1><a name="s19"></a>19 — Support</h1>

<h2>Contact Your Administrator</h2>
<table>
<tr><th style="width:25%;">Detail</th><th>Value</th></tr>
<tr><td>Name</td><td>{ADMIN_NAME}</td></tr>
<tr><td>Email</td><td>{ADMIN_EMAIL}</td></tr>
<tr><td>Phone</td><td>{ADMIN_PHONE}</td></tr>
<tr><td>Dashboard URL</td><td><code>{SYSTEM_URL}</code></td></tr>
</table>

<h2>Before Contacting Support</h2>
<p>Please check Section 18 (Troubleshooting) first. If the issue persists:</p>
<ol>
<li>Note the exact error message shown in the dashboard or browser</li>
<li>Note what you were doing when the error occurred (which page, which agent,
    which prompt)</li>
<li>Note whether the error is reproducible (does it happen every time?)</li>
<li>Check the Observability dashboard for any system-wide alerts</li>
</ol>

<h2>Useful Information to Provide</h2>
<ul>
<li>Your username and role</li>
<li>Your namespace</li>
<li>The run ID (visible in Run History) if the issue is with a specific agent run</li>
<li>Approximate time the issue occurred</li>
</ul>

<hr/>
<p style="text-align:center;color:#888;font-size:9pt;">
  ClaudeOS v{VERSION} &nbsp;&middot;&nbsp; {TODAY} &nbsp;&middot;&nbsp;
  Prepared for {CLIENT} &nbsp;&middot;&nbsp; Confidential
</p>
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
        s14_advanced(),
        s15_api(),
        s16_security(),
        s17_sync(),
        s18_troubleshoot(),
        s19_support(),
    ])
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>ClaudeOS — Client Handbook — {CLIENT}</title>
  <style>{CSS}</style>
</head>
<body>
<div id="footer_content">ClaudeOS v13.1 &nbsp;&#183;&nbsp; faiyke-ai &nbsp;&#183;&nbsp; Page <pdf:pagenumber> of <pdf:pagecount></div>
{body}
</body>
</html>"""


if __name__ == "__main__":
    out_path = Path(f"docs/ClaudeOS_Handbook_{CLIENT}.pdf")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("Building HTML...")
    html = build_html()

    print(f"Rendering PDF -> {out_path} ...")
    with open(out_path, "wb") as f:
        result = pisa.CreatePDF(io.StringIO(html), dest=f)

    if result.err:
        print(f"PDF errors: {result.err}")
    else:
        size_kb = out_path.stat().st_size // 1024
        print(f"Done: {out_path} ({size_kb} KB)")
