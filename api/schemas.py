"""TraceShield AI — FastAPI Request and Response Schemas.

Defines Pydantic models for health, projects, scans, findings, graph views,
AI-assisted investigations, and verification workflows matching docs/API_SPEC.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Error Models
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
    request_id: str = Field(default_factory=lambda: f"req-{uuid4().hex[:8]}")


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Health Models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    dependencies: Dict[str, str] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Project Models
# ---------------------------------------------------------------------------

class ProjectSummary(BaseModel):
    id: str
    name: str
    target_type: str = "web_app"
    target_ref: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class PaginationMeta(BaseModel):
    limit: int = 50
    offset: int = 0
    total: int = 0


class ProjectListResponse(BaseModel):
    items: List[ProjectSummary]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Scan Models
# ---------------------------------------------------------------------------

class ScanCreateRequest(BaseModel):
    scanner: str = Field(description="Scanner ID, e.g. http_headers or bola_check")
    target: Optional[str] = Field(default=None, description="Explicit target URL (must be authorized)")
    target_url: Optional[str] = Field(default=None, description="Alias for target URL")



class ScanResponse(BaseModel):
    id: str
    project_id: str
    scanner: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    findings_count: int = 0
    error_summary: Optional[str] = None
    target_url: Optional[str] = None


class ScanListResponse(BaseModel):
    items: List[ScanResponse]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Finding Models
# ---------------------------------------------------------------------------

class FindingSummary(BaseModel):
    id: str
    project_id: str
    title: str
    category: str
    type: str
    severity: str
    severity_level: int
    status: str
    source: str
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    fingerprint: Optional[str] = None


class FindingDetail(FindingSummary):
    endpoint: Optional[Dict[str, Any]] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    impact_paths: List[Dict[str, Any]] = Field(default_factory=list)
    priority: Optional[Dict[str, Any]] = None
    guidance: Optional[str] = None


class FindingListResponse(BaseModel):
    items: List[FindingSummary]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Graph Exploration Models
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphMeta(BaseModel):
    node_count: int
    edge_count: int
    truncated: bool = False


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    meta: GraphMeta


class NeighborsResponse(BaseModel):
    node: GraphNode
    neighbors: List[GraphNode]
    edges: List[GraphEdge]
    meta: GraphMeta


# ---------------------------------------------------------------------------
# Investigation Models
# ---------------------------------------------------------------------------

class InvestigationRequest(BaseModel):
    project_id: str = "shop-demo"
    question: str
    finding_ids: Optional[List[str]] = Field(default=None, description="Optional target finding IDs")


class NextAction(BaseModel):
    action: str
    target: Optional[str] = None
    why: str
    method: str
    requires_approval: bool = True
    verification: str
    sensitive_assets: List[str] = Field(default_factory=list)


class InvestigationResponse(BaseModel):
    id: str
    project_id: str
    question: str
    status: str = "completed"
    answer: str
    finding_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    affected_components: List[Dict[str, Any]] = Field(default_factory=list)
    observed_facts: List[str] = Field(default_factory=list)
    inferred_relationships: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    next_actions: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: str
    completed_at: str


# ---------------------------------------------------------------------------
# Verification Models
# ---------------------------------------------------------------------------

class BolaVerificationRequest(BaseModel):
    project_id: str = "shop-demo"
    target_url: Optional[str] = None


class BolaVerificationResponse(BaseModel):
    test_id: str
    project_id: str = "shop-demo"
    outcome: str
    finding_id: Optional[str] = None
    status: str
    summary: str
    tested_at: str
