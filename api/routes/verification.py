"""TraceShield AI — Verification Endpoints.

POST /api/verification/bola: Authorized BOLA verification workflow.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, status

from api.schemas import BolaVerificationRequest, BolaVerificationResponse
from api.services.scan_service import run_bola_verification_workflow

logger = logging.getLogger("traceshield.api.verification")
router = APIRouter(prefix="/verification", tags=["verification"])


@router.post("/bola", response_model=BolaVerificationResponse)
def verify_bola(request: BolaVerificationRequest) -> BolaVerificationResponse:
    """Execute authorized BOLA verification and record verification state."""
    try:
        return run_bola_verification_workflow(request)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error("BOLA verification failed unexpectedly: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="BOLA verification failed unexpectedly.",
        )
