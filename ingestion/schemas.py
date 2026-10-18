"""TraceShield AI — Ingestion Schemas and Canonical Data Contracts.

Defines Pydantic models, lifecycle status enums, deterministic fingerprinting,
canonical entity resolution, and standardized scan execution result contracts.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class FindingLifecycleStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    CONFIRMED = "CONFIRMED"
    INCONCLUSIVE = "INCONCLUSIVE"
    REMEDIATED = "REMEDIATED"
    REOPENED = "REOPENED"


class FindingSeverity(int, Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    INFORMATIONAL = 1
    UNKNOWN = 0


class ScanExecutionStatus(str, Enum):
    COMPLETED_WITH_FINDINGS = "completed_with_findings"
    COMPLETED_CLEAN = "completed_clean"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Canonical mapping for DemoShop seeded/known findings to ensure
# seeding and scanner ingestion share the exact same canonical identifiers.
CANONICAL_FINDINGS = {
    ("shop-demo", "BOLA", "/api/orders/{id}"): {
        "finding_id": "F-001",
        "endpoint_id": "ep-orders",
        "title": "Broken Object Level Authorization on order retrieval",
        "severity": 4,
    },
    ("shop-demo", "MISSING_CSP", "/"): {
        "finding_id": "F-002",
        "endpoint_id": "ep-root",
        "title": "Missing Content Security Policy",
        "severity": 2,
    },
    ("shop-demo", "MISSING_CSP", "/api/products"): {
        "finding_id": "F-002",
        "endpoint_id": "ep-catalog",
        "title": "Missing Content Security Policy",
        "severity": 2,
    },
}


def validate_target_url(
    url: str,
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "demoshop"),
    allowed_schemes: tuple[str, ...] = ("http", "https"),
) -> str:
    """Validate target URL against authorization boundaries.
    
    Prevents scanning unapproved remote targets, private ranges, or cloud metadata.
    """
    if not url or not isinstance(url, str):
        raise ValueError("Target URL must be a non-empty string.")

    parsed = urlsplit(url.strip())
    if not parsed.scheme or parsed.scheme.lower() not in allowed_schemes:
        raise ValueError(
            f"Unauthorized URL scheme '{parsed.scheme}'. Allowed schemes: {allowed_schemes}"
        )

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise ValueError(f"Invalid target URL: missing hostname in '{url}'.")

    # Include hosts from ALLOWED_SCAN_HOSTS env var if provided
    env_hosts = [h.strip().lower() for h in __import__("os").getenv("ALLOWED_SCAN_HOSTS", "").split(",") if h.strip()]
    effective_hosts = [h.lower() for h in allowed_hosts] + env_hosts

    if hostname not in effective_hosts:
        raise ValueError(
            f"Unauthorized scan target '{hostname}'. Starter scanners are restricted to: {effective_hosts}"
        )


    return url.strip()


def compute_finding_fingerprint(
    project_id: str,
    vulnerability_type: str,
    endpoint_path: str,
) -> str:
    """Compute a deterministic SHA-256 fingerprint from core attributes.
    
    Excludes timestamps, runtime request IDs, and variable response bodies.
    """
    normalized = (
        f"{project_id.strip().lower()}:"
        f"{vulnerability_type.strip().upper()}:"
        f"{endpoint_path.strip().lower()}"
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def resolve_canonical_finding_id(
    project_id: str,
    vulnerability_type: str,
    endpoint_path: str,
) -> str:
    """Resolve stable canonical finding ID.
    
    Reconciles seed fixture IDs (F-001, F-002) with scanner observations
    so duplicate findings are not created in FalkorDB.
    """
    key = (project_id.strip(), vulnerability_type.strip().upper(), endpoint_path.strip())
    if key in CANONICAL_FINDINGS:
        return CANONICAL_FINDINGS[key]["finding_id"]
    
    # Try normalized path
    norm_path = endpoint_path.rstrip("/") or "/"
    norm_key = (project_id.strip(), vulnerability_type.strip().upper(), norm_path)
    if norm_key in CANONICAL_FINDINGS:
        return CANONICAL_FINDINGS[norm_key]["finding_id"]

    # Fallback to deterministic fingerprint-based ID
    fp = compute_finding_fingerprint(project_id, vulnerability_type, endpoint_path)
    return f"F-{fp[:8].upper()}"


def resolve_canonical_endpoint_id(
    project_id: str,
    endpoint_path: str,
    vulnerability_type: str = "",
) -> str:
    """Resolve canonical endpoint ID matching seed_graph topology."""
    norm_path = endpoint_path.rstrip("/") or "/"
    if norm_path == "/api/orders/{id}" or norm_path.startswith("/api/orders/"):
        return "ep-orders"
    if norm_path in ("/api/products", "/products"):
        return "ep-catalog"
    if norm_path == "/":
        return "ep-root"
    
    safe_path = norm_path.replace("/", "_").strip("_")
    return f"{project_id}:ep_{safe_path or 'root'}"


def generate_evidence_id(finding_id: str, prefix: str = "EV") -> str:
    """Generate a unique, immutable evidence identifier preserving history."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    uid = uuid4().hex[:6].upper()
    return f"{prefix}-{finding_id}-{ts}-{uid}"


def generate_scan_id(scanner_name: str) -> str:
    """Generate unique scan execution identifier."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    uid = uuid4().hex[:6].upper()
    safe_name = scanner_name.replace("_", "-").upper()
    return f"SCAN-{safe_name}-{ts}-{uid}"


def determine_lifecycle_transition(
    current_status: Optional[str],
    observed_outcome: str,
) -> FindingLifecycleStatus:
    """Determine the valid next lifecycle state given a scan observation.
    
    Rules:
    - CONFIRMED observation:
      - If currently REMEDIATED -> REOPENED
      - Otherwise -> CONFIRMED
    - DENIED / CLEAN observation (verification passed):
      - If finding exists -> REMEDIATED
    - INCONCLUSIVE observation:
      - If previously set -> retain current status
      - If new -> INCONCLUSIVE
    """
    obs = (observed_outcome or "").strip().upper()
    curr = (current_status or "").strip().upper()

    if obs in ("CONFIRMED", "VULNERABLE", "FAIL", "FAILED"):
        if curr in ("REMEDIATED", "RESOLVED", "CLOSED", "FIXED"):
            return FindingLifecycleStatus.REOPENED
        return FindingLifecycleStatus.CONFIRMED

    if obs in ("DENIED", "CLEAN", "PASS", "PASSED", "REMEDIATED", "SECURE"):
        return FindingLifecycleStatus.REMEDIATED

    if obs in ("INCONCLUSIVE", "UNKNOWN"):
        if curr and curr not in ("UNKNOWN", ""):
            # Retain established status rather than degrading on an inconclusive check
            return FindingLifecycleStatus(curr) if curr in FindingLifecycleStatus._value2member_map_ else FindingLifecycleStatus.INCONCLUSIVE
        return FindingLifecycleStatus.INCONCLUSIVE

    return FindingLifecycleStatus.UNVERIFIED


class NormalizedFinding(BaseModel):
    """Canonical model for a normalized security finding."""
    finding_id: str
    project_id: str = "shop-demo"
    website_name: str = "DemoShop"
    fingerprint: str
    title: str
    type: str
    severity_level: int = Field(default=2, ge=0, le=5)
    status: str = FindingLifecycleStatus.UNVERIFIED.value
    source: str
    endpoint_id: str
    endpoint_path: str
    evidence_id: str
    evidence_summary: str
    evidence_confirmed: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    guidance: Optional[str] = None
    target_url: Optional[str] = None
    observed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in FindingLifecycleStatus._value2member_map_:
            raise ValueError(f"Invalid finding status: {v}")
        return v_upper

    @field_validator("evidence_summary")
    @classmethod
    def validate_evidence_summary(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Evidence summary cannot be empty.")
        return v.strip()

    def to_graph_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching graph_writer required keys."""
        return {
            "finding_id": self.finding_id,
            "project_id": self.project_id,
            "website_name": self.website_name,
            "fingerprint": self.fingerprint,
            "title": self.title,
            "type": self.type,
            "severity_level": self.severity_level,
            "status": self.status,
            "source": self.source,
            "endpoint_id": self.endpoint_id,
            "endpoint_path": self.endpoint_path,
            "evidence_id": self.evidence_id,
            "evidence_summary": self.evidence_summary,
            "evidence_confirmed": self.evidence_confirmed,
            "confidence": self.confidence,
            "guidance": self.guidance or "",
            "target_url": self.target_url or "",
            "observed_at": self.observed_at,
        }


class ScanRunResult(BaseModel):
    """Standardized contract for a scanner execution run.
    
    Distinguishes completed_with_findings, completed_clean, failed, and cancelled.
    """
    scan_id: str
    project_id: str = "shop-demo"
    scanner_name: str
    target_url: str
    status: ScanExecutionStatus
    started_at: str
    completed_at: str
    findings: List[NormalizedFinding] = Field(default_factory=list)
    error_summary: Optional[str] = None
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def findings_count(self) -> int:
        return len(self.findings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "project_id": self.project_id,
            "scanner_name": self.scanner_name,
            "target_url": self.target_url,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "findings_count": self.findings_count,
            "findings": [f.to_graph_dict() for f in self.findings],
            "error_summary": self.error_summary,
            "execution_metadata": self.execution_metadata,
        }
