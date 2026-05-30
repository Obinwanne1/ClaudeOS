"""System tools — give agents access to internal ClaudeOS data.

These tools let agents read outputs produced by other agents, search memory,
and query workspace data. This enables cross-agent workflows where one agent's
output becomes another agent's input.

Tools exposed to Claude:
  search_outputs     — find saved outputs by keyword/topic/agent
  get_output         — fetch full content of a specific output by ID
  get_recent_outputs — list the most recent outputs in this workspace
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger("claudeos.tools.system_tools")

# ── Claude API tool definitions ───────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "search_outputs",
        "description": (
            "Search saved outputs from any agent in this workspace. "
            "Use this to find reports, research, analyses, or any content "
            "produced by other agents. Search by keyword, topic, or title. "
            "Returns output IDs — use get_output to retrieve full content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keyword, topic, or phrase to search for in saved outputs.",
                },
                "agent_name": {
                    "type": "string",
                    "description": (
                        "Optional: filter by which agent produced the output. "
                        "E.g. 'research-agent', 'briefing-agent'."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (1–10). Default 5.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_output",
        "description": (
            "Fetch the complete content of a saved output by its ID. "
            "Use after search_outputs or get_recent_outputs to read the full text "
            "of a report, research output, or any saved agent result."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "output_id": {
                    "type": "string",
                    "description": "The output ID returned by search_outputs or get_recent_outputs.",
                },
            },
            "required": ["output_id"],
        },
    },
    {
        "name": "get_recent_outputs",
        "description": (
            "List the most recent outputs saved in this workspace. "
            "Use when you need to find what was recently produced without "
            "knowing the exact title. Optionally filter by agent name."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent outputs to list (1–10). Default 5.",
                    "default": 5,
                },
                "agent_name": {
                    "type": "string",
                    "description": "Optional: only show outputs from this agent.",
                },
            },
        },
    },
]

_TOOL_MAP = {t["name"]: t for t in TOOL_DEFINITIONS}


def get_definitions(tool_names: list[str]) -> list[dict]:
    return [_TOOL_MAP[n] for n in tool_names if n in _TOOL_MAP]


# ── Tool dispatcher ───────────────────────────────────────────────────────────

def call_tool(name: str, tool_input: dict, namespace: str = "global") -> str:
    """Execute a system tool. Namespace-scoped — agents only see their own workspace data."""
    try:
        if name == "search_outputs":
            return _search_outputs(
                query=tool_input.get("query", ""),
                namespace=namespace,
                agent_name=tool_input.get("agent_name", ""),
                limit=min(int(tool_input.get("limit", 5)), 10),
            )
        elif name == "get_output":
            return _get_output(
                output_id=tool_input.get("output_id", ""),
                namespace=namespace,
            )
        elif name == "get_recent_outputs":
            return _get_recent_outputs(
                namespace=namespace,
                limit=min(int(tool_input.get("limit", 5)), 10),
                agent_name=tool_input.get("agent_name", ""),
            )
        else:
            return f"Unknown system tool: {name}"
    except Exception as e:
        logger.warning("System tool %s failed: %s", name, e)
        return f"System tool error ({name}): {e}"


# ── Implementations ───────────────────────────────────────────────────────────

def _search_outputs(query: str, namespace: str, agent_name: str = "", limit: int = 5) -> str:
    from core.database import get_db

    if not query:
        return "Query is required for search_outputs."

    pattern = f"%{query}%"
    with get_db() as conn:
        if agent_name:
            rows = conn.execute(
                """SELECT o.id, o.title, o.content, o.created_at,
                          COALESCE(a.name, o.tags) as src_agent
                   FROM outputs o
                   LEFT JOIN agent_runs r ON r.id = o.agent_run_id
                   LEFT JOIN agents a ON a.id = r.agent_id
                   WHERE o.namespace = ? AND o.deleted_at IS NULL
                     AND LOWER(COALESCE(a.name,'')) LIKE LOWER(?)
                     AND (LOWER(o.title) LIKE LOWER(?) OR LOWER(o.content) LIKE LOWER(?))
                   ORDER BY o.created_at DESC LIMIT ?""",
                (namespace, f"%{agent_name}%", pattern, pattern, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT o.id, o.title, o.content, o.created_at,
                          COALESCE(a.name, '') as src_agent
                   FROM outputs o
                   LEFT JOIN agent_runs r ON r.id = o.agent_run_id
                   LEFT JOIN agents a ON a.id = r.agent_id
                   WHERE o.namespace = ? AND o.deleted_at IS NULL
                     AND (LOWER(o.title) LIKE LOWER(?) OR LOWER(o.content) LIKE LOWER(?))
                   ORDER BY o.created_at DESC LIMIT ?""",
                (namespace, pattern, pattern, limit),
            ).fetchall()

    if not rows:
        # Try broader match — maybe query terms are too specific
        with get_db() as conn:
            rows = conn.execute(
                """SELECT o.id, o.title, o.content, o.created_at,
                          COALESCE(a.name, '') as src_agent
                   FROM outputs o
                   LEFT JOIN agent_runs r ON r.id = o.agent_run_id
                   LEFT JOIN agents a ON a.id = r.agent_id
                   WHERE o.namespace = ? AND o.deleted_at IS NULL
                   ORDER BY o.created_at DESC LIMIT ?""",
                (namespace, limit),
            ).fetchall()
        if not rows:
            return (
                f"No outputs found in workspace '{namespace}'. "
                "No agent outputs have been saved yet — run an agent with save_output=true first."
            )
        # Return recent ones with a note
        note = f"No outputs matched '{query}'. Showing {len(rows)} most recent outputs instead:\n\n"
        return note + _format_output_list(rows)

    return f"Found {len(rows)} output(s) matching '{query}':\n\n" + _format_output_list(rows)


def _get_output(output_id: str, namespace: str) -> str:
    from core.database import get_db

    if not output_id:
        return "output_id is required."

    with get_db() as conn:
        row = conn.execute(
            """SELECT o.id, o.title, o.content, o.created_at, o.tags,
                      COALESCE(a.name, '') as src_agent
               FROM outputs o
               LEFT JOIN agent_runs r ON r.id = o.agent_run_id
               LEFT JOIN agents a ON a.id = r.agent_id
               WHERE o.id = ? AND o.namespace = ? AND o.deleted_at IS NULL""",
            (output_id, namespace),
        ).fetchone()

    if not row:
        # Try without namespace scoping to give a useful error
        with get_db() as conn:
            exists = conn.execute(
                "SELECT id, namespace FROM outputs WHERE id = ? AND deleted_at IS NULL",
                (output_id,),
            ).fetchone()
        if exists:
            return (
                f"Output '{output_id}' exists but belongs to namespace '{exists['namespace']}', "
                f"not '{namespace}'. You can only access outputs in your own workspace."
            )
        return f"Output '{output_id}' not found. Use search_outputs or get_recent_outputs to find valid IDs."

    tags = []
    if row["tags"]:
        try:
            tags = json.loads(row["tags"])
        except Exception:
            pass

    return "\n".join([
        f"# {row['title']}",
        f"**Produced by:** {row['src_agent'] or 'unknown agent'}",
        f"**Saved:** {(row['created_at'] or '')[:16]}",
        f"**ID:** {row['id']}",
        "---",
        row["content"] or "(empty content)",
    ])


def _get_recent_outputs(namespace: str, limit: int = 5, agent_name: str = "") -> str:
    from core.database import get_db

    with get_db() as conn:
        if agent_name:
            rows = conn.execute(
                """SELECT o.id, o.title, o.content, o.created_at,
                          COALESCE(a.name, '') as src_agent
                   FROM outputs o
                   LEFT JOIN agent_runs r ON r.id = o.agent_run_id
                   LEFT JOIN agents a ON a.id = r.agent_id
                   WHERE o.namespace = ? AND o.deleted_at IS NULL
                     AND LOWER(COALESCE(a.name,'')) LIKE LOWER(?)
                   ORDER BY o.created_at DESC LIMIT ?""",
                (namespace, f"%{agent_name}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT o.id, o.title, o.content, o.created_at,
                          COALESCE(a.name, '') as src_agent
                   FROM outputs o
                   LEFT JOIN agent_runs r ON r.id = o.agent_run_id
                   LEFT JOIN agents a ON a.id = r.agent_id
                   WHERE o.namespace = ? AND o.deleted_at IS NULL
                   ORDER BY o.created_at DESC LIMIT ?""",
                (namespace, limit),
            ).fetchall()

    if not rows:
        return (
            f"No outputs found in workspace '{namespace}'. "
            "Run an agent first and save_output will store results here."
        )

    return f"{len(rows)} most recent output(s) in this workspace:\n\n" + _format_output_list(rows)


def _format_output_list(rows) -> str:
    lines = []
    for r in rows:
        content_preview = (r["content"] or "").replace("\n", " ")[:250]
        lines.append(f"**ID:** `{r['id']}`")
        lines.append(f"**Title:** {r['title']}")
        lines.append(f"**Agent:** {r['src_agent'] or 'unknown'}")
        lines.append(f"**Date:** {(r['created_at'] or '')[:16]}")
        lines.append(f"**Preview:** {content_preview}...")
        lines.append("")
    lines.append("Call `get_output(output_id)` with the ID above to retrieve full content.")
    return "\n".join(lines)
