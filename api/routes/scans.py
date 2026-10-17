"""TraceShield AI — Scan Endpoints.

POST /api/projects/{project_id}/scans: Request an authorized scanner run.
GET /api/scans/{scan_id}: Scan execution state and findings count.
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from api.schemas import ScanCreateRequest, ScanListResponse, ScanResponse
from api.services.project_service import get_project_by_id
from api.services.scan_service import execute_scan_job, get_scan_by_id, list_scans

logger = logging.getLogger("traceshield.api.scans")
router = APIRouter(tags=["scans"])


@router.post(
    "/projects/{project_id}/scans",
    response_model=ScanResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scan(project_id: str, request: ScanCreateRequest) -> ScanResponse:
    """Execute an authorized security scan against the specified project."""
    # Verify project exists
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    try:
        return execute_scan_job(project_id=project_id, request=request)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error("Scan job failed unexpectedly: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scan execution failed unexpectedly.",
        )


@router.get("/scans", response_model=ScanListResponse)
def get_scans(
    project_id: Optional[str] = Query(default=None, description="Filter by project ID"),
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> ScanListResponse:
    """Retrieve scan execution history."""
    return list_scans(project_id=project_id, limit=limit, offset=offset)


@router.get("/projects/{project_id}/scans", response_model=ScanListResponse)
def get_project_scans(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> ScanListResponse:
    """Retrieve scan execution history for a project."""
    return list_scans(project_id=project_id, limit=limit, offset=offset)


@router.get("/scans/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: str) -> ScanResponse:
    """Retrieve scan execution state and safe summary by ID."""
    scan = get_scan_by_id(scan_id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan '{scan_id}' not found.",
        )
    return scan
