"""Central authentication module — passwords, JWT, sessions, decorators."""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Optional

import bcrypt
import jwt
from flask import g, jsonify, request

from core.database import get_db
from core.utils import new_id, utcnow

logger = logging.getLogger("claudeos.auth")

# ── Config helpers ─────────────────────────────────────────────────────────────

def _cfg(key: str, default: str) -> str:
    try:
        with get_db() as conn:
            row = conn.execute("SELECT value FROM system_config WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    except Exception:
        return default


def _cfg_int(key: str, default: int) -> int:
    try:
        return int(_cfg(key, str(default)))
    except (ValueError, TypeError):
        return default


# ── Password ───────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def validate_password_strength(password: str, username: str = "") -> Optional[str]:
    """Returns an error message, or None if password is strong enough."""
    if len(password) < 10:
        return "Password must be at least 10 characters"
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one digit"
    if username and username.lower() in password.lower():
        return "Password must not contain your username"
    return None


# ── JWT ────────────────────────────────────────────────────────────────────────

def _secret() -> str:
    from core.config import get_settings
    return get_settings().CLAUDEOS_SECRET_KEY


def create_access_token(user_id: str, username: str, role: str, namespace: Optional[str]) -> str:
    ttl_minutes = _cfg_int("access_token_minutes", 60)
    now = utcnow()
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "namespace": namespace,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure."""
    return jwt.decode(token, _secret(), algorithms=["HS256"])


def decode_access_token_unverified(token: str) -> dict:
    """Decode without verifying expiry — used for refresh decision only."""
    return jwt.decode(token, _secret(), algorithms=["HS256"], options={"verify_exp": False})


# ── Refresh tokens (opaque) ────────────────────────────────────────────────────

def create_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, sha256_hash). Store the hash, send the raw token."""
    raw = secrets.token_urlsafe(48)
    hashed = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, hashed


def store_refresh_token(user_id: str, token_hash: str, ip: str = "", ua: str = "") -> str:
    """Stores session row. Returns session id."""
    ttl_days = _cfg_int("refresh_token_days", 7)
    session_id = new_id()
    expires_at = (utcnow() + timedelta(days=ttl_days)).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO user_sessions(id, user_id, token_hash, ip_address, user_agent, expires_at) VALUES (?,?,?,?,?,?)",
            (session_id, user_id, token_hash, ip, ua, expires_at),
        )
    return session_id


def validate_refresh_token(raw_token: str) -> Optional[dict]:
    """Returns the session row if valid, None otherwise."""
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_sessions WHERE token_hash = ? AND revoked = 0 AND expires_at > CURRENT_TIMESTAMP",
            (token_hash,),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE user_sessions SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],)
            )
    return dict(row) if row else None


def revoke_session(session_id: str) -> None:
    with get_db() as conn:
        conn.execute("UPDATE user_sessions SET revoked = 1 WHERE id = ?", (session_id,))


def revoke_sessions_by_token_hash(token_hash: str) -> None:
    with get_db() as conn:
        conn.execute("UPDATE user_sessions SET revoked = 1 WHERE token_hash = ?", (token_hash,))


# ── Lockout ────────────────────────────────────────────────────────────────────

def check_lockout(user: dict) -> Optional[int]:
    """Returns seconds remaining in lockout, or None if not locked."""
    if not user.get("locked_until"):
        return None
    locked_until = datetime.fromisoformat(user["locked_until"])
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    remaining = (locked_until - utcnow()).total_seconds()
    return int(remaining) if remaining > 0 else None


def record_failed_attempt(user_id: str) -> None:
    max_attempts = _cfg_int("max_failed_attempts", 5)
    lockout_minutes = _cfg_int("lockout_minutes", 15)
    with get_db() as conn:
        conn.execute(
            f"""UPDATE users SET
                failed_attempts = failed_attempts + 1,
                locked_until = CASE
                    WHEN failed_attempts + 1 >= ? THEN datetime('now', '+{lockout_minutes} minutes')
                    ELSE locked_until
                END,
                updated_at = CURRENT_TIMESTAMP
                WHERE id = ?""",
            (max_attempts, user_id),
        )
    audit_log("login_failure", user_id=user_id, ip=_client_ip(), ua=_client_ua())


def clear_failed_attempts(user_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,),
        )


# ── Audit log ──────────────────────────────────────────────────────────────────

def audit_log(
    event_type: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    ip: str = "",
    ua: str = "",
    namespace: Optional[str] = None,
    detail: Optional[dict] = None,
) -> None:
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO auth_events(id, event_type, user_id, username, ip_address, user_agent, namespace, detail) VALUES (?,?,?,?,?,?,?,?)",
                (new_id(), event_type, user_id, username, ip, ua, namespace, json.dumps(detail or {})),
            )
    except Exception as e:
        logger.warning("audit_log failed: %s", e)


# ── User CRUD helpers ──────────────────────────────────────────────────────────

def get_user_by_username(username: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def create_user(username: str, password: str, role: str = "viewer",
                namespace: Optional[str] = None, email: Optional[str] = None,
                must_change_password: bool = False) -> dict:
    user_id = new_id()
    pw_hash = hash_password(password)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users(id, username, email, password_hash, role, namespace, must_change_password) "
            "VALUES (?,?,?,?,?,?,?)",
            (user_id, username, email, pw_hash, role, namespace, int(must_change_password)),
        )
    user = get_user_by_id(user_id)
    audit_log("user_created", user_id=user_id, username=username, namespace=namespace)
    return user


# ── Flask request helpers ──────────────────────────────────────────────────────

def _client_ip() -> str:
    try:
        return request.remote_addr or ""
    except RuntimeError:
        return ""


def _client_ua() -> str:
    try:
        return request.headers.get("User-Agent", "")
    except RuntimeError:
        return ""


# ── API key fallback (re-uses existing api_keys table) ────────────────────────

def _validate_api_key_header(raw_key: str) -> bool:
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, permissions, namespace FROM api_keys WHERE key_hash = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)",
            (key_hash,),
        ).fetchone()
    if not row:
        return False
    with get_db() as conn:
        conn.execute("UPDATE api_keys SET last_used = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
    g.user_id = f"apikey:{row['id']}"
    g.username = row["name"]
    g.user_role = "operator"
    g.user_namespace = None
    g.auth_method = "api_key"
    return True


# ── Decorators ────────────────────────────────────────────────────────────────

def require_auth(f):
    """Accept JWT Bearer OR legacy X-API-Key. Sets g.user_* context."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. JWT Bearer
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_access_token(token)
                g.user_id        = payload["sub"]
                g.username       = payload["username"]
                g.user_role      = payload["role"]
                g.user_namespace = payload.get("namespace")
                g.auth_method    = "jwt"
                return f(*args, **kwargs)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401

        # 2. X-API-Key fallback
        raw_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if raw_key and _validate_api_key_header(raw_key):
            return f(*args, **kwargs)

        return jsonify({"error": "Authentication required"}), 401
    return decorated


def require_role(*allowed_roles: str):
    """403 if g.user_role is not in allowed_roles. Must be used after @require_auth."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if getattr(g, "user_role", None) not in allowed_roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def effective_namespace(requested: Optional[str] = None) -> Optional[str]:
    """Return the namespace to query based on caller's role.
    Clients/viewers are always restricted to their own namespace.
    """
    role = getattr(g, "user_role", "admin")
    if role in ("client", "viewer"):
        return getattr(g, "user_namespace", None)
    return requested
