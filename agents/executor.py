"""Claude API executor — the core of the agent system.

Every agent call goes through here. Responsibilities:
1. Inject namespace memory context into system prompt
2. Call Claude API (claude-sonnet-4-6)
3. Log token usage to agent_runs table
4. Auto-save output to Output Manager if save_output=True
5. Write run result back to agent_runs
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import anthropic

from core.config import get_settings
from core.database import get_db
from core.utils import new_id, utcnow_str
from memory import engine as memory_engine

logger = logging.getLogger("claudeos.agents.executor")

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=get_settings().ANTHROPIC_API_KEY)
    return _client


def execute(
    run_id: str,
    agent_name: str,
    system_prompt: str,
    prompt: str,
    namespace: str,
    model: str,
    max_tokens: int,
    temperature: float,
    context: dict,
    session_id: Optional[str],
    triggered_by: str,
    workflow_run_id: Optional[str],
    save_output: bool,
    agent_id: str,
) -> dict:
    """Execute an agent run. Returns result dict with output, tokens, status."""

    # Build enriched system prompt with memory context
    mem_context = memory_engine.get_agent_context(namespace, min_confidence=0.8)
    system = _build_system_prompt(system_prompt, mem_context, namespace, context)

    # Mark as running
    _update_run_status(run_id, "running")
    start = time.monotonic()

    try:
        client = _get_client()
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        duration_ms = int((time.monotonic() - start) * 1000)
        output_text = response.content[0].text if response.content else ""
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        output = {
            "text": output_text,
            "model": response.model,
            "stop_reason": response.stop_reason,
        }

        # Save to agent_runs
        with get_db() as conn:
            conn.execute(
                """UPDATE agent_runs SET
                   output=?, status='done', tokens_in=?, tokens_out=?,
                   duration_ms=?, completed_at=?
                   WHERE id=?""",
                (json.dumps(output), tokens_in, tokens_out, duration_ms, utcnow_str(), run_id),
            )

        # Auto-save to Output Manager
        if save_output and output_text.strip():
            _save_output(
                namespace=namespace,
                agent_run_id=run_id,
                workflow_run_id=workflow_run_id,
                title=f"{agent_name} — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                content=output_text,
                agent_name=agent_name,
            )

        _log_event("agent_run_complete", namespace, {
            "agent": agent_name,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "duration_ms": duration_ms,
        })

        logger.info("Agent %s completed in %dms (%d+%d tokens)", agent_name, duration_ms, tokens_in, tokens_out)
        return {"status": "done", "output": output, "tokens_in": tokens_in, "tokens_out": tokens_out, "duration_ms": duration_ms}

    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        error_msg = str(e)
        logger.error("Agent %s failed: %s", agent_name, error_msg)
        with get_db() as conn:
            conn.execute(
                "UPDATE agent_runs SET status='failed', error=?, duration_ms=?, completed_at=? WHERE id=?",
                (error_msg, duration_ms, utcnow_str(), run_id),
            )
        return {"status": "failed", "error": error_msg, "duration_ms": duration_ms}


def create_run_record(
    agent_id: str,
    namespace: str,
    prompt: str,
    context: dict,
    session_id: Optional[str],
    triggered_by: str,
    workflow_run_id: Optional[str],
) -> str:
    """Insert a pending agent_run record. Returns run_id."""
    run_id = new_id()
    input_data = json.dumps({"prompt": prompt, "context": context})
    with get_db() as conn:
        conn.execute(
            """INSERT INTO agent_runs
               (id, agent_id, session_id, namespace, input, status, triggered_by, workflow_run_id, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
            (run_id, agent_id, session_id, namespace, input_data, triggered_by, workflow_run_id, utcnow_str()),
        )
    return run_id


def _build_system_prompt(base_prompt: str, mem_context: str, namespace: str, extra_context: dict) -> str:
    parts = [base_prompt]
    if mem_context:
        parts.append(mem_context)
    if extra_context:
        ctx_lines = [f"## Additional Context"]
        for k, v in extra_context.items():
            ctx_lines.append(f"- {k}: {v}")
        parts.append("\n".join(ctx_lines))
    parts.append(f"\n## Operating Context\nNamespace: {namespace}\nDate: {utcnow_str()[:10]}")
    return "\n\n".join(parts)


def _update_run_status(run_id: str, status: str) -> None:
    with get_db() as conn:
        conn.execute("UPDATE agent_runs SET status=? WHERE id=?", (status, run_id))


def _save_output(
    namespace: str,
    agent_run_id: str,
    workflow_run_id: Optional[str],
    title: str,
    content: str,
    agent_name: str,
) -> None:
    try:
        from outputs.manager import save as save_output
        save_output(
            namespace=namespace,
            title=title,
            content=content,
            output_type="report",
            agent_run_id=agent_run_id,
            workflow_run_id=workflow_run_id,
            tags=[agent_name, namespace],
        )
    except ImportError:
        # Output Manager not yet built (Phase 6) — save inline to DB only
        _save_output_inline(namespace, agent_run_id, title, content, agent_name)
    except Exception as e:
        logger.warning("Failed to save output: %s", e)


def _save_output_inline(namespace: str, agent_run_id: str, title: str, content: str, agent_name: str) -> None:
    """Fallback: save directly to outputs table without full Output Manager."""
    import json as _json
    output_id = new_id()
    now = utcnow_str()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO outputs
               (id, namespace, agent_run_id, type, title, content, format, tags, size_bytes, created_at, updated_at)
               VALUES (?, ?, ?, 'report', ?, ?, 'markdown', ?, ?, ?, ?)""",
            (
                output_id, namespace, agent_run_id, title, content,
                _json.dumps([agent_name, namespace]),
                len(content.encode("utf-8")), now, now,
            ),
        )


def _log_event(event_type: str, namespace: str, payload: dict) -> None:
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO system_events(id, event_type, namespace, payload) VALUES (?, ?, ?, ?)",
                (new_id(), event_type, namespace, json.dumps(payload)),
            )
    except Exception:
        pass
