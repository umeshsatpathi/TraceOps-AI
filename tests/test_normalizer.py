"""Unit tests for scanner normalization functions."""
from ingestion.normalizer import (
    normalize_bola_observation,
    normalize_csp_remediation,
    normalize_missing_csp,
)


def test_normalize_missing_csp():
    """Missing CSP must resolve to canonical F-002, ep-root, and CONFIRMED status."""
    res = normalize_missing_csp("http://127.0.0.1:5001/", 200)
    assert res["finding_id"] == "F-002"
    assert res["endpoint_id"] == "ep-root"
    assert res["endpoint_path"] == "/"
    assert res["type"] == "MISSING_CSP"
    assert res["severity_level"] == 2
    assert res["status"] == "CONFIRMED"
    assert res["evidence_confirmed"] is True
    assert "EV-CSP-" in res["evidence_id"]
    assert "fingerprint" in res and len(res["fingerprint"]) == 64


def test_normalize_csp_remediation():
    """Observed CSP header must produce REMEDIATED status with verification evidence."""
    res = normalize_csp_remediation(
        "http://127.0.0.1:5001/",
        200,
        "default-src 'self'",
        current_status="CONFIRMED",
    )
    assert res["finding_id"] == "F-002"
    assert res["status"] == "REMEDIATED"
    assert res["evidence_confirmed"] is True
    assert "default-src 'self'" in res["evidence_summary"]
    assert "EV-CSP-VERIFY-" in res["evidence_id"]


def test_normalize_bola_confirmed():
    """Confirmed BOLA check must produce canonical F-001, ep-orders, and CONFIRMED status."""
    res = normalize_bola_observation(
        observed="CONFIRMED",
        owner_http=200,
        other_http=200,
        endpoint_path="/api/orders/{id}",
    )
    assert res["finding_id"] == "F-001"
    assert res["endpoint_id"] == "ep-orders"
    assert res["status"] == "CONFIRMED"
    assert res["severity_level"] == 4
    assert res["evidence_confirmed"] is True
    assert "cross-user access confirmed" in res["evidence_summary"].lower()


def test_normalize_bola_denied():
    """Denied non-owner request must transition finding status to REMEDIATED."""
    res = normalize_bola_observation(
        observed="DENIED",
        owner_http=200,
        other_http=403,
        current_status="CONFIRMED",
    )
    assert res["finding_id"] == "F-001"
    assert res["status"] == "REMEDIATED"
    assert res["evidence_confirmed"] is True
    assert "ownership enforcement verified" in res["evidence_summary"].lower()


def test_normalize_bola_reopened():
    """Confirmed BOLA observation on a previously REMEDIATED finding must REOPEN it."""
    res = normalize_bola_observation(
        observed="CONFIRMED",
        owner_http=200,
        other_http=200,
        current_status="REMEDIATED",
    )
    assert res["finding_id"] == "F-001"
    assert res["status"] == "REOPENED"
