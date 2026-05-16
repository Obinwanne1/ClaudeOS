"""Agent API routes — /api/v1/agents/*"""
import json
from flask import Blueprint, jsonify, request, g

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


@agents_bp.get("/runs")
@require_auth
def list_runs():
    namespace = request.args.get("namespace")
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 200)
    runs = dispatcher.list_runs(namespace=namespace, status=status, limit=limit)
    return jsonify({"runs": runs, "count": len(runs)})
