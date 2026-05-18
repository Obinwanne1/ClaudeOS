"""Memory API routes — /api/v1/memory/*"""
from flask import Blueprint, jsonify, request, g

from memory import engine
from memory.schemas import (
    MemoryEntryCreate,
    MemoryEntryUpdate,
    MemorySearchRequest,
)
from core.auth import require_auth, effective_namespace
from core.utils import utcnow_str

memory_bp = Blueprint("memory", __name__, url_prefix="/api/v1/memory")


def _entry_dict(e) -> dict:
    return {
        "id": e.id,
        "namespace": e.namespace,
        "category": e.category,
        "key": e.key,
        "value": e.value,
        "source": e.source,
        "agent_id": e.agent_id,
        "session_id": e.session_id,
        "tags": e.tags,
        "confidence": e.confidence,
        "expires_at": e.expires_at.isoformat() if e.expires_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


@memory_bp.get("")
@require_auth
def list_memory():
    namespace = effective_namespace(request.args.get("namespace"))
    category = request.args.get("category")
    min_confidence = float(request.args.get("min_confidence", 0.0))
    limit = min(int(request.args.get("limit", 100)), 500)
    offset = int(request.args.get("offset", 0))

    entries = engine.list_entries(namespace, category, min_confidence, limit=limit, offset=offset)
    return jsonify({
        "entries": [_entry_dict(e) for e in entries],
        "count": len(entries),
    })


@memory_bp.post("")
@require_auth
def write_memory():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    # Enforce namespace for client/viewer roles
    forced_ns = effective_namespace(data.get("namespace"))
    if forced_ns:
        data["namespace"] = forced_ns

    try:
        entry_create = MemoryEntryCreate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 422

    entry = engine.write(
        namespace=entry_create.namespace,
        category=entry_create.category,
        key=entry_create.key,
        value=entry_create.value,
        source=entry_create.source,
        agent_id=entry_create.agent_id,
        session_id=entry_create.session_id,
        tags=entry_create.tags,
        confidence=entry_create.confidence,
        expires_at=entry_create.expires_at,
    )
    return jsonify(_entry_dict(entry)), 201


@memory_bp.delete("/bulk")
@require_auth
def bulk_delete_memory():
    ids = (request.get_json(silent=True) or {}).get("ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "ids list required"}), 422
    deleted, failed = [], []
    for eid in ids:
        (deleted if engine.delete(eid) else failed).append(eid)
    return jsonify({"deleted": deleted, "failed": failed, "count": len(deleted)})


@memory_bp.get("/<entry_id>")
@require_auth
def get_memory(entry_id: str):
    entry = engine.get_by_id(entry_id)
    if not entry:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_entry_dict(entry))


@memory_bp.put("/<entry_id>")
@require_auth
def update_memory(entry_id: str):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    try:
        update_data = MemoryEntryUpdate(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 422

    entry = engine.update(entry_id, update_data)
    if not entry:
        return jsonify({"error": "Not found"}), 404
    return jsonify(_entry_dict(entry))


@memory_bp.delete("/<entry_id>")
@require_auth
def delete_memory(entry_id: str):
    deleted = engine.delete(entry_id)
    if not deleted:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"deleted": entry_id})


@memory_bp.post("/search")
@require_auth
def search_memory():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    # Enforce namespace for client/viewer
    forced_ns = effective_namespace(data.get("namespace"))
    if forced_ns:
        data["namespace"] = forced_ns

    try:
        req = MemorySearchRequest(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 422

    entries = engine.search(req)
    return jsonify({
        "query": req.query,
        "mode": req.mode,
        "namespace": req.namespace,
        "results": [_entry_dict(e) for e in entries],
        "count": len(entries),
    })


@memory_bp.post("/import")
@require_auth
def import_memory():
    from pathlib import Path
    from core.config import get_settings
    from memory.importer import import_directory

    settings = get_settings()
    memory_dir = Path(settings.CLAUDE_MEMORY_PATH)
    namespace = request.args.get("namespace", "global")

    if not memory_dir.exists():
        return jsonify({"error": f"Memory directory not found: {memory_dir}"}), 400

    results = import_directory(memory_dir, namespace=namespace)
    total = sum(results.values())
    return jsonify({
        "imported": total,
        "total_files": len(results),
        "results": results,
        "timestamp": utcnow_str(),
    })


@memory_bp.get("/namespaces")
@require_auth
def list_namespaces():
    counts = engine.namespace_counts()
    return jsonify({"namespaces": counts})


@memory_bp.delete("/expire")
@require_auth
def expire_memory():
    count = engine.expire_stale()
    return jsonify({"expired": count, "timestamp": utcnow_str()})


@memory_bp.get("/context/<namespace>")
@require_auth
def agent_context(namespace: str):
    min_confidence = float(request.args.get("min_confidence", 0.8))
    context_str = engine.get_agent_context(namespace, min_confidence)
    return jsonify({"namespace": namespace, "context": context_str})
