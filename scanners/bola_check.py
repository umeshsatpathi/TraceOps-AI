"""Local synthetic-user test for Broken Object Level Authorization.

Provides programmatic run_bola_scan() returning a validated ScanRunResult,
plus CLI and history inspection entry points.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ingestion.bola_writer import get_bola_history, save_bola_test
from ingestion.normalizer import normalize_bola_observation
from ingestion.schemas import (
    NormalizedFinding,
    ScanExecutionStatus,
    ScanRunResult,
    generate_scan_id,
    validate_target_url,
)

DEMOSHOP_PORT = os.getenv("DEMOSHOP_PORT", "5001")
BASE_URL = os.getenv("DEMOSHOP_URL", f"http://127.0.0.1:{DEMOSHOP_PORT}")
URL = f"{BASE_URL.rstrip('/')}/api/orders/101"


def request_order(fake_token: str, url: str = URL, timeout: float = 5.0):
    request = Request(url, headers={"Authorization": f"Bearer {fake_token}"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read(4096)
    except HTTPError as exc:
        return exc.code, exc.read(4096)


def run_bola_scan(
    url: str = URL,
    project_id: str = "shop-demo",
    persist: bool = True,
    timeout: float = 5.0,
) -> ScanRunResult:
    """Execute authorized synthetic BOLA check and return a ScanRunResult.
    
    Guarantees that target validation errors or network connection failures
    return FAILED, never falsely reporting clean results.
    """
    scan_id = generate_scan_id("bola_check")
    started_at = datetime.now(timezone.utc).isoformat()

    # 1. Scope authorization validation
    try:
        validated_url = validate_target_url(url)
    except ValueError as err:
        completed_at = datetime.now(timezone.utc).isoformat()
        return ScanRunResult(
            scan_id=scan_id,
            project_id=project_id,
            scanner_name="bola_check",
            target_url=url,
            status=ScanExecutionStatus.FAILED,
            started_at=started_at,
            completed_at=completed_at,
            error_summary=f"Scope authorization rejected target: {err}",
        )

    # 2. Issue authenticated test requests
    try:
        owner_http, owner_body = request_order("demo-alice", validated_url, timeout=timeout)
        other_http, other_body = request_order("demo-bob", validated_url, timeout=timeout)
    except (URLError, TimeoutError, OSError) as exc:
        completed_at = datetime.now(timezone.utc).isoformat()
        return ScanRunResult(
            scan_id=scan_id,
            project_id=project_id,
            scanner_name="bola_check",
            target_url=validated_url,
            status=ScanExecutionStatus.FAILED,
            started_at=started_at,
            completed_at=completed_at,
            error_summary=f"DemoShop target unreachable: {type(exc).__name__} - {exc}",
            execution_metadata={"error_type": type(exc).__name__},
        )

    # 3. Evaluate ownership logic
    owner_is_alice = False
    other_reads_alice = False
    try:
        owner_is_alice = owner_http == 200 and json.loads(owner_body).get("owner") == "alice"
        other_reads_alice = other_http == 200 and json.loads(other_body).get("owner") == "alice"
    except (ValueError, AttributeError, UnicodeDecodeError):
        pass

    completed_at = datetime.now(timezone.utc).isoformat()

    if owner_is_alice and other_reads_alice:
        observed = "CONFIRMED"
        status = ScanExecutionStatus.COMPLETED_WITH_FINDINGS
        error_summary = None
    elif owner_is_alice and other_http in (403, 404):
        observed = "DENIED"
        status = ScanExecutionStatus.COMPLETED_CLEAN
        error_summary = None
    else:
        observed = "INCONCLUSIVE"
        status = ScanExecutionStatus.FAILED
        error_summary = (
            f"Test inconclusive: owner HTTP {owner_http}, non-owner HTTP {other_http}. "
            "Verify route /api/orders/101 and synthetic accounts demo-alice/demo-bob."
        )

    finding_dict = normalize_bola_observation(
        observed=observed,
        owner_http=owner_http,
        other_http=other_http,
        endpoint_path="/api/orders/{id}",
        project_id=project_id,
        target_url=validated_url,
    )
    finding_obj = NormalizedFinding(**finding_dict)
    findings = [finding_obj]

    # 4. Optional graph persistence
    execution_metadata = {
        "owner_http": owner_http,
        "other_http": other_http,
        "observed_outcome": observed,
    }

    if persist:
        try:
            db_outcome = save_bola_test(observed, owner_http, other_http)
            execution_metadata["test_id"] = db_outcome.get("test_id")
            execution_metadata["target_finding_id"] = db_outcome.get("finding_id")
            execution_metadata["finding_status"] = db_outcome.get("status")
        except Exception as exc:
            return ScanRunResult(
                scan_id=scan_id,
                project_id=project_id,
                scanner_name="bola_check",
                target_url=validated_url,
                status=ScanExecutionStatus.FAILED,
                started_at=started_at,
                completed_at=completed_at,
                findings=findings,
                error_summary=f"Graph persistence failed: {exc}",
                execution_metadata=execution_metadata,
            )

    return ScanRunResult(
        scan_id=scan_id,
        project_id=project_id,
        scanner_name="bola_check",
        target_url=validated_url,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        findings=findings,
        error_summary=error_summary,
        execution_metadata=execution_metadata,
    )


def scan(url: str = URL) -> int:
    """CLI/Streamlit convenience wrapper around run_bola_scan."""
    print("[TraceShield] Authorized local synthetic-user BOLA check")
    print(f"[Endpoint] {url}")

    result = run_bola_scan(url=url, persist=True)

    if result.status == ScanExecutionStatus.FAILED and not result.execution_metadata:
        print(f"[ERROR] {result.error_summary}")
        raise RuntimeError(result.error_summary)

    meta = result.execution_metadata
    print(f"[Owner (Alice)] HTTP {meta.get('owner_http')}")
    print(f"[Other user (Bob)] HTTP {meta.get('other_http')}")

    if result.status == ScanExecutionStatus.COMPLETED_WITH_FINDINGS:
        print("[FAIL] Cross-user access observed on synthetic order 101.")
        print(f"[FalkorDB] Stored TestResult: {meta.get('test_id')} (Finding: {meta.get('target_finding_id')}, Status: {meta.get('finding_status')})")
        print(f'[Next] python agent.py "Investigate {meta.get("target_finding_id", "F-001")}"')
        return 0
    elif result.status == ScanExecutionStatus.COMPLETED_CLEAN:
        print("[PASS] Order ownership enforced: non-owner access denied.")
        print(f"[FalkorDB] Stored TestResult: {meta.get('test_id')} (Finding: {meta.get('target_finding_id')}, Status: {meta.get('finding_status')})")
        print(f"[Next] Finding {meta.get('target_finding_id', 'F-001')} status updated to REMEDIATED.")
        return 0
    else:
        print(f"[INCONCLUSIVE] {result.error_summary}")
        return 2


def main():
    parser = argparse.ArgumentParser(description="Local synthetic BOLA check")
    parser.add_argument("--history", action="store_true", help="List saved graph test results")
    parser.add_argument("--url", default=URL, help=f"Target URL (default {URL})")
    args = parser.parse_args()
    if args.history:
        print(json.dumps(get_bola_history(), indent=2))
        return 0
    return scan(args.url)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ConnectionError) as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1)
