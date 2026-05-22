"""System routes: /health, /system/status, /system/stats, /system/events."""
import platform
from pathlib import Path
from flask import Blueprint, jsonify, request

from core.config import get_settings
from core.database import get_db
from core.utils import utcnow_str
from core.auth import require_auth, effective_namespace

system_bp = Blueprint("system", __name__, url_prefix="/api/v1")


@system_bp.get("/health")
def health():
    s = get_settings()
    return jsonify({
        "status": "ok",
        "version": s.CLAUDEOS_VERSION,
        "env": s.CLAUDEOS_ENV,
        "timestamp": utcnow_str(),
    })


@system_bp.get("/system/status")
@require_auth
def status():
    settings = get_settings()
    db_ok = False
    db_path = str(settings.sqlite_path)
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    db_size_kb = 0
    if Path(db_path).exists():
        db_size_kb = round(Path(db_path).stat().st_size / 1024, 1)

    return jsonify({
        "status": "ok",
        "version": settings.CLAUDEOS_VERSION,
        "env": settings.CLAUDEOS_ENV,
        "timestamp": utcnow_str(),
        "platform": platform.system(),
        "python": platform.python_version(),
        "services": {
            "api": {"status": "ok", "port": settings.FLASK_PORT},
            "database": {"status": "ok" if db_ok else "error", "path": db_path, "size_kb": db_size_kb},
            "chromadb": {"status": "ok", "path": str(settings.chromadb_path)},
        },
    })


@system_bp.get("/system/stats")
@require_auth
def stats():
    ns = effective_namespace(None)
    try:
        with get_db() as conn:
            if ns:
                # Scoped counts — client/viewer see only their namespace
                counts = {
                    "memory_entries": conn.execute("SELECT COUNT(*) FROM memory_entries WHERE namespace=?", (ns,)).fetchone()[0],
                    "agents":         conn.execute("SELECT COUNT(*) FROM agents WHERE enabled=1").fetchone()[0],
                    "agent_runs":     conn.execute("SELECT COUNT(*) FROM agent_runs WHERE namespace=?", (ns,)).fetchone()[0],
                    "workflows":      conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0],
                    "outputs":        conn.execute("SELECT COUNT(*) FROM outputs WHERE namespace=?", (ns,)).fetchone()[0],
                    "projects":       conn.execute("SELECT COUNT(*) FROM projects WHERE namespace=?", (ns,)).fetchone()[0],
                    "open_tickets":   conn.execute(
                        "SELECT COUNT(*) FROM tickets WHERE namespace=? AND status NOT IN ('resolved','closed','completed')", (ns,)
                    ).fetchone()[0],
                }
            else:
                # Global counts — admin/operator see everything
                tables = ["memory_entries", "agents", "agent_runs", "workflows", "workflow_runs",
                          "outputs", "namespaces", "projects", "system_events"]
                union_sql = " UNION ALL ".join(
                    f"SELECT '{t}' AS tbl, COUNT(*) AS cnt FROM {t}" for t in tables
                )
                rows = conn.execute(union_sql).fetchall()
                counts = {row[0]: row[1] for row in rows}
                counts["open_tickets"] = conn.execute(
                    "SELECT COUNT(*) FROM tickets WHERE status NOT IN ('resolved','closed','completed')"
                ).fetchone()[0]
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"timestamp": utcnow_str(), "counts": counts, "namespace": ns})


@system_bp.get("/system/events")
@require_auth
def events():
    limit = min(int(request.args.get("limit", 50)), 200)
    severity = request.args.get("severity")
    # effective_namespace forces client/viewer to their own namespace
    namespace = effective_namespace(request.args.get("namespace"))

    conditions, params = [], []
    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if namespace:
        conditions.append("namespace = ?")
        params.append(namespace)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM system_events {where} ORDER BY created_at DESC LIMIT ?", params
        ).fetchall()

    return jsonify({
        "events": [dict(r) for r in rows],
        "count": len(rows),
    })
