"""Integration and contract tests for scanners: http_headers and bola_check."""
import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError
import pytest

from demoshop.app import Handler, ORDERS
from ingestion.schemas import ScanExecutionStatus
from scanners.http_headers import run_header_scan
from scanners.bola_check import run_bola_scan


# ---------------------------------------------------------------------------
# Scope and Target Security Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "unauthorized_target",
    [
        "http://example.com/",
        "https://google.com/api",
        "http://169.254.169.254/latest/meta-data/",  # Cloud metadata
        "http://192.168.1.100:8000/",                # Private LAN
        "ftp://localhost:21/",                       # Disallowed scheme
        "",                                          # Empty string
    ],
)
def test_scanner_scope_validation_rejects_unauthorized_targets(unauthorized_target):
    """Scanners must reject unauthorized or dangerous targets with FAILED status."""
    header_res = run_header_scan(target_url=unauthorized_target, persist=False)
    assert header_res.status == ScanExecutionStatus.FAILED
    assert "Scope authorization rejected target" in (header_res.error_summary or "")
    assert header_res.findings_count == 0

    bola_res = run_bola_scan(url=unauthorized_target, persist=False)
    assert bola_res.status == ScanExecutionStatus.FAILED
    assert "Scope authorization rejected target" in (bola_res.error_summary or "")
    assert bola_res.findings_count == 0


def test_scanner_network_failure_is_explicitly_failed_never_clean():
    """A connection failure or timeout must report FAILED, never false clean pass."""
    with patch("scanners.http_headers.urlopen", side_effect=URLError("Connection refused")):
        res = run_header_scan(target_url="http://127.0.0.1:5001/", persist=False)
        assert res.status == ScanExecutionStatus.FAILED
        assert "Network error" in (res.error_summary or "")
        assert res.findings_count == 0

    with patch("scanners.bola_check.urlopen", side_effect=TimeoutError("Request timed out")):
        res = run_bola_scan(url="http://127.0.0.1:5001/api/orders/101", persist=False)
        assert res.status == ScanExecutionStatus.FAILED
        assert "unreachable" in (res.error_summary or "").lower()
        assert res.findings_count == 0


# ---------------------------------------------------------------------------
# DemoShop Behavioral Tests (Vulnerable vs Secure)
# ---------------------------------------------------------------------------

class MockHTTPResponse:
    def __init__(self, status: int, headers: dict, body: bytes = b""):
        self.status = status
        self.headers = headers
        self._body = body

    def read(self, *args):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_http_header_scan_vulnerable_mode():
    """Vulnerable DemoShop (no CSP header) produces COMPLETED_WITH_FINDINGS."""
    mock_resp = MockHTTPResponse(200, {"Content-Type": "text/html"})
    with patch("scanners.http_headers.urlopen", return_value=mock_resp):
        res = run_header_scan(target_url="http://127.0.0.1:5001/", persist=False)
        assert res.status == ScanExecutionStatus.COMPLETED_WITH_FINDINGS
        assert res.findings_count == 1
        finding = res.findings[0]
        assert finding.finding_id == "F-002"
        assert finding.status == "CONFIRMED"
        assert finding.type == "MISSING_CSP"


def test_http_header_scan_secure_mode():
    """Secure DemoShop (CSP header present) produces COMPLETED_CLEAN with remediation evidence."""
    mock_resp = MockHTTPResponse(
        200,
        {"Content-Type": "text/html", "Content-Security-Policy": "default-src 'self'"},
    )
    with patch("scanners.http_headers.urlopen", return_value=mock_resp):
        res = run_header_scan(target_url="http://127.0.0.1:5001/", persist=False)
        assert res.status == ScanExecutionStatus.COMPLETED_CLEAN
        assert res.findings_count == 1
        finding = res.findings[0]
        assert finding.finding_id == "F-002"
        assert finding.status == "REMEDIATED"
        assert "default-src 'self'" in finding.evidence_summary


def test_bola_scan_vulnerable_mode():
    """In vulnerable mode, non-owner reads Alice's order -> COMPLETED_WITH_FINDINGS."""
    alice_resp = MockHTTPResponse(
        200, {}, json.dumps({"id": "101", "owner": "alice"}).encode()
    )
    # Bob also receives Alice's order (BOLA vulnerability)
    bob_resp = MockHTTPResponse(
        200, {}, json.dumps({"id": "101", "owner": "alice"}).encode()
    )

    with patch("scanners.bola_check.urlopen", side_effect=[alice_resp, bob_resp]):
        res = run_bola_scan(url="http://127.0.0.1:5001/api/orders/101", persist=False)
        assert res.status == ScanExecutionStatus.COMPLETED_WITH_FINDINGS
        assert res.findings_count == 1
        finding = res.findings[0]
        assert finding.finding_id == "F-001"
        assert finding.status == "CONFIRMED"
        assert finding.type == "BOLA"


def test_bola_scan_secure_mode():
    """In secure mode, non-owner request returns 403 Forbidden -> COMPLETED_CLEAN."""
    from urllib.error import HTTPError
    alice_resp = MockHTTPResponse(
        200, {}, json.dumps({"id": "101", "owner": "alice"}).encode()
    )
    # Bob receives HTTP 403 Forbidden
    bob_err = HTTPError("url", 403, "Forbidden", {}, None)

    with patch("scanners.bola_check.urlopen", side_effect=[alice_resp, bob_err]):
        res = run_bola_scan(url="http://127.0.0.1:5001/api/orders/101", persist=False)
        assert res.status == ScanExecutionStatus.COMPLETED_CLEAN
        assert res.findings_count == 1
        finding = res.findings[0]
        assert finding.finding_id == "F-001"
        assert finding.status == "REMEDIATED"
        assert "ownership enforcement verified" in finding.evidence_summary.lower()
