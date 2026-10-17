"""Unit tests for normalizer edge cases and graph_writer persistence contracts."""
from unittest.mock import MagicMock, patch
import pytest
from pydantic import ValidationError

from ingestion.normalizer import (
    normalize_missing_csp,
    normalize_csp_remediation,
    normalize_bola_observation,
)
from ingestion.schemas import (
    NormalizedFinding,
    ScanExecutionStatus,
    ScanRunResult,
    compute_finding_fingerprint,
    validate_target_url,
)
from ingestion.graph_writer import save_finding, save_scan_run


# ---------------------------------------------------------------------------
# Normalizer Validation & Edge Cases
# ---------------------------------------------------------------------------

def test_normalize_missing_csp_empty_url_raises():
    with pytest.raises(ValueError, match="URL must not be empty"):
        normalize_missing_csp("", 200)


def test_normalize_csp_remediation_empty_header_raises():
    with pytest.raises(ValueError, match="CSP header value must not be empty"):
        normalize_csp_remediation("http://127.0.0.1:5001/", 200, "   ")


def test_normalize_bola_observation_empty_endpoint_raises():
    with pytest.raises(ValueError, match="endpoint_path must not be empty"):
        normalize_bola_observation("CONFIRMED", 200, 200, endpoint_path="")


def test_normalized_finding_empty_evidence_raises():
    fp = compute_finding_fingerprint("shop-demo", "BOLA", "/api/orders/{id}")
    with pytest.raises(ValidationError):
        NormalizedFinding(
            finding_id="F-001",
            fingerprint=fp,
            title="BOLA",
            type="BOLA",
            severity_level=4,
            source="scanner",
            endpoint_id="ep-orders",
            endpoint_path="/api/orders/{id}",
            evidence_id="EV-001",
            evidence_summary="",  # Empty evidence must be rejected
        )


def test_normalized_finding_invalid_severity_raises():
    fp = compute_finding_fingerprint("shop-demo", "BOLA", "/api/orders/{id}")
    with pytest.raises(ValidationError):
        NormalizedFinding(
            finding_id="F-001",
            fingerprint=fp,
            title="BOLA",
            type="BOLA",
            severity_level=99,  # Severity must be 0-5
            source="scanner",
            endpoint_id="ep-orders",
            endpoint_path="/api/orders/{id}",
            evidence_id="EV-001",
            evidence_summary="Summary",
        )


def test_normalized_finding_invalid_confidence_raises():
    fp = compute_finding_fingerprint("shop-demo", "BOLA", "/api/orders/{id}")
    with pytest.raises(ValidationError):
        NormalizedFinding(
            finding_id="F-001",
            fingerprint=fp,
            title="BOLA",
            type="BOLA",
            severity_level=2,
            confidence=1.5,  # Confidence must be 0.0-1.0
            source="scanner",
            endpoint_id="ep-orders",
            endpoint_path="/api/orders/{id}",
            evidence_id="EV-001",
            evidence_summary="Summary",
        )


# ---------------------------------------------------------------------------
# Graph Writer Validation & ScanRun Persistence Tests
# ---------------------------------------------------------------------------

def test_save_finding_rejects_non_dict():
    with pytest.raises(TypeError, match="must be a dictionary"):
        save_finding("not-a-dict")  # type: ignore


def test_save_finding_rejects_missing_required_fields():
    with pytest.raises(ValueError, match="Missing required finding fields"):
        save_finding({"finding_id": "F-001"})


def test_save_finding_rejects_empty_evidence():
    incomplete = {
        "finding_id": "F-001", "title": "BOLA", "type": "BOLA",
        "severity_level": 4, "status": "CONFIRMED", "source": "scanner",
        "website_name": "DemoShop", "endpoint_id": "ep-orders",
        "endpoint_path": "/api/orders/{id}", "evidence_id": "EV-001",
        "evidence_summary": "   ",  # Blank evidence
        "evidence_confirmed": True,
    }
    with pytest.raises(ValueError, match="Evidence summary must not be empty"):
        save_finding(incomplete)


class MockResultSet:
    def __init__(self, result_set):
        self.result_set = result_set


def test_save_scan_run_persists_scan_and_detected_edges():
    """save_scan_run must persist ScanRun node and link to detected findings."""
    mock_graph = MagicMock()
    mock_graph.ro_query.return_value = MockResultSet([])
    mock_graph.query.return_value = MockResultSet([["F-002"]])

    finding_dict = normalize_missing_csp("http://127.0.0.1:5001/", 200)
    finding_obj = NormalizedFinding(**finding_dict)

    scan_result = ScanRunResult(
        scan_id="SCAN-TEST-001",
        project_id="shop-demo",
        scanner_name="http_headers",
        target_url="http://127.0.0.1:5001/",
        status=ScanExecutionStatus.COMPLETED_WITH_FINDINGS,
        started_at="2026-10-17T12:00:00Z",
        completed_at="2026-10-17T12:00:01Z",
        findings=[finding_obj],
    )

    with patch("ingestion.graph_writer.get_graph", return_value=mock_graph):
        scan_id = save_scan_run(scan_result)
        assert scan_id == "SCAN-TEST-001"

        # Check Cypher calls: 1 for finding, 1 for ScanRun, 1 for DETECTED edge, plus routes_to
        queries = [call[0][0] for call in mock_graph.query.call_args_list]
        cypher_combined = " ".join(queries)
        assert "CREATE (s:ScanRun" in cypher_combined
        assert "MERGE (s)-[:DETECTED]->(f)" in cypher_combined
