"""Tickets REST API routes."""
from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, g, jsonify, request

from core.auth import require_auth, effective_namespace
from core.database import get_db
from core.utils import new_id, utcnow_str

tickets_bp = Blueprint("tickets", __name__, url_prefix="/api/v1/tickets")

SLA_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 72}
VALID_STATUSES = {"open", "in_progress", "resolved", "closed"}
VALID_CATEGORIES = {"bug", "billing", "access", "feature", "other"}
VALID_SLA_TIERS = set(SLA_HOURS.keys())
STAFF_ROLES = {"admin", "operator", "staff"}


def _ticket_dict(row) -> dict:
    return {
        "id": row["id"],
        "namespace": row["namespace"],
        "created_by": row["created_by"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "category": row["category"],
        "priority": row["priority"],
        "sla_tier": row["sla_tier"],
        "sla_due_at": row["sla_due_at"],
        "assigned_to": row["assigned_to"],
        "resolution": row["resolution"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _can_access_ticket(ticket: dict) -> bool:
    """True if current user may read this ticket."""
    if g.user_role in ("admin", "operator"):
        return True
    if ticket["created_by"] == g.username:
        return True
    if ticket["assigned_to"] == g.username:
        return True
    return False


def _get_ticket_by_id(ticket_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return _ticket_dict(row) if row else None


# ── List ───────────────────────────────────────────────────────────────────────

@tickets_bp.get("")
@require_auth
def list_tickets():
    role = g.user_role
    username = g.username

    status_filter = request.args.get("status")
    priority_filter = request.args.get("priority")
    ns_filter = request.args.get("namespace")
    assigned_filter = request.args.get("assigned_to")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))

    conditions = []
    params: list = []

    if role in ("client", "viewer"):
        # Namespace-scoped — own tickets only
        ns = effective_namespace()
        conditions.append("namespace = ?")
        params.append(ns)
        conditions.append("created_by = ?")
        params.append(username)
    elif role == "staff":
        # Staff see tickets assigned to them
        conditions.append("assigned_to = ?")
        params.append(username)
    else:
        # admin/operator — full access with optional filters
        if ns_filter:
            conditions.append("namespace = ?")
            params.append(ns_filter)
        if assigned_filter:
            if assigned_filter == "me":
                conditions.append("assigned_to = ?")
                params.append(username)
            else:
                conditions.append("assigned_to = ?")
                params.append(assigned_filter)

    if status_filter and status_filter in VALID_STATUSES:
        conditions.append("status = ?")
        params.append(status_filter)
    if priority_filter:
        try:
            conditions.append("priority = ?")
            params.append(int(priority_filter))
        except ValueError:
            pass

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM tickets {where} ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()

    return jsonify([_ticket_dict(r) for r in rows])


# ── Create ─────────────────────────────────────────────────────────────────────

@tickets_bp.post("")
@require_auth
def create_ticket():
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    category = body.get("category", "other")
    priority = body.get("priority", 3)

    if not title or not description:
        return jsonify({"error": "title and description required"}), 422
    if category not in VALID_CATEGORIES:
        category = "other"
    try:
        priority = int(priority)
        if priority not in (1, 2, 3, 4):
            priority = 3
    except (ValueError, TypeError):
        priority = 3

    # Namespace: clients/viewers locked to own; others supply or default to global
    ns = effective_namespace(body.get("namespace")) or g.user_namespace or "global"

    ticket_id = new_id()
    now = utcnow_str()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO tickets
               (id, namespace, created_by, title, description, status, category, priority, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)""",
            (ticket_id, ns, g.username, title, description, category, priority, now, now),
        )

    return jsonify({
        "id": ticket_id,
        "namespace": ns,
        "created_by": g.username,
        "title": title,
        "description": description,
        "status": "open",
        "category": category,
        "priority": priority,
        "sla_tier": None,
        "sla_due_at": None,
        "assigned_to": None,
        "resolution": None,
        "created_at": now,
        "updated_at": now,
    }), 201


# ── Get single ─────────────────────────────────────────────────────────────────

@tickets_bp.get("/<ticket_id>")
@require_auth
def get_ticket(ticket_id: str):
    ticket = _get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    if not _can_access_ticket(ticket):
        return jsonify({"error": "Access denied"}), 403
    return jsonify(ticket)


# ── Update ─────────────────────────────────────────────────────────────────────

@tickets_bp.patch("/<ticket_id>")
@require_auth
def update_ticket(ticket_id: str):
    ticket = _get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    if not _can_access_ticket(ticket):
        return jsonify({"error": "Access denied"}), 403

    body = request.get_json(silent=True) or {}
    role = g.user_role
    sets = []
    params: list = []

    if role in ("client", "viewer"):
        # Clients may only update description if ticket is still open
        if ticket["status"] != "open":
            return jsonify({"error": "Cannot edit a ticket that is not open"}), 403
        if "description" in body:
            sets.append("description = ?")
            params.append(body["description"])
    elif role == "staff":
        # Staff: status, resolution
        if "status" in body and body["status"] in VALID_STATUSES:
            sets.append("status = ?")
            params.append(body["status"])
        if "resolution" in body:
            sets.append("resolution = ?")
            params.append(body["resolution"])
    else:
        # admin/operator: all fields
        if "title" in body:
            sets.append("title = ?")
            params.append(body["title"])
        if "description" in body:
            sets.append("description = ?")
            params.append(body["description"])
        if "status" in body and body["status"] in VALID_STATUSES:
            sets.append("status = ?")
            params.append(body["status"])
        if "category" in body and body["category"] in VALID_CATEGORIES:
            sets.append("category = ?")
            params.append(body["category"])
        if "priority" in body:
            try:
                p = int(body["priority"])
                if p in (1, 2, 3, 4):
                    sets.append("priority = ?")
                    params.append(p)
            except (ValueError, TypeError):
                pass
        if "assigned_to" in body:
            sets.append("assigned_to = ?")
            params.append(body["assigned_to"] or None)
        if "resolution" in body:
            sets.append("resolution = ?")
            params.append(body["resolution"])
        if "sla_tier" in body:
            tier = body["sla_tier"]
            if tier in VALID_SLA_TIERS:
                due = (datetime.utcnow() + timedelta(hours=SLA_HOURS[tier])).strftime("%Y-%m-%d %H:%M:%S")
                sets.append("sla_tier = ?")
                params.append(tier)
                sets.append("sla_due_at = ?")
                params.append(due)
            elif tier is None or tier == "":
                sets.append("sla_tier = NULL")
                sets.append("sla_due_at = NULL")

    if not sets:
        return jsonify({"error": "No valid fields to update"}), 422

    now = utcnow_str()
    sets.append("updated_at = ?")
    params.append(now)
    params.append(ticket_id)

    with get_db() as conn:
        conn.execute(
            f"UPDATE tickets SET {', '.join(sets)} WHERE id = ?", params
        )

    return jsonify(_get_ticket_by_id(ticket_id))


# ── Delete ─────────────────────────────────────────────────────────────────────

@tickets_bp.delete("/<ticket_id>")
@require_auth
def delete_ticket(ticket_id: str):
    if g.user_role != "admin":
        return jsonify({"error": "Admin only"}), 403
    with get_db() as conn:
        row = conn.execute("DELETE FROM tickets WHERE id = ? RETURNING id", (ticket_id,)).fetchone()
    if not row:
        return jsonify({"error": "Ticket not found"}), 404
    return jsonify({"deleted": ticket_id})


# ── Comments ───────────────────────────────────────────────────────────────────

@tickets_bp.get("/<ticket_id>/comments")
@require_auth
def list_comments(ticket_id: str):
    ticket = _get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    if not _can_access_ticket(ticket):
        return jsonify({"error": "Access denied"}), 403
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM ticket_comments WHERE ticket_id = ? ORDER BY created_at ASC",
            (ticket_id,),
        ).fetchall()
    return jsonify([{
        "id": r["id"],
        "ticket_id": r["ticket_id"],
        "author": r["author"],
        "body": r["body"],
        "created_at": r["created_at"],
    } for r in rows])


@tickets_bp.post("/<ticket_id>/comments")
@require_auth
def add_comment(ticket_id: str):
    ticket = _get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404
    if not _can_access_ticket(ticket):
        return jsonify({"error": "Access denied"}), 403

    body = (request.get_json(silent=True) or {}).get("body", "").strip()
    if not body:
        return jsonify({"error": "body required"}), 422

    cid = new_id()
    now = utcnow_str()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ticket_comments (id, ticket_id, author, body, created_at) VALUES (?, ?, ?, ?, ?)",
            (cid, ticket_id, g.username, body, now),
        )

    return jsonify({"id": cid, "ticket_id": ticket_id, "author": g.username, "body": body, "created_at": now}), 201


# ── Stats ──────────────────────────────────────────────────────────────────────

@tickets_bp.get("/stats")
@require_auth
def ticket_stats():
    if g.user_role not in ("admin", "operator"):
        return jsonify({"error": "Insufficient permissions"}), 403

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        by_status = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM tickets GROUP BY status"
        ).fetchall()
        by_priority = conn.execute(
            "SELECT priority, COUNT(*) as cnt FROM tickets GROUP BY priority"
        ).fetchall()
        sla_breached = conn.execute(
            "SELECT COUNT(*) as cnt FROM tickets WHERE sla_due_at IS NOT NULL AND sla_due_at < ? AND status NOT IN ('resolved','closed')",
            (now_str,),
        ).fetchone()
        by_ns = conn.execute(
            "SELECT namespace, COUNT(*) as cnt FROM tickets GROUP BY namespace ORDER BY cnt DESC"
        ).fetchall()
        unassigned = conn.execute(
            "SELECT COUNT(*) as cnt FROM tickets WHERE assigned_to IS NULL AND status NOT IN ('resolved','closed')"
        ).fetchone()

    return jsonify({
        "by_status": {r["status"]: r["cnt"] for r in by_status},
        "by_priority": {r["priority"]: r["cnt"] for r in by_priority},
        "sla_breached": sla_breached["cnt"] if sla_breached else 0,
        "by_namespace": {r["namespace"]: r["cnt"] for r in by_ns},
        "unassigned_open": unassigned["cnt"] if unassigned else 0,
    })


# ── Assignable staff ───────────────────────────────────────────────────────────

@tickets_bp.get("/assignable-staff")
@require_auth
def assignable_staff():
    if g.user_role not in ("admin", "operator"):
        return jsonify({"error": "Insufficient permissions"}), 403
    with get_db() as conn:
        rows = conn.execute(
            "SELECT username, role, namespace FROM users WHERE role IN ('admin','operator','staff') AND is_active = 1 ORDER BY username",
        ).fetchall()
    return jsonify([{"username": r["username"], "role": r["role"], "namespace": r["namespace"]} for r in rows])
