"""TraceShield AI — Scan & Verification Service.

Coordinates scoped scanner runs, persists scan runs and detected findings to FalkorDB,
and executes authorized BOLA verification workflows.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from api.schemas import (
    BolaVerificationRequest,
    BolaVerificationResponse,
    PaginationMeta,
    ScanCreateRequest,
    ScanListResponse,
    ScanResponse,
)
from graph_db import get_graph
from ingestion.bola_writer import save_bola_test
from ingestion.graph_writer import save_scan_run
from ingestion.schemas import (
    ScanExecutionStatus,
    validate_target_url,
)
from scanners.bola_check import run_bola_scan
from scanners.http_headers import run_header_scan

logger = logging.getLogger("traceshield.scans")

# In-memory store for scan results
_SCAN_STORE: Dict[str, ScanResponse] = {}

DEFAULT_TARGET = "http://127.0.0.1:5001"
APPROVED_SCANNERS = {"http_headers", "bola_check"}


def resolve_scan_target_url(raw_target: str) -> str:
    """Validate target URL and transparently resolve container hostnames when running in Docker."""
    target_url = validate_target_url(raw_target)
    if os.getenv("RUNNING_IN_DOCKER", "").lower() in ("true", "1", "yes"):
        target_url = target_url.replace("127.0.0.1:5001", "demoshop:5001").replace("localhost:5001", "demoshop:5001")
    return target_url


def execute_scan_job(
    project_id: str,
    request: ScanCreateRequest,
) -> ScanResponse:
    """Execute an authorized scanner run, persist findings to FalkorDB, and return ScanResponse."""
    scanner_id = request.scanner.strip().lower()
    if scanner_id not in APPROVED_SCANNERS:
        raise ValueError(
            f"Unsupported scanner '{request.scanner}'. Approved scanners are: {sorted(APPROVED_SCANNERS)}"
        )

    raw_target = request.target or request.target_url or DEFAULT_TARGET
    target_url = resolve_scan_target_url(raw_target)


    if scanner_id == "http_headers":
        scan_run_result = run_header_scan(target_url=target_url, project_id=project_id, persist=True)
    elif scanner_id == "bola_check":
        scan_run_result = run_bola_scan(target_url=target_url, project_id=project_id, persist=True)
    else:
        raise ValueError(f"Unknown scanner: {scanner_id}")

    # Persist the scan run record
    if scan_run_result:
        try:
            save_scan_run(scan_run_result)
        except Exception as exc:
            logger.warning("Failed saving scan run to FalkorDB: %s", exc)

        response = ScanResponse(
            id=scan_run_result.scan_id,
            project_id=scan_run_result.project_id,
            scanner=scan_run_result.scanner_name,
            status=scan_run_result.status.value,
            started_at=scan_run_result.started_at,
            completed_at=scan_run_result.completed_at,
            findings_count=scan_run_result.findings_count,
            error_summary=scan_run_result.error_summary,
            target_url=target_url,
        )
    else:
        # Fallback empty completed scan
        now = datetime.now(timezone.utc).isoformat()
        response = ScanResponse(
            id=f"scan-{uuid4().hex[:8]}",
            project_id=project_id,
            scanner=scanner_id,
            status="completed",
            started_at=now,
            completed_at=now,
            findings_count=0,
            target_url=target_url,
        )

    _SCAN_STORE[response.id] = response
    return response


def get_scan_by_id(scan_id: str) -> Optional[ScanResponse]:
    """Retrieve scan status by ID from memory store or FalkorDB."""
    norm_id = scan_id.strip()
    if norm_id in _SCAN_STORE:
        return _SCAN_STORE[norm_id]

    try:
        graph = get_graph()
        rows = graph.ro_query(
            """
            MATCH (s {id:$scan_id})
            WHERE s:Scan OR s:ScanRun
            RETURN s.id, s.project_id, s.scanner, s.status, s.started_at,
                   s.completed_at, s.findings_count, s.error_summary, s.target_url
            """,
            params={"scan_id": norm_id},
        ).result_set
        if rows and rows[0]:
            s_id, p_id, scanner, st, s_at, c_at, f_count, err, t_url = rows[0]
            res = ScanResponse(
                id=str(s_id),
                project_id=str(p_id or "shop-demo"),
                scanner=str(scanner or "unknown"),
                status=str(st or "completed"),
                started_at=str(s_at or datetime.now(timezone.utc).isoformat()),
                completed_at=str(c_at) if c_at else None,
                findings_count=int(f_count or 0),
                error_summary=str(err) if err else None,
                target_url=str(t_url) if t_url else None,
            )
            _SCAN_STORE[norm_id] = res
            return res
    except Exception as exc:
        logger.debug("Failed querying scan from FalkorDB: %s", exc)

    return None


def list_scans(
    project_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> ScanListResponse:
    """Retrieve scans from memory store and FalkorDB Scan/ScanRun nodes."""
    all_scans: Dict[str, ScanResponse] = dict(_SCAN_STORE)

    try:
        graph = get_graph()
        rows = graph.ro_query(
            """
            MATCH (s)
            WHERE s:Scan OR s:ScanRun
            RETURN s.id, s.project_id, s.scanner, s.status, s.started_at,
                   s.completed_at, s.findings_count, s.error_summary, s.target_url
            ORDER BY s.started_at DESC
            """
        ).result_set
        for row in rows:
            if not row or not row[0]:
                continue
            s_id, p_id, scanner, st, s_at, c_at, f_count, err, t_url = row
            s_id_str = str(s_id)
            if s_id_str not in all_scans:
                all_scans[s_id_str] = ScanResponse(
                    id=s_id_str,
                    project_id=str(p_id or "project-demoshop"),
                    scanner=str(scanner or "unknown"),
                    status=str(st or "completed"),
                    started_at=str(s_at or datetime.now(timezone.utc).isoformat()),
                    completed_at=str(c_at) if c_at else None,
                    findings_count=int(f_count or 0),
                    error_summary=str(err) if err else None,
                    target_url=str(t_url) if t_url else None,
                )
    except Exception as exc:
        logger.debug("Failed querying scans from FalkorDB: %s", exc)

    items = list(all_scans.values())
    if project_id:
        items = [s for s in items if s.project_id == project_id or project_id in ("project-demoshop", "shop-demo")]

    items.sort(key=lambda s: s.started_at or "", reverse=True)
    total = len(items)
    paged = items[offset : offset + limit]
    return ScanListResponse(
        items=paged,
        pagination=PaginationMeta(limit=limit, offset=offset, total=total),
    )


def run_bola_verification_workflow(
    request: BolaVerificationRequest,
) -> BolaVerificationResponse:
    """Execute authorized BOLA verification and record the verification outcome."""
    raw_target = request.target_url or DEFAULT_TARGET
    target_url = resolve_scan_target_url(raw_target)
    test_id = f"test-bola-{uuid4().hex[:8]}"
    tested_at = datetime.now(timezone.utc).isoformat()

    try:
        run_res = run_bola_scan(target_url=target_url, project_id=request.project_id, persist=True)

        if run_res.status == ScanExecutionStatus.FAILED:
            is_inconclusive = (
                "inconclusive" in (run_res.error_summary or "").lower()
                or run_res.execution_metadata.get("observed_outcome") == "INCONCLUSIVE"
            )
            if is_inconclusive:
                return BolaVerificationResponse(
                    test_id=test_id,
                    project_id=request.project_id,
                    outcome="INCONCLUSIVE",
                    finding_id="F-001",
                    status="INCONCLUSIVE",
                    summary=run_res.error_summary or "BOLA verification inconclusive.",
                    tested_at=tested_at,
                )

            return BolaVerificationResponse(
                test_id=test_id,
                project_id=request.project_id,
                outcome="ERROR",
                finding_id="F-001",
                status="FAILED",
                summary=f"BOLA verification failed during scan execution: {run_res.error_summary}",
                tested_at=tested_at,
            )

        owner_http = int(run_res.execution_metadata.get("owner_http", 200))
        other_http = int(
            run_res.execution_metadata.get(
                "other_http",
                200 if run_res.status == ScanExecutionStatus.COMPLETED_WITH_FINDINGS else 403,
            )
        )

        if run_res.status == ScanExecutionStatus.COMPLETED_WITH_FINDINGS or run_res.findings_count > 0:
            outcome = "CONFIRMED_UNAUTHORIZED_ACCESS"
            status = "CONFIRMED"
            summary = "Cross-tenant access confirmed. User B succeeded in accessing User A's order without authorization."

            try:
                save_bola_test("CONFIRMED", owner_http, other_http)
            except Exception as exc:
                logger.warning("Failed saving BOLA confirmed status to graph: %s", exc)
        else:
            outcome = "DENIED_ACCESS"
            status = "REMEDIATED"
            summary = "Cross-tenant access was properly rejected (403/404). Authorization check passed."

            try:
                save_bola_test("DENIED", owner_http, other_http)
            except Exception as exc:
                logger.warning("Failed saving BOLA denied status to graph: %s", exc)

        return BolaVerificationResponse(
            test_id=test_id,
            project_id=request.project_id,
            outcome=outcome,
            finding_id="F-001",
            status=status,
            summary=summary,
            tested_at=tested_at,
        )

    except Exception as exc:
        logger.error("BOLA verification workflow encountered error: %s", exc)
        return BolaVerificationResponse(
            test_id=test_id,
            project_id=request.project_id,
            outcome="ERROR",
            finding_id="F-001",
            status="FAILED",
            summary=f"BOLA verification check encountered unexpected error: {str(exc)}",
            tested_at=tested_at,
        )
