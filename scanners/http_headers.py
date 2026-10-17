"""Scan authorized local DemoShop for Content Security Policy header.

Provides programmatic run_header_scan() returning a validated ScanRunResult,
plus the CLI scan() entry point.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from graph_tools import get_evidence, get_finding, score_priority
from ingestion.graph_writer import save_finding
from ingestion.normalizer import normalize_csp_remediation, normalize_missing_csp
from ingestion.schemas import (
    NormalizedFinding,
    ScanExecutionStatus,
    ScanRunResult,
    generate_scan_id,
    validate_target_url,
)

DEMOSHOP_PORT = os.getenv("DEMOSHOP_PORT", "5001")
TARGET_URL = os.getenv("DEMOSHOP_URL", f"http://127.0.0.1:{DEMOSHOP_PORT}/")


def run_header_scan(
    target_url: str = TARGET_URL,
    project_id: str = "shop-demo",
    persist: bool = True,
    timeout: float = 5.0,
) -> ScanRunResult:
    """Execute authorized HTTP header scan and return a structured ScanRunResult.
    
    Guarantees that network errors, timeouts, or invalid targets return FAILED,
    never falsely reporting clean results.
    """
    scan_id = generate_scan_id("http_headers")
    started_at = datetime.now(timezone.utc).isoformat()

    # 1. Scope and target authorization check
    try:
        validated_url = validate_target_url(target_url)
    except ValueError as err:
        completed_at = datetime.now(timezone.utc).isoformat()
        return ScanRunResult(
            scan_id=scan_id,
            project_id=project_id,
            scanner_name="http_headers",
            target_url=target_url,
            status=ScanExecutionStatus.FAILED,
            started_at=started_at,
            completed_at=completed_at,
            error_summary=f"Scope authorization rejected target: {err}",
        )

    # 2. Execute HTTP GET with strict timeout
    try:
        with urlopen(validated_url, timeout=timeout) as response:
            status_code = response.status
            csp_header = response.headers.get("Content-Security-Policy")
    except (URLError, TimeoutError, OSError) as exc:
        completed_at = datetime.now(timezone.utc).isoformat()
        return ScanRunResult(
            scan_id=scan_id,
            project_id=project_id,
            scanner_name="http_headers",
            target_url=validated_url,
            status=ScanExecutionStatus.FAILED,
            started_at=started_at,
            completed_at=completed_at,
            error_summary=f"Network error during scan: {type(exc).__name__} - {exc}",
            execution_metadata={"error_type": type(exc).__name__},
        )
    except HTTPError as exc:
        status_code = exc.code
        csp_header = exc.headers.get("Content-Security-Policy")

    completed_at = datetime.now(timezone.utc).isoformat()

    # 3. Analyze CSP presence and build normalized findings
    if csp_header:
        finding_dict = normalize_csp_remediation(
            validated_url,
            status_code,
            csp_header,
            project_id=project_id,
        )
        status = ScanExecutionStatus.COMPLETED_CLEAN
    else:
        finding_dict = normalize_missing_csp(
            validated_url,
            status_code,
            project_id=project_id,
        )
        status = ScanExecutionStatus.COMPLETED_WITH_FINDINGS

    finding_obj = NormalizedFinding(**finding_dict)
    findings = [finding_obj]

    # 4. Optional graph persistence
    if persist:
        try:
            save_finding(finding_dict)
        except Exception as exc:
            return ScanRunResult(
                scan_id=scan_id,
                project_id=project_id,
                scanner_name="http_headers",
                target_url=validated_url,
                status=ScanExecutionStatus.FAILED,
                started_at=started_at,
                completed_at=completed_at,
                findings=findings,
                error_summary=f"Graph persistence failed: {exc}",
            )

    return ScanRunResult(
        scan_id=scan_id,
        project_id=project_id,
        scanner_name="http_headers",
        target_url=validated_url,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        findings=findings,
        execution_metadata={
            "http_status": status_code,
            "csp_header": csp_header,
        },
    )


def scan(target_url: str = TARGET_URL) -> dict:
    """CLI/Streamlit convenience wrapper around run_header_scan."""
    print("\n[TraceShield] Starting HTTP header scan...")
    print(f"[Target] {target_url}")

    result = run_header_scan(target_url=target_url, persist=True)

    if result.status == ScanExecutionStatus.FAILED:
        print(f"\n[ERROR] Scan failed: {result.error_summary}")
        raise RuntimeError(result.error_summary)

    finding = result.findings[0]
    print(f"[HTTP Status] {result.execution_metadata.get('http_status')}")

    if result.status == ScanExecutionStatus.COMPLETED_CLEAN:
        print(f"[PASS] Content-Security-Policy header is present: '{result.execution_metadata.get('csp_header')}'")
        print(f"\n[FalkorDB] Updated finding status to REMEDIATED: {finding.finding_id}")
        return {"status": "PASS", "finding_id": finding.finding_id, "csp": result.execution_metadata.get("csp_header")}

    print("[FINDING] Content-Security-Policy header missing")
    print(f"\n[Saved to FalkorDB] {finding.finding_id}")
    print("\nFinding:")
    try:
        print(get_finding(finding.finding_id))
        print("\nEvidence:")
        print(get_evidence(finding.finding_id))
        print("\nGraph-based priority:")
        print(score_priority(finding.finding_id))
    except Exception as exc:
        print(f"[Note] Graph inspect skipped ({exc})")

    print("\n[NEXT] Run:")
    print(f'python agent.py "Investigate {finding.finding_id}"')
    return {"status": "FINDING", "finding_id": finding.finding_id}


if __name__ == "__main__":
    try:
        scan()
    except Exception as error:
        print(f"\n[ERROR] {type(error).__name__}: {error}")
        raise SystemExit(1)
