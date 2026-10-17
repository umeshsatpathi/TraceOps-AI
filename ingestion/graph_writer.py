"""Create or update scanner findings and evidence history in FalkorDB."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from graph_db import get_graph
from ingestion.schemas import (
    ScanRunResult,
    compute_finding_fingerprint,
    determine_lifecycle_transition,
    resolve_canonical_endpoint_id,
    resolve_canonical_finding_id,
)


def save_finding(finding: dict) -> str:
    """Idempotently persist or update a finding, adding a new evidence observation.
    
    Preserves historical observations while updating finding status and timestamps.
    """
    if not isinstance(finding, dict):
        raise TypeError(f"Finding must be a dictionary, got {type(finding).__name__}")

    required = [
        "finding_id", "title", "type", "severity_level",
        "status", "source", "website_name",
        "endpoint_id", "endpoint_path", "evidence_id",
        "evidence_summary", "evidence_confirmed",
    ]

    missing = [key for key in required if key not in finding]
    if missing:
        raise ValueError(f"Missing required finding fields: {missing}")

    if not str(finding.get("evidence_summary", "")).strip():
        raise ValueError("Evidence summary must not be empty.")

    data: Dict[str, Any] = dict(finding)
    project_id = data.get("project_id", "shop-demo")
    data["project_id"] = project_id

    if "fingerprint" not in data or not data["fingerprint"]:
        data["fingerprint"] = compute_finding_fingerprint(
            project_id, data["type"], data["endpoint_path"]
        )

    if "observed_at" not in data or not data["observed_at"]:
        data["observed_at"] = datetime.now(timezone.utc).isoformat()

    graph = get_graph()

    # Check for existing finding to validate lifecycle transition
    existing = graph.ro_query(
        "MATCH (f:Finding {id:$id}) RETURN f.status",
        params={"id": data["finding_id"]},
    ).result_set

    if existing and existing[0] and existing[0][0]:
        current_status = existing[0][0]
        # Calculate next valid lifecycle state given this observation
        observation_flag = "PASS" if data.get("status") == "REMEDIATED" else "CONFIRMED"
        data["status"] = determine_lifecycle_transition(current_status, observation_flag).value

    query = """
    MERGE (w:Website {id: $project_id})
    SET w.name = $website_name

    MERGE (e:Endpoint {id: $endpoint_id})
    SET e.path = $endpoint_path

    MERGE (w)-[:EXPOSES]->(e)

    MERGE (f:Finding {id: $finding_id})
    SET f.title = $title,
        f.type = $type,
        f.severity_level = $severity_level,
        f.status = $status,
        f.source = $source,
        f.fingerprint = $fingerprint,
        f.last_seen_at = $observed_at

    MERGE (f)-[:AFFECTS]->(e)

    MERGE (ev:Evidence {id: $evidence_id})
    SET ev.summary = $evidence_summary,
        ev.confirmed = $evidence_confirmed,
        ev.observed_at = $observed_at

    MERGE (f)-[:SUPPORTED_BY]->(ev)

    RETURN f.id
    """

    result = graph.query(query, params=data)

    if not result.result_set:
        raise RuntimeError("FalkorDB did not return the finding ID")

    # If the endpoint is ep-root or ep-catalog, ensure routes_to is present
    if data["endpoint_id"] in ("ep-root", "ep-catalog"):
        graph.query("""
            MATCH (e:Endpoint {id:$eid})
            MERGE (s:Service {id:'catalog'})
            SET s.name = 'Catalog Service'
            MERGE (e)-[:ROUTES_TO]->(s)
        """, params={"eid": data["endpoint_id"]})

    return str(result.result_set[0][0])


def save_scan_run(scan_result: ScanRunResult) -> str:
    """Persist a ScanRun node and link it to the project and detected findings."""
    graph = get_graph()

    # 1. Save all findings first
    finding_ids = []
    for finding in scan_result.findings:
        fid = save_finding(finding.to_graph_dict())
        finding_ids.append(fid)

    # 2. Persist the ScanRun execution record
    graph.query("""
        MERGE (w:Website {id: $project_id})
        CREATE (s:ScanRun {
            id: $scan_id,
            project_id: $project_id,
            scanner: $scanner,
            status: $status,
            target_url: $target_url,
            started_at: $started_at,
            completed_at: $completed_at,
            findings_count: $findings_count,
            error_summary: $error_summary
        })
        MERGE (w)-[:HAS_SCAN]->(s)
    """, params={
        "project_id": scan_result.project_id,
        "scan_id": scan_result.scan_id,
        "scanner": scan_result.scanner_name,
        "status": scan_result.status.value,
        "target_url": scan_result.target_url,
        "started_at": scan_result.started_at,
        "completed_at": scan_result.completed_at,
        "findings_count": scan_result.findings_count,
        "error_summary": scan_result.error_summary or "",
    })

    # 3. Link ScanRun to detected findings
    for fid in finding_ids:
        graph.query("""
            MATCH (s:ScanRun {id: $scan_id})
            MATCH (f:Finding {id: $finding_id})
            MERGE (s)-[:DETECTED]->(f)
        """, params={"scan_id": scan_result.scan_id, "finding_id": fid})

    return scan_result.scan_id
