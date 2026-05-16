"""Workflow Engine REST API routes."""
from __future__ import annotations

import threading
from flask import Blueprint, jsonify, request

from core.auth import require_auth, effective_namespace
require_api_key = require_auth  # alias
from core.utils import utcnow_str

workflows_bp = Blueprint("workflows", __name__, url_prefix="/api/v1/workflows")


@workflows_bp.get("")
@require_api_key
def list_workflows():
    from workflows.registry import list_workflows as _list
    trigger_type = request.args.get("trigger_type")
    namespace = request.args.get("namespace")
    enabled_only = request.args.get("enabled", "true").lower() == "true"
    workflows = _list(trigger_type=trigger_type, namespace=namespace, enabled_only=enabled_only)
    return jsonify([_wf_summary(wf) for wf in workflows])


@workflows_bp.get("/<name>")
@require_api_key
def get_workflow(name: str):
    from workflows.registry import get_by_name
    wf = get_by_name(name)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
    return jsonify(_wf_detail(wf))


@workflows_bp.post("/<name>/run")
@require_api_key
def trigger_workflow(name: str):
    """Trigger a workflow run immediately. Returns run_id."""
    from workflows.registry import get_by_name
    from workflows import pipeline

    wf = get_by_name(name)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
    if not wf.enabled:
        return jsonify({"error": "Workflow is disabled"}), 400

    body = request.get_json(silent=True) or {}
    context = body.get("context", {})
    namespace = body.get("namespace") or wf.namespace
    context["namespace"] = namespace

    run_id = pipeline.create_run_record(wf.id, "user", context)

    def _run():
        pipeline.run(wf, run_id, context, triggered_by="user")

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return jsonify({"run_id": run_id, "status": "running", "workflow": name}), 202


@workflows_bp.get("/<name>/runs")
@require_api_key
def get_workflow_runs(name: str):
    from workflows.registry import get_by_name
    from workflows.pipeline import list_runs
    wf = get_by_name(name)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
    limit = int(request.args.get("limit", 20))
    status = request.args.get("status")
    runs = list_runs(workflow_id=wf.id, status=status, limit=limit)
    return jsonify(runs)


@workflows_bp.get("/runs/all")
@require_api_key
def list_all_runs():
    from workflows.pipeline import list_runs
    limit = int(request.args.get("limit", 30))
    status = request.args.get("status")
    runs = list_runs(status=status, limit=limit)
    return jsonify(runs)


@workflows_bp.get("/runs/<run_id>")
@require_api_key
def get_run(run_id: str):
    from workflows.pipeline import get_run as _get_run
    run = _get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(run)


@workflows_bp.get("/scheduler/jobs")
@require_api_key
def list_scheduler_jobs():
    from workflows.scheduler import list_scheduled_jobs
    return jsonify(list_scheduled_jobs())


@workflows_bp.post("/scheduler/reload")
@require_api_key
def reload_scheduler():
    """Reload scheduled workflows from DB (after enable/disable changes)."""
    from workflows.scheduler import get_scheduler, _load_scheduled_workflows
    sched = get_scheduler()
    if not sched:
        return jsonify({"error": "Scheduler not running"}), 503
    # Remove all workflow jobs
    for job in sched.get_jobs():
        if job.id.startswith("wf_"):
            sched.remove_job(job.id)
    _load_scheduled_workflows()
    return jsonify({"status": "reloaded", "jobs": list_scheduled_jobs()})


@workflows_bp.patch("/<name>")
@require_api_key
def update_workflow(name: str):
    """Enable/disable a workflow."""
    from workflows.registry import get_by_name, upsert
    from workflows.scheduler import schedule_workflow, unschedule_workflow
    wf = get_by_name(name)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
    body = request.get_json(silent=True) or {}
    if "enabled" in body:
        wf.enabled = bool(body["enabled"])
        upsert(wf)
        if wf.trigger_type == "schedule":
            if wf.enabled:
                schedule_workflow(wf.name, wf.trigger_spec)
            else:
                unschedule_workflow(wf.name)
    return jsonify(_wf_summary(wf))


# ── helpers ───────────────────────────────────────────────────────────────────

def _wf_summary(wf) -> dict:
    return {
        "id": wf.id,
        "name": wf.name,
        "display_name": wf.display_name,
        "description": wf.description,
        "trigger_type": wf.trigger_type,
        "trigger_spec": wf.trigger_spec,
        "namespace": wf.namespace,
        "enabled": wf.enabled,
        "step_count": len(wf.steps),
    }


def _wf_detail(wf) -> dict:
    d = _wf_summary(wf)
    d["steps"] = [s.model_dump() for s in wf.steps]
    return d
