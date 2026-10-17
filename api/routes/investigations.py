"""TraceShield AI — Investigation Endpoints.

POST /api/investigations: Start an AI/graph-grounded security investigation.
GET /api/investigations/{investigation_id}: Retrieve investigation state and result.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, status

from api.schemas import InvestigationRequest, InvestigationResponse
from api.services.investigation_service import (
    get_investigation_by_id,
    run_investigation,
)

logger = logging.getLogger("traceshield.api.investigations")
router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.post("", response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
def start_investigation(request: InvestigationRequest) -> InvestigationResponse:
    """Execute an evidence-grounded investigation with verified graph references."""
    try:
        return run_investigation(request)
    except Exception as exc:
        logger.error("Investigation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Investigation execution failed.",
        )


@router.get("/{investigation_id}", response_model=InvestigationResponse)
def get_investigation(investigation_id: str) -> InvestigationResponse:
    """Retrieve completed investigation by ID."""
    inv = get_investigation_by_id(investigation_id)
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found.",
        )
    return inv
