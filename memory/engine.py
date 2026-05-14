"""Memory Engine — unified facade for all memory operations.

All agents and workflows call this module. Never call store.py or
vector_store.py directly from outside the memory package.

Write path:
    engine.write() → store.write() + vector_store.upsert()

Read paths:
    1. engine.get()             — exact namespace+key lookup (SQLite)
    2. engine.search_text()     — FTS5 keyword search (SQLite)
    3. engine.search_semantic() — cosine similarity (ChromaDB → join SQLite)

Agent context injection:
    engine.get_agent_context()  — high-confidence facts for system prompt
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from memory import store, vector_store
from memory.schemas import (
    MemoryEntry,
    MemoryEntryCreate,
    MemoryEntryUpdate,
    MemorySearchRequest,
)
from core.database import get_db
from core.utils import new_id, utcnow_str

logger = logging.getLogger("claudeos.memory.engine")


def write(
    namespace: str,
    category: str,
    key: str,
    value: str,
    source: str = "user",
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
    confidence: float = 1.0,
    expires_at: Optional[datetime] = None,
) -> MemoryEntry:
    """Write a memory entry. Upserts on same namespace+key."""
    entry_create = MemoryEntryCreate(
        namespace=namespace,
        category=category,
        key=key,
        value=value,
        source=source,
        agent_id=agent_id,
        session_id=session_id,
        tags=tags or [],
        confidence=confidence,
        expires_at=expires_at,
    )
    entry = store.write(entry_create)

    # Embed into ChromaDB
    embed_text = f"{entry.key}: {entry.value}"
    chroma_id = vector_store.upsert(
        memory_id=entry.id,
        namespace=namespace,
        text=embed_text,
        metadata={
            "namespace": namespace,
            "category": category,
            "key": key,
            "confidence": str(confidence),
        },
    )

    # Record vector metadata in SQLite
    if chroma_id:
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO memory_vectors(id, memory_id, chroma_id) VALUES (?, ?, ?)",
                    (new_id(), entry.id, chroma_id),
                )
        except Exception as e:
            logger.warning("Failed to record vector metadata: %s", e)

    _log_event("memory_write", namespace, {"key": key, "category": category})
    return entry


def get(namespace: str, key: str) -> Optional[MemoryEntry]:
    """Exact key lookup within a namespace."""
    return store.get_by_key(namespace, key)


def get_by_id(entry_id: str) -> Optional[MemoryEntry]:
    return store.get_by_id(entry_id)


def list_entries(
    namespace: Optional[str] = None,
    category: Optional[str] = None,
    min_confidence: float = 0.0,
    limit: int = 100,
    offset: int = 0,
) -> list[MemoryEntry]:
    return store.list_entries(namespace, category, min_confidence, limit=limit, offset=offset)


def update(entry_id: str, update_data: MemoryEntryUpdate) -> Optional[MemoryEntry]:
    entry = store.update(entry_id, update_data)
    if entry and update_data.value is not None:
        # Re-embed on value change
        vector_store.upsert(
            memory_id=entry.id,
            namespace=entry.namespace,
            text=f"{entry.key}: {entry.value}",
            metadata={"namespace": entry.namespace, "category": entry.category, "key": entry.key},
        )
    return entry


def delete(entry_id: str) -> bool:
    entry = store.get_by_id(entry_id)
    if entry:
        vector_store.delete(entry.id, entry.namespace)
    return store.delete(entry_id)


def search_text(
    query: str,
    namespace: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 10,
) -> list[MemoryEntry]:
    """FTS5 keyword search."""
    return store.search_text(query, namespace, category, limit)


def search_semantic(
    query: str,
    namespace: str,
    top_k: int = 5,
    min_confidence: float = 0.0,
) -> list[MemoryEntry]:
    """Semantic search via ChromaDB → hydrate from SQLite."""
    hits = vector_store.search(query, namespace, top_k=top_k)
    results: list[MemoryEntry] = []
    for hit in hits:
        entry = store.get_by_id(hit["memory_id"])
        if entry and not entry.is_expired() and entry.confidence >= min_confidence:
            results.append(entry)
    return results


def search(req: MemorySearchRequest) -> list[MemoryEntry]:
    """Unified search dispatcher."""
    if req.mode == "text":
        return search_text(req.query, req.namespace, req.category, req.top_k)
    if req.mode == "semantic":
        ns = req.namespace or "global"
        return search_semantic(req.query, ns, req.top_k, req.min_confidence)
    # "both" — merge, dedupe by id
    text_results = search_text(req.query, req.namespace, req.category, req.top_k)
    sem_ns = req.namespace or "global"
    sem_results = search_semantic(req.query, sem_ns, req.top_k, req.min_confidence)
    seen: set[str] = set()
    merged: list[MemoryEntry] = []
    for e in text_results + sem_results:
        if e.id not in seen:
            seen.add(e.id)
            merged.append(e)
    return merged[: req.top_k]


def expire_stale() -> int:
    """Delete expired entries from SQLite and ChromaDB."""
    # Get expired IDs before deletion for ChromaDB cleanup
    with get_db() as conn:
        expired_rows = conn.execute(
            "SELECT id, namespace FROM memory_entries WHERE expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP"
        ).fetchall()
    for row in expired_rows:
        vector_store.delete(row["id"], row["namespace"])
    count = store.expire_stale()
    logger.info("Expired %d stale memory entries", count)
    return count


def namespace_counts() -> dict[str, int]:
    return store.namespace_counts()


def get_agent_context(namespace: str, min_confidence: float = 0.8) -> str:
    """Build context string for injection into agent system prompts."""
    entries = store.get_context_for_agent(namespace, min_confidence)
    if not entries:
        return ""
    lines = [f"## ClaudeOS Memory Context [{namespace}]"]
    for e in entries:
        lines.append(f"- [{e.category}] {e.key}: {e.value}  (confidence: {e.confidence:.2f})")
    return "\n".join(lines)


def _log_event(event_type: str, namespace: str, payload: dict) -> None:
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO system_events(id, event_type, namespace, payload) VALUES (?, ?, ?, ?)",
                (new_id(), event_type, namespace, json.dumps(payload)),
            )
    except Exception:
        pass
