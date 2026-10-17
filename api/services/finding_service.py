"""TraceShield AI — Finding Service.

Provides filtered finding queries, finding detail with graph relationships,
and lifecycle retrieval without inline Cypher in API routes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from api.schemas import FindingDetail, FindingListResponse, FindingSummary, PaginationMeta
from graph_db import get_graph
from graph_tools import get_evidence, get_finding, score_priority, trace_impact

logger = logging.getLogger("traceshield.findings")


def list_findings(
    project_id: Optional[str] = None,
    scan_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> FindingListResponse:
    """Retrieve filtered findings with deterministic sorting and pagination."""
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    where_clauses: List[str] = []
    params: Dict[str, Any] = {"limit": limit, "offset": offset}

    if status:
        where_clauses.append("toUpper(f.status) = $status")
        params["status"] = status.strip().upper()

    if severity:
        where_clauses.append("(toLower(f.severity) = $severity OR toString(f.severity_level) = $severity)")
        params["severity"] = severity.strip().lower()

    if category:
        where_clauses.append("toLower(f.category) = $category")
        params["category"] = category.strip().lower()

    match_prefix = "MATCH (f:Finding)"
    if scan_id:
        match_prefix = "MATCH (s {id:$scan_id})-[:DETECTED]->(f:Finding)"
        params["scan_id"] = scan_id.strip()


    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
        {match_prefix}
        {where_sql}
        RETURN f.id, f.title, f.category, f.type, f.severity, f.severity_level,
               f.status, f.source, f.first_seen_at, f.last_seen_at, f.fingerprint, f.project_id
        ORDER BY f.severity_level DESC, f.id ASC
        SKIP $offset LIMIT $limit
    """

    count_query = f"""
        {match_prefix}
        {where_sql}
        RETURN count(f)
    """

    items: List[FindingSummary] = []
    total = 0

    try:
        graph = get_graph()
        rows = graph.ro_query(query, params=params).result_set
        for row in rows:
            (
                f_id,
                title,
                cat,
                f_type,
                sev,
                sev_lvl,
                st,
                src,
                f_seen,
                l_seen,
                fp,
                p_id,
            ) = row
            items.append(
                FindingSummary(
                    id=str(f_id),
                    project_id=str(p_id or project_id or "project-demoshop"),
                    title=str(title or f_id),
                    category=str(cat or "security_finding"),
                    type=str(f_type or "VULNERABILITY"),
                    severity=str(sev or "medium").lower(),
                    severity_level=int(sev_lvl or 1),
                    status=str(st or "OPEN"),
                    source=str(src or "scanner"),
                    first_seen_at=str(f_seen) if f_seen else None,
                    last_seen_at=str(l_seen) if l_seen else None,
                    fingerprint=str(fp) if fp else None,
                )
            )

        count_res = graph.ro_query(count_query, params=params).result_set
        if count_res and count_res[0]:
            try:
                total = int(count_res[0][0])
            except (ValueError, TypeError):
                total = len(items)
        else:
            total = len(items)


    except Exception as exc:
        logger.error("FalkorDB query failed in list_findings: %s", exc)

    return FindingListResponse(
        items=items,
        pagination=PaginationMeta(limit=limit, offset=offset, total=total),
    )


def get_finding_detail(finding_id: str) -> Optional[FindingDetail]:
    """Retrieve full finding details, connected endpoint, evidence, and impact paths."""
    base = get_finding(finding_id)
    if not base or "error" in base:
        return None

    # Retrieve connected endpoint info
    endpoint_info: Optional[Dict[str, Any]] = None
    try:
        graph = get_graph()
        ep_rows = graph.ro_query(
            """
            MATCH (f:Finding {id:$id})-[:AFFECTS]->(e:Endpoint)
            RETURN e.id, e.path, e.method, e.auth_required
            """,
            params={"id": finding_id},
        ).result_set
        if ep_rows and ep_rows[0]:
            e_id, e_path, e_method, e_auth = ep_rows[0]
            endpoint_info = {
                "id": str(e_id or ""),
                "path": str(e_path or ""),
                "method": str(e_method or "GET"),
                "auth_required": bool(e_auth),
            }
    except Exception as exc:
        logger.warning("Failed querying endpoint for finding %s: %s", finding_id, exc)

    evidence_items = get_evidence(finding_id)
    impact_paths = trace_impact(finding_id)
    priority_info = score_priority(finding_id)

    # Remediation guidance based on finding type
    f_type = str(base.get("type") or "").upper()
    if "BOLA" in f_type or "AUTH" in f_type:
        guidance = (
            "Enforce tenant authorization checks at the data layer before accessing orders. "
            "Validate that the authenticated user owns the requested record."
        )
    elif "CSP" in f_type:
        guidance = (
            "Add a Content-Security-Policy response header restricting script-src, object-src, "
            "and base-uri to trusted origins."
        )
    else:
        guidance = "Review code and access policies for the affected endpoint and service."

    return FindingDetail(
        id=str(base["id"]),
        project_id="project-demoshop",
        title=str(base.get("title") or base["id"]),
        category=str(base.get("category") or "security_finding"),
        type=str(base.get("type") or "VULNERABILITY"),
        severity=str(base.get("severity") or "high").lower(),
        severity_level=int(base.get("severity_level") or 1),
        status=str(base.get("status") or "OPEN"),
        source=str(base.get("source") or "scanner"),
        first_seen_at=str(base.get("first_seen_at")) if base.get("first_seen_at") else None,
        last_seen_at=str(base.get("last_seen_at")) if base.get("last_seen_at") else None,
        fingerprint=str(base.get("fingerprint")) if base.get("fingerprint") else None,
        endpoint=endpoint_info,
        evidence=evidence_items,
        impact_paths=impact_paths,
        priority=priority_info,
        guidance=guidance,
    )
