"""TraceShield AI — Graph Exploration Endpoints.

GET /api/graph: Bounded Cytoscape graph view scoped by project or finding.
GET /api/graph/nodes/{node_id}/neighbors: Scoped neighboring nodes and connecting edges.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from api.schemas import GraphResponse, NeighborsResponse
from api.services.graph_service import get_bounded_graph, get_node_neighbors

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
def get_graph_view(
    project_id: Optional[str] = Query(default=None, description="Scope graph to project"),
    finding_id: Optional[str] = Query(default=None, description="Root subgraph at finding"),
    depth: int = Query(default=3, ge=1, le=5, description="Traversal depth"),
    limit: int = Query(default=100, ge=1, le=500, description="Max nodes/edges returned"),
) -> GraphResponse:
    """Retrieve bounded graph data for frontend visualization."""
    return get_bounded_graph(
        project_id=project_id,
        finding_id=finding_id,
        depth=depth,
        limit=limit,
    )


@router.get("/nodes/{node_id}/neighbors", response_model=NeighborsResponse)
def get_neighbors(
    node_id: str,
    direction: str = Query(default="both", description="Direction: in, out, or both"),
    relationship_type: Optional[str] = Query(default=None, description="Filter by relationship type"),
    limit: int = Query(default=50, ge=1, le=200, description="Max neighbors returned"),
) -> NeighborsResponse:
    """Retrieve neighboring nodes and connecting relationships for a selected node."""
    if direction not in ("in", "out", "both"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direction must be one of: 'in', 'out', 'both'",
        )

    result = get_node_neighbors(
        node_id=node_id,
        direction=direction,
        relationship_type=relationship_type,
        limit=limit,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found in graph.",
        )
    return result
