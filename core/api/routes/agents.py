"""Agent API routes — /api/v1/agents/*

Phase 10.1: SSE streaming endpoint
Phase 12.3: A2A Agent Cards per agent
"""
import json
from flask import Blueprint, Response, jsonify, request, g, stream_with_context

from agents import registry, dispatcher
from agents.schemas import AgentDispatchRequest
from core.auth import require_auth, effective_namespace
from core.utils import utcnow_str

agents_bp = Blueprint("agents", __name__, url_prefix="/api/v1/agents")


def _agent_dict(a) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "display_name": a.display_name,
        "description": a.description,
        "category": a.category,
        "model": a.model,
        "max_tokens": a.max_tokens,
        "temperature": a.temperature,
        "tools": a.tools,
        "namespace_lock": a.namespace_lock,
        "tags": a.tags,
        "enabled": a.enabled,
        "version": a.version,
    }


@agents_bp.get("")
@require_auth
def list_agents():
    category = request.args.get("category")
    enabled_only = request.args.get("enabled_only", "true").lower() == "true"
    agents = registry.list_agents(category=category, enabled_only=enabled_only)
    return jsonify({"agents": [_agent_dict(a) for a in agents], "count": len(agents)})


@agents_bp.get("/<agent_id>")
@require_auth
def get_agent(agent_id: str):
    agent = registry.get_by_id(agent_id) or registry.get_by_name(agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify(_agent_dict(agent))


@agents_bp.get("/<agent_name>/.well-known/agent.json")
@require_auth
def agent_card(agent_name: str):
    """A2A Agent Card — Phase 12.3.
    Returns a machine-readable Agent Card per the Agent-to-Agent protocol spec.
    External orchestrators can discover and delegate to ClaudeOS agents via this endpoint.
    """
    agent = registry.get_by_name(agent_name)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    from core.config import get_settings
    settings = get_settings()
    base_url = f"http://localhost:{settings.FLASK_PORT}/api/v1"

    card = {
        "name": agent.name,
        "displayName": agent.display_name,
        "description": agent.description,
        "version": agent.version,
        "category": agent.category,
        "tags": agent.tags,
        "capabilities": {
            "streaming": True,
            "multiTurn": True,
            "multiModal": True,
        },
        "input": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The task or question for the agent"},
                "namespace": {"type": "string", "description": "Target namespace context"},
                "context": {"type": "object", "description": "Optional key-value context dict"},
                "messages": {"type": "array", "description": "Prior conversation turns for multi-turn"},
            },
            "required": ["prompt"],
        },
        "output": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "model": {"type": "string"},
                "stop_reason": {"type": "string"},
            },
        },
        "endpoints": {
            "run": f"{base_url}/agents/{agent.name}/run",
            "stream": f"{base_url}/agents/{agent.name}/stream",
            "agentCard": f"{base_url}/agents/{agent.name}/.well-known/agent.json",
        },
        "auth": {
            "type": "bearer",
            "description": "JWT Bearer token or X-API-Key header",
        },
        "model": agent.model,
        "namespaceLock": agent.namespace_lock,
        "enabled": agent.enabled,
    }
    return jsonify(card)


@agents_bp.post("/<agent_name>/run")
@require_auth
def run_agent(agent_name: str):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    try:
        req = AgentDispatchRequest(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 422

    try:
        run_id = dispatcher.dispatch(agent_name, req, block=False)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403

    return jsonify({
        "run_id": run_id,
        "agent": agent_name,
        "namespace": req.namespace,
        "status": "pending",
        "poll_url": f"/api/v1/agents/runs/{run_id}",
    }), 202


@agents_bp.get("/<agent_name>/stream")
@require_auth
def stream_agent(agent_name: str):
    """SSE streaming endpoint — Phase 10.1.

    Returns Server-Sent Events with token-by-token streaming.
    Query params: prompt (required), namespace, context (JSON)

    SSE event format:
        data: {"type": "token", "text": "..."}
        data: {"type": "done", "tokens_in": N, "tokens_out": N}
        data: {"type": "error", "message": "..."}
    """
    prompt = request.args.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "prompt query param required"}), 400

    namespace = request.args.get("namespace", "global")
    try:
        context = json.loads(request.args.get("context", "{}"))
    except Exception:
        context = {}

    messages_raw = request.args.get("messages")
    try:
        messages = json.loads(messages_raw) if messages_raw else None
    except Exception:
        messages = None

    agent = registry.get_by_name(agent_name)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    if not agent.enabled:
        return jsonify({"error": "Agent is disabled"}), 400

    # Create run record so streaming runs appear in history + observability
    import time as _time
    from agents.executor import create_run_record, _trigger_eval, _bg_pool, _update_run_status
    from core.database import get_db
    run_id = create_run_record(
        agent_id=agent.id,
        namespace=namespace,
        prompt=prompt,
        context=context,
        session_id=None,
        triggered_by="user",
        workflow_run_id=None,
    )
    _update_run_status(run_id, "running")

    def _generate():
        full_text = []
        start = _time.monotonic()
        try:
            from agents.executor import execute_stream
            for chunk in execute_stream(
                agent_name=agent.name,
                system_prompt=agent.system_prompt,
                prompt=prompt,
                namespace=namespace,
                model=agent.model,
                max_tokens=agent.max_tokens,
                temperature=agent.temperature,
                context=context,
                messages=messages,
            ):
                if isinstance(chunk, dict) and chunk.get("_done"):
                    tokens_in = chunk["tokens_in"]
                    tokens_out = chunk["tokens_out"]
                    duration_ms = int((_time.monotonic() - start) * 1000)
                    text = "".join(full_text)
                    output = {"text": text, "model": agent.model, "stop_reason": "end_turn"}
                    with get_db() as conn:
                        conn.execute(
                            """UPDATE agent_runs SET output=?, status='done', tokens_in=?,
                               tokens_out=?, duration_ms=?, completed_at=? WHERE id=?""",
                            (json.dumps(output), tokens_in, tokens_out,
                             duration_ms, utcnow_str(), run_id),
                        )
                    _bg_pool.submit(_trigger_eval, run_id, prompt, text, "")
                    yield f"data: {json.dumps({'type': 'done', 'run_id': run_id, 'tokens_in': tokens_in, 'tokens_out': tokens_out})}\n\n".encode("utf-8")
                else:
                    full_text.append(chunk)
                    payload = json.dumps({"type": "token", "text": chunk})
                    yield f"data: {payload}\n\n".encode("utf-8")
        except Exception as e:
            duration_ms = int((_time.monotonic() - start) * 1000)
            with get_db() as conn:
                conn.execute(
                    "UPDATE agent_runs SET status='failed', error=?, duration_ms=?, completed_at=? WHERE id=?",
                    (str(e), duration_ms, utcnow_str(), run_id),
                )
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n".encode("utf-8")

    return Response(
        stream_with_context(_generate()),
        status=200,
        content_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
        direct_passthrough=True,
    )


@agents_bp.get("/runs/<run_id>")
@require_auth
def get_run(run_id: str):
    run = dispatcher.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(run)


@agents_bp.get("/<agent_id>/runs")
@require_auth
def list_agent_runs(agent_id: str):
    agent = registry.get_by_id(agent_id) or registry.get_by_name(agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    limit = min(int(request.args.get("limit", 50)), 200)
    runs = dispatcher.list_runs(agent_id=agent.id, limit=limit)
    return jsonify({"runs": runs, "count": len(runs)})


@agents_bp.post("/runs/<run_id>/cancel")
@require_auth
def cancel_run(run_id: str):
    cancelled = dispatcher.cancel_run(run_id)
    if not cancelled:
        return jsonify({"error": "Run not found or already complete"}), 404
    return jsonify({"cancelled": run_id})


@agents_bp.delete("/runs/<run_id>")
@require_auth
def delete_run(run_id: str):
    from core.database import get_db
    run = dispatcher.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    # namespace scoping — clients can only delete their own
    ns = effective_namespace(run.get("namespace"))
    if g.user_role not in ("admin", "operator") and run.get("namespace") != g.user_namespace:
        return jsonify({"error": "Forbidden"}), 403
    with get_db() as conn:
        conn.execute("DELETE FROM agent_runs WHERE id=?", (run_id,))
    return jsonify({"deleted": run_id})


@agents_bp.get("/runs")
@require_auth
def list_runs():
    namespace = effective_namespace(request.args.get("namespace"))
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 200)
    runs = dispatcher.list_runs(namespace=namespace, status=status, limit=limit)
    return jsonify({"runs": runs, "count": len(runs)})


@agents_bp.get("/<agent_name>/conversations")
@require_auth
def list_conversations(agent_name: str):
    """List multi-turn conversations for an agent — Phase 13.4."""
    namespace = effective_namespace(request.args.get("namespace"))
    limit = min(int(request.args.get("limit", 20)), 100)
    from core.database import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, session_id, namespace, username, created_at, updated_at
               FROM agent_conversations
               WHERE agent_name=? AND namespace=?
               ORDER BY updated_at DESC LIMIT ?""",
            (agent_name, namespace or "global", limit),
        ).fetchall()
    return jsonify({"conversations": [dict(r) for r in rows], "count": len(rows)})
