"""System routes: /health, /system/status, /system/stats, /system/events."""
import platform
from pathlib import Path
from flask import Blueprint, jsonify, request

from core.config import get_settings
from core.database import get_db
from core.utils import utcnow_str
from core.auth import require_auth, effective_namespace

system_bp = Blueprint("system", __name__, url_prefix="/api/v1")


def _chromadb_probe(path: str) -> dict:
    """Actually probe ChromaDB — returns real status instead of hardcoded 'ok'."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=path)
        client.heartbeat()
        return {"status": "ok", "path": path}
    except Exception as e:
        return {"status": "error", "path": path, "error": str(e)[:120]}


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
            "chromadb": _chromadb_probe(str(settings.chromadb_path)),
        },
    })


@system_bp.get("/system/stats")
@require_auth
def stats():
    ns = effective_namespace(None)
    try:
        with get_db() as conn:
            if ns:
                # Scoped counts — 2 queries instead of 7 sequential round-trips
                rows = conn.execute(
                    """SELECT
                         (SELECT COUNT(*) FROM memory_entries WHERE namespace=?) AS memory_entries,
                         (SELECT COUNT(*) FROM agents WHERE enabled=1)           AS agents,
                         (SELECT COUNT(*) FROM agent_runs WHERE namespace=?)      AS agent_runs,
                         (SELECT COUNT(*) FROM workflows)                         AS workflows,
                         (SELECT COUNT(*) FROM outputs WHERE namespace=?)         AS outputs,
                         (SELECT COUNT(*) FROM projects p
                            JOIN namespaces n ON p.namespace_id=n.id
                            WHERE n.slug=?)                                       AS projects,
                         (SELECT COUNT(*) FROM tickets
                            WHERE namespace=?
                              AND status NOT IN ('resolved','closed','completed')) AS open_tickets""",
                    (ns, ns, ns, ns, ns),
                ).fetchone()
                counts = dict(rows)
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


@system_bp.get("/system/namespace-stats")
@require_auth
def namespace_stats():
    """Per-namespace usage metrics for the Client Usage Dashboard.
    Clients can only query their own namespace; admins can pass ?namespace=slug."""
    requested = request.args.get("namespace")
    ns = effective_namespace(requested)
    if not ns:
        return jsonify({"error": "namespace required"}), 400

    # 30-day window for cost/runs
    from datetime import datetime, timedelta
    month_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    week_ago  = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")

    try:
        with get_db() as conn:
            # Token usage (last 30 days)
            tok = conn.execute(
                """SELECT COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0),
                          COUNT(*), COALESCE(AVG(eval_score),0)
                   FROM agent_runs WHERE namespace=? AND created_at>=? AND status='done'""",
                (ns, month_ago),
            ).fetchone()
            tokens_in, tokens_out, run_count, eval_avg = tok[0], tok[1], tok[2], tok[3]

            # Cost estimate (Claude Sonnet 4.6 pricing)
            cost_usd = round((tokens_in / 1_000_000 * 3.0) + (tokens_out / 1_000_000 * 15.0), 4)

            # Ticket resolution rate (last 30 days)
            t_total = conn.execute(
                "SELECT COUNT(*) FROM tickets WHERE namespace=? AND created_at>=?",
                (ns, month_ago),
            ).fetchone()[0]
            t_closed = conn.execute(
                "SELECT COUNT(*) FROM tickets WHERE namespace=? AND created_at>=? "
                "AND status IN ('completed','closed','resolved')",
                (ns, month_ago),
            ).fetchone()[0]

            # Memory freshness (entries updated in last 7 days)
            m_total = conn.execute(
                "SELECT COUNT(*) FROM memory_entries WHERE namespace=? AND archived=0",
                (ns,),
            ).fetchone()[0]
            m_fresh = conn.execute(
                "SELECT COUNT(*) FROM memory_entries WHERE namespace=? AND archived=0 AND updated_at>=?",
                (ns, week_ago),
            ).fetchone()[0]

            # Memory last consolidated
            last_cons = conn.execute(
                "SELECT MAX(updated_at) FROM memory_entries WHERE namespace=? AND is_consolidated=1",
                (ns,),
            ).fetchone()[0]

            # Workflow success rate (last 30 days) — scoped via workflows.namespace join
            wf_total, wf_ok = 0, 0
            try:
                wf_row = conn.execute(
                    "SELECT COUNT(*), SUM(CASE WHEN wr.status='done' THEN 1 ELSE 0 END) "
                    "FROM workflow_runs wr "
                    "JOIN workflows w ON wr.workflow_id=w.id "
                    "WHERE w.namespace=? AND wr.created_at>=?",
                    (ns, month_ago),
                ).fetchone()
                wf_total, wf_ok = wf_row[0], (wf_row[1] or 0)
            except Exception:
                pass

            # Output count
            out_count = conn.execute(
                "SELECT COUNT(*) FROM outputs WHERE namespace=?", (ns,)
            ).fetchone()[0]

            # Recent runs (last 10 for activity feed)
            recent_rows = conn.execute(
                """SELECT id, agent_id, status, eval_score, created_at, duration_ms
                   FROM agent_runs WHERE namespace=? ORDER BY created_at DESC LIMIT 10""",
                (ns,),
            ).fetchall()
            recent_runs = [dict(r) for r in recent_rows]

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Namespace Pulse Score (0–100 composite)
    q_score  = min((eval_avg / 5.0) * 100, 100) if eval_avg else 50
    t_score  = (t_closed / t_total * 100) if t_total else 100
    m_score  = (m_fresh / m_total * 100) if m_total else 100
    wf_score = (wf_ok / wf_total * 100) if wf_total else 100
    pulse    = round(q_score * 0.40 + t_score * 0.30 + m_score * 0.20 + wf_score * 0.10, 1)

    return jsonify({
        "namespace":      ns,
        "period_days":    30,
        "tokens_in":      tokens_in,
        "tokens_out":     tokens_out,
        "cost_usd":       cost_usd,
        "run_count":      run_count,
        "eval_avg":       round(eval_avg, 2),
        "ticket_total":   t_total,
        "tickets_closed": t_closed,
        "memory_count":   m_total,
        "memory_fresh":   m_fresh,
        "last_consolidated": last_cons,
        "workflow_total": wf_total,
        "workflow_ok":    wf_ok,
        "output_count":   out_count,
        "pulse_score":    pulse,
        "recent_runs":    recent_runs,
        "timestamp":      utcnow_str(),
    })


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
