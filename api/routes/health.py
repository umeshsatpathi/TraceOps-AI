"""TraceShield AI — Health Endpoint.

GET /api/health: Process and dependency health check without false claims.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from fastapi import APIRouter

from api.schemas import HealthResponse
from graph_db import get_graph

logger = logging.getLogger("traceshield.api.health")
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def check_health() -> HealthResponse:
    """Verify application state and FalkorDB connectivity."""
    db_status = "unavailable"
    overall_status = "ok"

    try:
        graph = get_graph()
        # Verify graph connectivity
        res = graph.ro_query("RETURN 1").result_set
        if res and res[0][0] == 1:
            db_status = "ok"
    except Exception as exc:
        logger.warning("Health check detected graph_db unavailable: %s", exc)
        db_status = "unavailable"
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        dependencies={"graph_db": db_status},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
