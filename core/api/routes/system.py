"""System routes: /health, /system/status, /system/stats, /system/events."""
import platform
from pathlib import Path
from flask import Blueprint, jsonify, request

from core.config import get_settings
from core.database import get_db
from core.utils import utcnow_str

system_bp = Blueprint("system", __name__, url_prefix="/api/v1")


@system_bp.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "version": get_settings().CLAUDEOS_VERSION,
        "env": get_settings().CLAUDEOS_ENV,
        "timestamp": utcnow_str(),
    })


@system_bp.get("/system/status")
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
def stats():
    tables = ["memory_entries", "agents", "agent_runs", "workflows", "workflow_runs",
              "outputs", "namespaces", "projects", "system_events"]
    try:
        union_sql = " UNION ALL ".join(
            f"SELECT '{t}' AS tbl, COUNT(*) AS cnt FROM {t}" for t in tables
        )
        with get_db() as conn:
            rows = conn.execute(union_sql).fetchall()
        counts = {row[0]: row[1] for row in rows}
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"timestamp": utcnow_str(), "counts": counts})


@system_bp.get("/system/events")
def events():
    limit = min(int(request.args.get("limit", 50)), 200)
    severity = request.args.get("severity")
    namespace = request.args.get("namespace")

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
