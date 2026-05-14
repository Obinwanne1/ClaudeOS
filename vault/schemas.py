"""Client Vault schemas."""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class NamespaceCreate(BaseModel):
    slug: str
    display_name: str
    description: str = ""
    type: str = "client"          # client | personal | system
    color: str = "#407E3C"
    icon: str = "🏢"
    parent_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Namespace(NamespaceCreate):
    id: str
    enabled: bool = True
    created_at: str = ""


class ProjectCreate(BaseModel):
    namespace_id: str
    name: str
    slug: str
    description: str = ""
    status: str = "active"        # active | paused | archived
    priority: int = 2             # 1=high, 2=medium, 3=low
    tech_stack: list[str] = Field(default_factory=list)
    path: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Project(ProjectCreate):
    id: str
    created_at: str = ""
    updated_at: str = ""
