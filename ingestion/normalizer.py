"""Convert security observations into standard normalized finding dictionaries.

Uses ingestion.schemas to ensure stable fingerprints, canonical finding IDs,
guidance, confidence metrics, and unique evidence history across scans.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from ingestion.schemas import (
    NormalizedFinding,
    compute_finding_fingerprint,
    determine_lifecycle_transition,
    generate_evidence_id,
    resolve_canonical_endpoint_id,
    resolve_canonical_finding_id,
    validate_target_url,
)


def normalize_missing_csp(
    url: str,
    http_status: int,
    project_id: str = "shop-demo",
    website_name: str = "DemoShop",
    current_status: str | None = None,
) -> dict:
    """Normalize an absent Content-Security-Policy observation."""
    if not url or not url.strip():
        raise ValueError("Cannot normalize finding: URL must not be empty.")

    parsed = urlsplit(url)
    path = parsed.path or "/"

    fingerprint = compute_finding_fingerprint(project_id, "MISSING_CSP", path)
    finding_id = resolve_canonical_finding_id(project_id, "MISSING_CSP", path)
    endpoint_id = resolve_canonical_endpoint_id(project_id, path, "MISSING_CSP")
    evidence_id = generate_evidence_id(finding_id, prefix="EV-CSP")
    
    # Absent CSP is a confirmed configuration observation
    status = determine_lifecycle_transition(current_status, "CONFIRMED").value

    finding = NormalizedFinding(
        finding_id=finding_id,
        project_id=project_id,
        website_name=website_name,
        fingerprint=fingerprint,
        title="Missing Content Security Policy",
        type="MISSING_CSP",
        severity_level=2,
        status=status,
        source="http_header_scanner",
        endpoint_id=endpoint_id,
        endpoint_path=path,
        evidence_id=evidence_id,
        evidence_summary=(
            f"HTTP GET {url} returned status {http_status}. "
            "The Content-Security-Policy response header was absent. "
            "This is an observed configuration issue, not proof "
            "of successful exploitation."
        ),
        evidence_confirmed=True,
        confidence=1.0,
        guidance="Deploy a Content-Security-Policy response header restricting script-src, object-src, and default-src.",
        target_url=url,
    )
    return finding.to_graph_dict()


def normalize_csp_remediation(
    url: str,
    http_status: int,
    csp_header: str,
    project_id: str = "shop-demo",
    website_name: str = "DemoShop",
    current_status: str | None = None,
) -> dict:
    """Normalize a retest verifying that CSP is present (remediation evidence)."""
    if not url or not url.strip():
        raise ValueError("Cannot normalize remediation: URL must not be empty.")
    if not csp_header or not csp_header.strip():
        raise ValueError("Cannot normalize CSP remediation: CSP header value must not be empty.")

    parsed = urlsplit(url)
    path = parsed.path or "/"

    fingerprint = compute_finding_fingerprint(project_id, "MISSING_CSP", path)
    finding_id = resolve_canonical_finding_id(project_id, "MISSING_CSP", path)
    endpoint_id = resolve_canonical_endpoint_id(project_id, path, "MISSING_CSP")
    evidence_id = generate_evidence_id(finding_id, prefix="EV-CSP-VERIFY")
    
    status = determine_lifecycle_transition(current_status, "PASS").value

    finding = NormalizedFinding(
        finding_id=finding_id,
        project_id=project_id,
        website_name=website_name,
        fingerprint=fingerprint,
        title="Missing Content Security Policy",
        type="MISSING_CSP",
        severity_level=2,
        status=status,
        source="http_header_scanner",
        endpoint_id=endpoint_id,
        endpoint_path=path,
        evidence_id=evidence_id,
        evidence_summary=(
            f"HTTP GET {url} returned status {http_status}. "
            f"The Content-Security-Policy response header was confirmed present: '{csp_header}'. "
            "Defensive header enforcement verified."
        ),
        evidence_confirmed=True,
        confidence=1.0,
        guidance="Maintain Content-Security-Policy policy restrictions and review directives against bypasses.",
        target_url=url,
    )
    return finding.to_graph_dict()


def normalize_bola_observation(
    observed: str,
    owner_http: int,
    other_http: int,
    endpoint_path: str = "/api/orders/{id}",
    project_id: str = "shop-demo",
    website_name: str = "DemoShop",
    current_status: str | None = None,
    target_url: str | None = None,
) -> dict:
    """Normalize a synthetic BOLA check outcome into a canonical finding structure."""
    if not endpoint_path or not endpoint_path.strip():
        raise ValueError("Cannot normalize BOLA observation: endpoint_path must not be empty.")

    fingerprint = compute_finding_fingerprint(project_id, "BOLA", endpoint_path)
    finding_id = resolve_canonical_finding_id(project_id, "BOLA", endpoint_path)
    endpoint_id = resolve_canonical_endpoint_id(project_id, endpoint_path, "BOLA")
    evidence_id = generate_evidence_id(finding_id, prefix="EV-BOLA")

    status = determine_lifecycle_transition(current_status, observed).value

    if observed == "CONFIRMED":
        summary = (
            f"Synthetic authorization check on {endpoint_path}: owner returned HTTP {owner_http}; "
            f"non-owner returned HTTP {other_http} with owner's data. Cross-user access confirmed."
        )
        confirmed = True
        confidence = 1.0
    elif observed == "DENIED":
        summary = (
            f"Synthetic authorization check on {endpoint_path}: owner returned HTTP {owner_http}; "
            f"non-owner request was rejected with HTTP {other_http}. Ownership enforcement verified."
        )
        confirmed = True
        confidence = 1.0
    else:
        summary = (
            f"Synthetic authorization check on {endpoint_path}: owner HTTP {owner_http}, "
            f"other HTTP {other_http}. Observation inconclusive; check service route."
        )
        confirmed = False
        confidence = 0.5

    finding = NormalizedFinding(
        finding_id=finding_id,
        project_id=project_id,
        website_name=website_name,
        fingerprint=fingerprint,
        title="Broken Object Level Authorization on order retrieval",
        type="BOLA",
        severity_level=4,
        status=status,
        source="synthetic_account_http_test",
        endpoint_id=endpoint_id,
        endpoint_path=endpoint_path,
        evidence_id=evidence_id,
        evidence_summary=summary,
        evidence_confirmed=confirmed,
        confidence=confidence,
        guidance="Enforce server-side record ownership checks against authenticated identity before querying or returning data.",
        target_url=target_url or f"http://127.0.0.1:5001{endpoint_path}",
    )
    return finding.to_graph_dict()
