"""Pure graph-driven action policy for TraceShield. No database/network imports."""

REMEDIATED = {"REMEDIATED", "RESOLVED", "FIXED", "CLOSED"}

def _status(value) -> str:
    return str(value or "UNKNOWN").upper()

def choose_safe_action(context: dict) -> dict:
    """Pure policy function: choose an allow-listed action from connected context."""
    finding = context.get("finding", {})
    finding_type = str(finding.get("type") or "").upper()
    status = _status(finding.get("status"))
    risk = int(context.get("priority", {}).get("priority_score", 0) or 0)
    paths = context.get("impact_paths", [])
    correlated = context.get("correlated_findings", [])
    sensitive = sorted({
        p.get("asset") for p in paths
        if p.get("classification") == "sensitive" and p.get("asset")
    })

    if "BOLA" in finding_type or "AUTH" in finding_type:
        if status in REMEDIATED:
            reason = (
                f"{finding.get('id')} is remediated but has inherent risk {risk}/100"
                + (f" and reaches sensitive asset(s): {', '.join(sensitive)}" if sensitive else "")
                + ". Run a regression authorization check rather than treating the historical score as current exploitability."
            )
        else:
            reason = (
                f"{finding.get('id')} is an unresolved authorization finding with inherent risk {risk}/100"
                + (f" and a graph path to sensitive asset(s): {', '.join(sensitive)}" if sensitive else "")
                + ". Gather fresh cross-user authorization evidence."
            )
        return {
            "action_kind": "RUN_SYNTHETIC_BOLA_CHECK",
            "action_label": "Run localhost synthetic-user BOLA verification",
            "reason": reason,
            "execution_mode": "ALLOW_LISTED_LOCAL_READ_ONLY",
            "target": "127.0.0.1:8000 /api/orders/101",
            "related_findings": [x.get("finding_id") for x in correlated],
            "sensitive_assets": sensitive,
        }

    if "CSP" in finding_type:
        reason = (
            f"{finding.get('id')} is a {status.lower()} CSP-related finding. "
            "A read-only localhost header rescan can refresh the observation without modifying the application."
        )
        return {
            "action_kind": "RUN_HTTP_HEADER_RESCAN",
            "action_label": "Rescan localhost HTTP security headers",
            "reason": reason,
            "execution_mode": "ALLOW_LISTED_LOCAL_READ_ONLY",
            "target": "127.0.0.1:8000 /",
            "related_findings": [x.get("finding_id") for x in correlated],
            "sensitive_assets": sensitive,
        }

    return {
        "action_kind": "REVIEW_ONLY",
        "action_label": "Record investigation for manual review",
        "reason": "No allow-listed automated verifier is mapped to this finding type. TraceShield will preserve the graph investigation but will not execute an arbitrary test.",
        "execution_mode": "NO_AUTOMATED_EXECUTION",
        "target": finding.get("id"),
        "related_findings": [x.get("finding_id") for x in correlated],
        "sensitive_assets": sensitive,
    }


