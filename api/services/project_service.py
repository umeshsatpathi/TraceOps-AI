"""TraceShield AI — Project Service.

Manages registered projects, target references, and project summaries.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from api.schemas import PaginationMeta, ProjectListResponse, ProjectSummary
from graph_db import get_graph

logger = logging.getLogger("traceshield.projects")

# Seed default project representation
DEFAULT_PROJECT = ProjectSummary(
    id="project-demoshop",
    name="DemoShop",
    target_type="web_app",
    target_ref="http://127.0.0.1:5001",
    created_at="2026-10-17T10:00:00Z",
    updated_at="2026-10-17T10:00:00Z",
)


def list_projects(limit: int = 50, offset: int = 0) -> ProjectListResponse:
    """Retrieve registered projects with pagination."""
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    projects: List[ProjectSummary] = []
    try:
        graph = get_graph()
        query = """
            MATCH (w:Website)
            RETURN w.id, w.name, w.target_type, w.target_ref, w.created_at, w.updated_at
            ORDER BY w.id ASC
            SKIP $offset LIMIT $limit
        """
        rows = graph.ro_query(query, params={"offset": offset, "limit": limit}).result_set
        for row in rows:
            p_id, name, t_type, t_ref, c_at, u_at = row
            projects.append(
                ProjectSummary(
                    id=str(p_id or "project-demoshop"),
                    name=str(name or "DemoShop"),
                    target_type=str(t_type or "web_app"),
                    target_ref=str(t_ref) if t_ref else None,
                    created_at=str(c_at or datetime.now(timezone.utc).isoformat()),
                    updated_at=str(u_at) if u_at else None,
                )
            )
        
        # Count total
        count_query = "MATCH (w:Website) RETURN count(w)"
        total_rows = graph.ro_query(count_query).result_set
        total = total_rows[0][0] if total_rows and total_rows[0] else len(projects)
    except Exception as exc:
        logger.warning("FalkorDB query failed in list_projects: %s. Using default project fallback.", exc)
        projects = [DEFAULT_PROJECT]
        total = 1

    if not projects and offset == 0:
        projects = [DEFAULT_PROJECT]
        total = 1

    return ProjectListResponse(
        items=projects,
        pagination=PaginationMeta(limit=limit, offset=offset, total=total),
    )


def get_project_by_id(project_id: str) -> Optional[ProjectSummary]:
    """Retrieve a project by ID or canonical alias."""
    norm_id = project_id.strip()
    # Accept both project-demoshop and shop-demo aliases
    if norm_id in ("project-demoshop", "shop-demo", "DemoShop"):
        return DEFAULT_PROJECT

    try:
        graph = get_graph()
        query = """
            MATCH (w:Website {id:$id})
            RETURN w.id, w.name, w.target_type, w.target_ref, w.created_at, w.updated_at
        """
        rows = graph.ro_query(query, params={"id": norm_id}).result_set
        if rows and rows[0]:
            p_id, name, t_type, t_ref, c_at, u_at = rows[0]
            return ProjectSummary(
                id=str(p_id),
                name=str(name or p_id),
                target_type=str(t_type or "web_app"),
                target_ref=str(t_ref) if t_ref else None,
                created_at=str(c_at or datetime.now(timezone.utc).isoformat()),
                updated_at=str(u_at) if u_at else None,
            )
    except Exception as exc:
        logger.warning("FalkorDB query failed in get_project_by_id(%s): %s", project_id, exc)

    return None
