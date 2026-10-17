"""Unit tests for ingestion schemas, deterministic fingerprinting, and lifecycle transitions."""
import pytest
from ingestion.schemas import (
    FindingLifecycleStatus,
    FindingSeverity,
    NormalizedFinding,
    compute_finding_fingerprint,
    determine_lifecycle_transition,
    generate_evidence_id,
    resolve_canonical_endpoint_id,
    resolve_canonical_finding_id,
)


def test_compute_finding_fingerprint_deterministic():
    """Fingerprint must be stable and identical regardless of whitespace/casing."""
    fp1 = compute_finding_fingerprint("shop-demo", "BOLA", "/api/orders/{id}")
    fp2 = compute_finding_fingerprint("SHOP-DEMO ", "bola", " /api/orders/{id} ")
    assert fp1 == fp2
    assert len(fp1) == 64  # SHA-256 hex string


def test_compute_finding_fingerprint_distinguishes_endpoints():
    """Fingerprints for different endpoints or types must not collide."""
    fp_orders = compute_finding_fingerprint("shop-demo", "BOLA", "/api/orders/{id}")
    fp_users = compute_finding_fingerprint("shop-demo", "BOLA", "/api/users/{id}")
    fp_csp = compute_finding_fingerprint("shop-demo", "MISSING_CSP", "/api/orders/{id}")
    assert fp_orders != fp_users
    assert fp_orders != fp_csp


def test_resolve_canonical_finding_id():
    """Ensure seeded fixture IDs (F-001, F-002) are canonically matched."""
    assert resolve_canonical_finding_id("shop-demo", "BOLA", "/api/orders/{id}") == "F-001"
    assert resolve_canonical_finding_id("shop-demo", "MISSING_CSP", "/") == "F-002"
    assert resolve_canonical_finding_id("shop-demo", "MISSING_CSP", "/api/products") == "F-002"

    # Unknown finding gets deterministic F-<hash> ID
    unknown_id = resolve_canonical_finding_id("other-proj", "SQLI", "/search")
    assert unknown_id.startswith("F-")
    assert len(unknown_id) == 10  # F- plus 8 chars


def test_resolve_canonical_endpoint_id():
    """Endpoints must resolve to known topology IDs."""
    assert resolve_canonical_endpoint_id("shop-demo", "/api/orders/{id}") == "ep-orders"
    assert resolve_canonical_endpoint_id("shop-demo", "/api/orders/101") == "ep-orders"
    assert resolve_canonical_endpoint_id("shop-demo", "/api/products") == "ep-catalog"
    assert resolve_canonical_endpoint_id("shop-demo", "/") == "ep-root"


def test_generate_evidence_id_unique():
    """Evidence IDs must be unique across invocations."""
    ev1 = generate_evidence_id("F-001")
    ev2 = generate_evidence_id("F-001")
    assert ev1 != ev2
    assert ev1.startswith("EV-F-001-")
    assert ev2.startswith("EV-F-001-")


@pytest.mark.parametrize(
    "curr,obs,expected",
    [
        # New or unverified finding confirmed
        (None, "CONFIRMED", FindingLifecycleStatus.CONFIRMED),
        ("UNVERIFIED", "CONFIRMED", FindingLifecycleStatus.CONFIRMED),
        ("UNVERIFIED", "FAIL", FindingLifecycleStatus.CONFIRMED),
        # Retest passes on previously confirmed finding -> REMEDIATED
        ("CONFIRMED", "DENIED", FindingLifecycleStatus.REMEDIATED),
        ("CONFIRMED", "PASS", FindingLifecycleStatus.REMEDIATED),
        ("CONFIRMED", "CLEAN", FindingLifecycleStatus.REMEDIATED),
        # Regression: finding was REMEDIATED but test now confirms recurrence -> REOPENED
        ("REMEDIATED", "CONFIRMED", FindingLifecycleStatus.REOPENED),
        ("RESOLVED", "FAIL", FindingLifecycleStatus.REOPENED),
        # Retest passes on already remediated finding -> stays REMEDIATED
        ("REMEDIATED", "PASS", FindingLifecycleStatus.REMEDIATED),
        # Inconclusive check retains existing confirmed status
        ("CONFIRMED", "INCONCLUSIVE", FindingLifecycleStatus.CONFIRMED),
        (None, "INCONCLUSIVE", FindingLifecycleStatus.INCONCLUSIVE),
    ],
)
def test_determine_lifecycle_transition(curr, obs, expected):
    result = determine_lifecycle_transition(curr, obs)
    assert result == expected


def test_normalized_finding_validation():
    """NormalizedFinding model must validate properties and convert to dict."""
    fp = compute_finding_fingerprint("shop-demo", "BOLA", "/api/orders/{id}")
    finding = NormalizedFinding(
        finding_id="F-001",
        project_id="shop-demo",
        website_name="DemoShop",
        fingerprint=fp,
        title="BOLA Vulnerability",
        type="BOLA",
        severity_level=4,
        status="CONFIRMED",
        source="scanner",
        endpoint_id="ep-orders",
        endpoint_path="/api/orders/{id}",
        evidence_id="EV-001",
        evidence_summary="Cross-user access confirmed",
        evidence_confirmed=True,
    )

    data = finding.to_graph_dict()
    assert data["finding_id"] == "F-001"
    assert data["status"] == "CONFIRMED"
    assert data["fingerprint"] == fp
    assert data["severity_level"] == 4
    assert data["evidence_confirmed"] is True
