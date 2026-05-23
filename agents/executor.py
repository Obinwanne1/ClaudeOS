"""Claude API executor — the core of the agent system.

Every agent call goes through here. Responsibilities:
1. Inject namespace memory context (tiered: summary + recent + relevant)
2. Call Claude API — streaming or blocking
3. LLM-as-Judge async quality scoring
4. Log token usage to agent_runs table
5. Auto-save output to Output Manager if save_output=True
6. Support multi-turn conversations (messages list)
7. Support multimodal content (images as base64 blocks)
"""
from __future__ import annotations

import base64
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Generator, Optional

from core.config import get_settings
from core.database import get_db
from core.utils import new_id, utcnow_str
from memory import engine as memory_engine

logger = logging.getLogger("claudeos.agents.executor")

_client = None  # anthropic.Anthropic — lazy, avoids 4s import at startup
_client_lock = threading.Lock()

# Background pool for fire-and-forget event log inserts + eval jobs.
_bg_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="exec-bg")


def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:  # double-checked locking
                import anthropic
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
    messages: Optional[list] = None,
    images: Optional[list[dict]] = None,
) -> dict:
    """Execute an agent run. Returns result dict with output, tokens, status.

    Args:
        messages: optional list of prior turns [{role, content}] for multi-turn
        images:   optional list of {data: base64_str, media_type: str}
    """
    # Build tiered context injection
    mem_context = _build_memory_context(namespace, prompt)
    system = _build_system_blocks(system_prompt, mem_context, namespace, context)

    # Build messages list (multi-turn support)
    api_messages = _build_messages(prompt, messages, images)

    # Mark as running
    _update_run_status(run_id, "running")
    start = time.monotonic()

    try:
        import anthropic
        client = _get_client()
        last_exc: Exception = RuntimeError("no attempts made")
        response = None

        for attempt in range(3):
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=api_messages,
                    timeout=120.0,
                )
                break
            except anthropic.APIStatusError as exc:
                last_exc = exc
                if exc.status_code == 529 and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise
            except anthropic.APITimeoutError as exc:
                last_exc = exc
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise
        else:
            raise last_exc

        duration_ms = int((time.monotonic() - start) * 1000)
        output_text = response.content[0].text if response.content else ""
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
        cache_created = getattr(response.usage, "cache_creation_input_tokens", 0) or 0

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

        # Async LLM-as-Judge evaluation
        _bg_pool.submit(_trigger_eval, run_id, prompt, output_text, mem_context)

        _log_event("agent_run_complete", namespace, {
            "agent": agent_name,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cache_read": cache_read,
            "cache_created": cache_created,
            "duration_ms": duration_ms,
        })

        logger.info(
            "Agent %s completed in %dms (%d+%d tokens, cache_read=%d cache_created=%d)",
            agent_name, duration_ms, tokens_in, tokens_out, cache_read, cache_created,
        )
        return {
            "status": "done", "output": output,
            "tokens_in": tokens_in, "tokens_out": tokens_out,
            "cache_read": cache_read, "cache_created": cache_created,
            "duration_ms": duration_ms,
        }

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


def execute_stream(
    agent_name: str,
    system_prompt: str,
    prompt: str,
    namespace: str,
    model: str,
    max_tokens: int,
    temperature: float,
    context: dict,
    messages: Optional[list] = None,
    images: Optional[list[dict]] = None,
) -> Generator[str, None, None]:
    """Streaming version — yields text chunks as they arrive from Claude API.

    Does NOT write to agent_runs (caller manages run_id separately via execute()).
    Used by the SSE Flask endpoint for real-time dashboard display.
    """
    mem_context = _build_memory_context(namespace, prompt)
    system = _build_system_blocks(system_prompt, mem_context, namespace, context)
    api_messages = _build_messages(prompt, messages, images)

    import anthropic
    client = _get_client()

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=api_messages,
        timeout=120.0,
    ) as stream:
        for text_chunk in stream.text_stream:
            yield text_chunk


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


def save_conversation_turn(
    conversation_id: str,
    turn_index: int,
    role: str,
    content: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    duration_ms: Optional[int] = None,
    run_id: Optional[str] = None,
) -> None:
    """Persist a single conversation turn to the DB."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO agent_conversation_turns
               (id, conversation_id, turn_index, role, content, tokens_in, tokens_out, duration_ms, run_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_id(), conversation_id, turn_index, role, content,
             tokens_in, tokens_out, duration_ms, run_id),
        )
        conn.execute(
            "UPDATE agent_conversations SET updated_at=? WHERE id=?",
            (utcnow_str(), conversation_id),
        )


def get_or_create_conversation(
    session_id: str,
    agent_name: str,
    namespace: str,
    username: str = "",
) -> str:
    """Return existing conversation_id for this session+agent, or create new one."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM agent_conversations WHERE session_id=? AND agent_name=?",
            (session_id, agent_name),
        ).fetchone()
        if row:
            return row["id"]
        conv_id = new_id()
        conn.execute(
            """INSERT INTO agent_conversations(id, session_id, agent_name, namespace, username)
               VALUES (?, ?, ?, ?, ?)""",
            (conv_id, session_id, agent_name, namespace, username),
        )
        return conv_id


def get_conversation_turns(conversation_id: str) -> list[dict]:
    """Return all turns for a conversation ordered by turn_index."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT role, content, tokens_in, tokens_out, duration_ms, run_id, created_at
               FROM agent_conversation_turns
               WHERE conversation_id = ?
               ORDER BY turn_index ASC""",
            (conversation_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_memory_context(namespace: str, query: str) -> str:
    """Build tiered context — falls back to flat context if context_builder unavailable."""
    try:
        from memory.context_builder import build_context
        return build_context(namespace, query, max_tokens=1500)
    except Exception:
        return memory_engine.get_agent_context(namespace, min_confidence=0.8)


def _build_messages(
    prompt: str,
    prior_messages: Optional[list],
    images: Optional[list[dict]],
) -> list[dict]:
    """Build the messages array for the Claude API call."""
    if prior_messages:
        # Multi-turn: append new user message to history
        messages = list(prior_messages)
    else:
        messages = []

    # Build current user message content
    content: list = []
    if images:
        for img in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.get("media_type", "image/png"),
                    "data": img["data"],
                },
            })
    content.append({"type": "text", "text": prompt})

    messages.append({"role": "user", "content": content if len(content) > 1 else prompt})
    return messages


def _build_system_blocks(base_prompt: str, mem_context: str, namespace: str, extra_context: dict) -> list:
    """Return system prompt as content blocks with cache_control on the stable prefix.

    Block 0 (cached): base agent system prompt — stable across all runs for this agent.
    Block 1 (dynamic): memory context + extra context + namespace/date — changes per call.
    """
    blocks = [
        {
            "type": "text",
            "text": base_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    dynamic_parts = []
    if mem_context:
        dynamic_parts.append(mem_context)
    if extra_context:
        ctx_lines = ["## Additional Context"]
        for k, v in extra_context.items():
            ctx_lines.append(f"- {k}: {v}")
        dynamic_parts.append("\n".join(ctx_lines))
    dynamic_parts.append(f"\n## Operating Context\nNamespace: {namespace}\nDate: {utcnow_str()[:10]}")

    blocks.append({"type": "text", "text": "\n\n".join(dynamic_parts)})
    return blocks


def _trigger_eval(run_id: str, prompt: str, output_text: str, context: str) -> None:
    """Fire LLM-as-Judge evaluation in background."""
    try:
        from agents.evaluator import evaluate_async
        evaluate_async(run_id, prompt, output_text, context)
    except Exception as e:
        logger.debug("Eval trigger failed: %s", e)


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
        _save_output_inline(namespace, agent_run_id, title, content, agent_name)
    except Exception as e:
        logger.warning("Failed to save output: %s", e)


def _save_output_inline(namespace: str, agent_run_id: str, title: str, content: str, agent_name: str) -> None:
    output_id = new_id()
    now = utcnow_str()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO outputs
               (id, namespace, agent_run_id, type, title, content, format, tags, size_bytes, created_at, updated_at)
               VALUES (?, ?, ?, 'report', ?, ?, 'markdown', ?, ?, ?, ?)""",
            (
                output_id, namespace, agent_run_id, title, content,
                json.dumps([agent_name, namespace]),
                len(content.encode("utf-8")), now, now,
            ),
        )


def _log_event(event_type: str, namespace: str, payload: dict) -> None:
    _bg_pool.submit(_do_log_event, event_type, namespace, payload)


def _do_log_event(event_type: str, namespace: str, payload: dict) -> None:
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO system_events(id, event_type, namespace, payload) VALUES (?, ?, ?, ?)",
                (new_id(), event_type, namespace, json.dumps(payload)),
            )
    except Exception as e:
        logger.warning("_log_event failed (%s): %s", event_type, e)
