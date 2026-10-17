"""TraceShield AI — Finding Endpoints.

GET /api/findings: Filtered, paginated security findings.
GET /api/findings/{finding_id}: Finding detail with graph evidence and impact paths.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from api.schemas import FindingDetail, FindingListResponse
from api.services.finding_service import get_finding_detail, list_findings

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=FindingListResponse)
def get_findings(
    project_id: Optional[str] = Query(default=None, description="Filter by project ID"),
    scan_id: Optional[str] = Query(default=None, description="Filter by scan run ID"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (critical, high, medium, low)"),
    status: Optional[str] = Query(default=None, description="Filter by lifecycle status (OPEN, CONFIRMED, REMEDIATED)"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> FindingListResponse:
    """Retrieve filtered findings with deterministic sorting."""
    return list_findings(
        project_id=project_id,
        scan_id=scan_id,
        severity=severity,
        status=status,
        category=category,
        limit=limit,
        offset=offset,
    )


@router.get("/{finding_id}", response_model=FindingDetail)
def get_finding(finding_id: str) -> FindingDetail:
    """Retrieve comprehensive finding details, evidence, and affected components."""
    finding = get_finding_detail(finding_id)
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found.",
        )
    return finding
