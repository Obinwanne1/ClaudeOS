"""Output Manager REST API routes."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, Response

from core.api.auth import require_api_key

outputs_bp = Blueprint("outputs", __name__, url_prefix="/api/v1/outputs")


@outputs_bp.get("")
@require_api_key
def list_outputs():
    from outputs.manager import list_outputs as _list
    namespace = request.args.get("namespace")
    output_type = request.args.get("type")
    tags = request.args.getlist("tag")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    outputs = _list(namespace=namespace, output_type=output_type, tags=tags or None, limit=limit, offset=offset)
    return jsonify([_out_dict(o) for o in outputs])


@outputs_bp.post("")
@require_api_key
def save_output():
    from outputs.manager import save
    from outputs.schemas import OutputSave
    body = request.get_json(silent=True) or {}
    try:
        data = OutputSave(**body)
    except Exception as e:
        return jsonify({"error": str(e)}), 422
    out = save(
        namespace=data.namespace,
        title=data.title,
        content=data.content,
        output_type=data.output_type,
        format=data.format,
        tags=data.tags,
        agent_run_id=data.agent_run_id,
        workflow_run_id=data.workflow_run_id,
        project_id=data.project_id,
        summary=data.summary,
    )
    return jsonify(_out_dict(out)), 201


@outputs_bp.get("/search")
@require_api_key
def search_outputs():
    from outputs.manager import search
    query = request.args.get("q", "")
    namespace = request.args.get("namespace")
    limit = min(int(request.args.get("limit", 20)), 100)
    if not query:
        return jsonify({"error": "q parameter required"}), 400
    results = search(query, namespace=namespace, limit=limit)
    return jsonify([r.model_dump() for r in results])


@outputs_bp.get("/stats")
@require_api_key
def output_stats():
    from outputs.manager import get_stats
    namespace = request.args.get("namespace")
    return jsonify(get_stats(namespace=namespace))


@outputs_bp.get("/<output_id>")
@require_api_key
def get_output(output_id: str):
    from outputs.manager import get_by_id
    out = get_by_id(output_id)
    if not out:
        return jsonify({"error": "Output not found"}), 404
    return jsonify(_out_dict(out))


@outputs_bp.get("/<output_id>/content")
@require_api_key
def get_content(output_id: str):
    """Return raw content as plain text."""
    from outputs.manager import export_text
    content = export_text(output_id)
    if content is None:
        return jsonify({"error": "Output not found"}), 404
    return Response(content, mimetype="text/plain; charset=utf-8")


@outputs_bp.get("/<output_id>/export")
@require_api_key
def export_output(output_id: str):
    from outputs.manager import get_by_id, export_json
    fmt = request.args.get("format", "json")
    if fmt == "json":
        data = export_json(output_id)
        if not data:
            return jsonify({"error": "Output not found"}), 404
        return jsonify(data)
    elif fmt in ("markdown", "text"):
        from outputs.manager import export_text
        content = export_text(output_id)
        if content is None:
            return jsonify({"error": "Output not found"}), 404
        mime = "text/markdown" if fmt == "markdown" else "text/plain"
        out = get_by_id(output_id)
        import re as _re
        safe = _re.sub(r"[^\w\s-]", "", out.title[:40]).strip().replace(" ", "_")
        ext = "md" if fmt == "markdown" else "txt"
        fname = f"{safe or output_id[:8]}.{ext}"
        return Response(
            content,
            mimetype=mime,
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )
    return jsonify({"error": f"Unknown format: {fmt}"}), 400


@outputs_bp.delete("/<output_id>")
@require_api_key
def delete_output(output_id: str):
    from outputs.manager import delete
    if not delete(output_id):
        return jsonify({"error": "Output not found"}), 404
    return jsonify({"deleted": output_id})


# ── helpers ───────────────────────────────────────────────────────────────────

def _out_dict(o) -> dict:
    return {
        "id": o.id,
        "namespace": o.namespace,
        "title": o.title,
        "summary": o.summary,
        "output_type": o.output_type,
        "format": o.format,
        "tags": o.tags,
        "size_bytes": o.size_bytes,
        "file_path": o.file_path,
        "agent_run_id": o.agent_run_id,
        "workflow_run_id": o.workflow_run_id,
        "created_at": o.created_at,
    }
