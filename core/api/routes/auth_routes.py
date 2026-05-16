"""Auth routes — /api/v1/auth/*"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from core.api.limiter import limiter
from core.auth import (
    audit_log, check_lockout, clear_failed_attempts, create_access_token,
    create_refresh_token, create_user, effective_namespace, get_user_by_id,
    get_user_by_username, hash_password, record_failed_attempt, require_auth,
    revoke_sessions_by_token_hash, store_refresh_token, validate_password_strength,
    validate_refresh_token, verify_password,
)
from core.database import get_db
from core.utils import new_id

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


def _ip() -> str:
    return request.remote_addr or ""


def _ua() -> str:
    return request.headers.get("User-Agent", "")


# ── POST /auth/login ──────────────────────────────────────────────────────────

@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    user = get_user_by_username(username)
    if not user:
        # Constant-time response — prevent username enumeration
        import time as _time; _time.sleep(0.2)
        audit_log("login_failure", username=username, ip=_ip(), ua=_ua(), detail={"reason": "not_found"})
        return jsonify({"error": "Invalid username or password"}), 401

    if not user["is_active"]:
        return jsonify({"error": "Account disabled"}), 403

    remaining = check_lockout(user)
    if remaining is not None:
        return jsonify({"error": "Account locked", "retry_after_seconds": remaining}), 423

    if not verify_password(password, user["password_hash"]):
        record_failed_attempt(user["id"])
        return jsonify({"error": "Invalid username or password"}), 401

    clear_failed_attempts(user["id"])
    audit_log("login_success", user_id=user["id"], username=username, ip=_ip(), ua=_ua(), namespace=user.get("namespace"))

    access_token = create_access_token(user["id"], user["username"], user["role"], user.get("namespace"))
    raw_refresh, refresh_hash = create_refresh_token()
    store_refresh_token(user["id"], refresh_hash, ip=_ip(), ua=_ua())

    return jsonify({
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "expires_in": 3600,
        "user": _user_public(user),
    })


# ── POST /auth/register ───────────────────────────────────────────────────────

@auth_bp.post("/register")
@limiter.limit("5 per minute")
def register():
    # Check if self-registration is enabled
    with get_db() as conn:
        cfg = conn.execute("SELECT value FROM system_config WHERE key = 'allow_self_register'").fetchone()
    if not cfg or cfg["value"] != "1":
        return jsonify({"error": "Self-registration is disabled"}), 403

    body = request.get_json(silent=True) or {}
    username  = (body.get("username") or "").strip()
    password  = body.get("password") or ""
    email     = (body.get("email") or "").strip() or None
    namespace = (body.get("namespace") or "").strip() or None

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    # Password strength
    err = validate_password_strength(password, username)
    if err:
        return jsonify({"error": err}), 422

    # Namespace must be a client-type namespace
    if not namespace:
        return jsonify({"error": "namespace required for self-registration"}), 422

    with get_db() as conn:
        ns_row = conn.execute(
            "SELECT slug, type FROM namespaces WHERE slug = ? AND enabled = 1", (namespace,)
        ).fetchone()
    if not ns_row:
        return jsonify({"error": f"Namespace '{namespace}' not found"}), 422
    if ns_row["type"] not in ("client",):
        return jsonify({"error": "Self-registration only allowed for client namespaces"}), 422

    # One client account per namespace
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE namespace = ? AND role = 'client'", (namespace,)
        ).fetchone()
    if existing:
        return jsonify({"error": f"A client account already exists for namespace '{namespace}'"}), 409

    # Username uniqueness
    if get_user_by_username(username):
        return jsonify({"error": "Username already taken"}), 409

    user = create_user(username, password, role="client", namespace=namespace, email=email)
    audit_log("register", user_id=user["id"], username=username, ip=_ip(), ua=_ua(), namespace=namespace)
    return jsonify({"message": "Account created. Please sign in.", "user": _user_public(user)}), 201


# ── POST /auth/refresh ────────────────────────────────────────────────────────

@auth_bp.post("/refresh")
@limiter.limit("20 per minute")
def refresh():
    body = request.get_json(silent=True) or {}
    raw_token = body.get("refresh_token") or ""
    if not raw_token:
        return jsonify({"error": "refresh_token required"}), 400

    session = validate_refresh_token(raw_token)
    if not session:
        return jsonify({"error": "Invalid or expired refresh token"}), 401

    user = get_user_by_id(session["user_id"])
    if not user or not user["is_active"]:
        return jsonify({"error": "User not found or disabled"}), 401

    access_token = create_access_token(user["id"], user["username"], user["role"], user.get("namespace"))
    audit_log("token_refresh", user_id=user["id"], username=user["username"], ip=_ip(), ua=_ua())

    return jsonify({"access_token": access_token, "expires_in": 3600})


# ── POST /auth/logout ─────────────────────────────────────────────────────────

@auth_bp.post("/logout")
@require_auth
def logout():
    body = request.get_json(silent=True) or {}
    raw_token = body.get("refresh_token") or ""
    if raw_token:
        import hashlib
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        revoke_sessions_by_token_hash(token_hash)
    from flask import g as _g
    audit_log("logout", user_id=getattr(_g, "user_id", None), username=getattr(_g, "username", None), ip=_ip(), ua=_ua())
    return jsonify({"message": "Logged out"})


# ── GET /auth/me ──────────────────────────────────────────────────────────────

@auth_bp.get("/me")
@require_auth
def me():
    from flask import g as _g
    user = get_user_by_id(_g.user_id.replace("apikey:", "") if _g.user_id.startswith("apikey:") else _g.user_id)
    if not user:
        # API key auth — return synthetic user object
        return jsonify({
            "id": _g.user_id,
            "username": _g.username,
            "role": _g.user_role,
            "namespace": _g.user_namespace,
            "auth_method": _g.auth_method,
        })
    return jsonify(_user_public(user))


# ── POST /auth/change-password ────────────────────────────────────────────────

@auth_bp.post("/change-password")
@require_auth
@limiter.limit("5 per minute")
def change_password():
    from flask import g as _g
    body = request.get_json(silent=True) or {}
    current_pw = body.get("current_password") or ""
    new_pw     = body.get("new_password") or ""

    if not current_pw or not new_pw:
        return jsonify({"error": "current_password and new_password required"}), 400

    if _g.user_id.startswith("apikey:"):
        return jsonify({"error": "Not applicable for API key auth"}), 400

    user = get_user_by_id(_g.user_id)
    if not user or not verify_password(current_pw, user["password_hash"]):
        return jsonify({"error": "Current password incorrect"}), 401

    err = validate_password_strength(new_pw, user["username"])
    if err:
        return jsonify({"error": err}), 422

    new_hash = hash_password(new_pw)
    with get_db() as conn:
        conn.execute("UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                     (new_hash, user["id"]))

    audit_log("password_change", user_id=user["id"], username=user["username"], ip=_ip(), ua=_ua())
    return jsonify({"message": "Password updated"})


# ── Helper ────────────────────────────────────────────────────────────────────

def _user_public(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email"),
        "role": user["role"],
        "namespace": user.get("namespace"),
        "is_active": bool(user["is_active"]),
        "last_login_at": user.get("last_login_at"),
        "created_at": user.get("created_at"),
    }
