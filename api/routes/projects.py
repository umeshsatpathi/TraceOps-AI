"""TraceShield AI — Project Endpoints.

GET /api/projects: Paginated registered projects.
GET /api/projects/{project_id}: Project details and summary.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.schemas import ProjectListResponse, ProjectSummary
from api.services.project_service import get_project_by_id, list_projects

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
def get_projects(
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> ProjectListResponse:
    """Retrieve registered projects with pagination."""
    return list_projects(limit=limit, offset=offset)


@router.get("/{project_id}", response_model=ProjectSummary)
def get_project(project_id: str) -> ProjectSummary:
    """Retrieve registered project details by ID."""
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found.",
        )
    return project
