"""TraceShield AI — graph-grounded investigation, correlation, and action planning.

Designed for the existing FalkorDB schema:
Finding-AFFECTS->Endpoint-ROUTES_TO->Service-QUERIES->Database-STORES->DataAsset.

This revision separates inherent graph impact from current remediation state so
historically severe findings do not automatically outrank unresolved ones.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from graph_db import get_graph
from graph_tools import get_finding, trace_impact, get_evidence, score_priority

REMEDIATED = {"REMEDIATED", "RESOLVED", "FIXED", "CLOSED"}
ACTIVE = {"CONFIRMED", "OPEN", "ACTIVE"}


def _status(value) -> str:
    return str(value or "UNKNOWN").upper()


def correlated_findings(finding_id: str) -> list[dict]:
    """Find other findings on the same endpoint, service, or database."""
    graph = get_graph()
    queries = {
        "same_endpoint": """
            MATCH (f:Finding {id:$id})-[:AFFECTS]->(e:Endpoint)<-[:AFFECTS]-(other:Finding)
            WHERE other.id <> $id
            RETURN DISTINCT other.id, other.title
        """,
        "same_service": """
            MATCH (f:Finding {id:$id})-[:AFFECTS]->(:Endpoint)-[:ROUTES_TO]->(s:Service)
            MATCH (other:Finding)-[:AFFECTS]->(:Endpoint)-[:ROUTES_TO]->(s)
            WHERE other.id <> $id
            RETURN DISTINCT other.id, other.title
        """,
        "same_database": """
            MATCH (f:Finding {id:$id})-[:AFFECTS]->(:Endpoint)-[:ROUTES_TO]->(:Service)-[:QUERIES]->(d:Database)
            MATCH (other:Finding)-[:AFFECTS]->(:Endpoint)-[:ROUTES_TO]->(:Service)-[:QUERIES]->(d)
            WHERE other.id <> $id
            RETURN DISTINCT other.id, other.title
        """,
    }
    related: dict[str, dict] = {}
    for reason, query in queries.items():
        for other_id, title in graph.ro_query(query, params={"id": finding_id}).result_set:
            entry = related.setdefault(
                other_id,
                {"finding_id": other_id, "title": title, "reasons": []},
            )
            entry["reasons"].append(reason)
    return list(related.values())


def _sensitive_assets(paths: list[dict]) -> list[str]:
    return sorted({
        p["asset"] for p in paths
        if p.get("classification") == "sensitive" and p.get("asset")
    })


def recommend_next_action(finding: dict, evidence: list[dict], paths: list[dict]) -> dict:
    """Choose a status-aware defensive next action from graph context and evidence."""
    finding_type = str(finding.get("type") or "").upper()
    status = _status(finding.get("status"))
    remediated = status in REMEDIATED
    is_bola = "BOLA" in finding_type or "AUTH" in finding_type
    is_csp = "CSP" in finding_type
    observed = any(ev.get("confirmed") is True for ev in evidence)
    sensitive_assets = _sensitive_assets(paths)

    if is_bola:
        if remediated:
            return {
                "action": "REGRESSION_VERIFY_OBJECT_OWNERSHIP",
                "target": finding.get("id"),
                "why": "This authorization finding is currently remediated, but its graph path reaches sensitive data; a safe regression check protects against reintroduction.",
                "method": "Run the local synthetic-user read-only authorization test and verify the non-owner remains denied while the owner succeeds.",
                "requires_approval": False,
                "verification": "Owner request succeeds and non-owner request returns 403/404 in the authorized DemoShop environment.",
                "sensitive_assets": sensitive_assets,
            }
        if observed or status in ACTIVE:
            return {
                "action": "PLAN_REMEDIATION_AND_RETEST",
                "target": finding.get("id"),
                "why": "Authorization failure has supporting evidence and the graph shows downstream impact.",
                "method": "Have the application owner correct object-level authorization, then run the approved synthetic-user verification test.",
                "requires_approval": True,
                "verification": "The same cross-user request is denied after the approved fix while owner access still works.",
                "sensitive_assets": sensitive_assets,
            }
        return {
            "action": "VERIFY_OBJECT_OWNERSHIP",
            "target": finding.get("id"),
            "why": "The authorization finding is unresolved and needs independent evidence; sensitive downstream assets increase investigation urgency.",
            "method": "Run read-only requests as two synthetic users against synthetic orders and test whether user B can read user A's object.",
            "requires_approval": False,
            "verification": "Record whether cross-user access is allowed or denied, with owner access as a control.",
            "sensitive_assets": sensitive_assets,
        }

    if is_csp:
        if remediated:
            return {
                "action": "REGRESSION_RESCAN_HEADERS",
                "target": finding.get("id"),
                "why": "The finding is marked remediated; a read-only header rescan can verify the control remains present.",
                "method": "Repeat the authorized localhost HTTP-header scan and inspect Content-Security-Policy.",
                "requires_approval": False,
                "verification": "CSP is present and the policy is reviewed for meaningful restrictions.",
                "sensitive_assets": sensitive_assets,
            }
        if observed:
            return {
                "action": "PROPOSE_CSP_POLICY_AND_RESCAN",
                "target": finding.get("id"),
                "why": "The scanner observed an absent CSP response header.",
                "method": "Add a tested Content-Security-Policy header in the local demo configuration after developer approval, then rescan.",
                "requires_approval": True,
                "verification": "Repeat the HTTP-header scan and confirm CSP is present; review the actual policy directives.",
                "sensitive_assets": sensitive_assets,
            }
        return {
            "action": "RECHECK_HTTP_HEADERS",
            "target": finding.get("id"),
            "why": "The missing-CSP finding is unresolved and should be confirmed with a fresh read-only response-header observation.",
            "method": "Repeat a GET request to the authorized local DemoShop and inspect the response headers.",
            "requires_approval": False,
            "verification": "CSP presence or absence is recorded with a timestamp.",
            "sensitive_assets": sensitive_assets,
        }

    return {
        "action": "REVIEW_EVIDENCE_AND_COMPONENT",
        "target": finding.get("id"),
        "why": "Graph context alone does not establish the vulnerability and no allow-listed automated verifier is mapped to this finding type.",
        "method": "Perform an authorized manual review of the affected component and attach sanitized reproducible evidence.",
        "requires_approval": True,
        "verification": "A reproducible test result is linked to the finding.",
        "sensitive_assets": sensitive_assets,
    }


def current_priority_tier(finding: dict, evidence: list[dict]) -> int:
    """Return a deterministic current-work tier. Lower is more urgent.

    0: confirmed/active unresolved
    1: unresolved but not confirmed
    2: remediated/closed regression monitoring
    """
    status = _status(finding.get("status"))
    if status in REMEDIATED:
        return 2
    if status in ACTIVE or any(ev.get("confirmed") is True for ev in evidence):
        return 0
    return 1


def investigate(finding_id: str) -> dict:
    """Produce an auditable multi-hop graph investigation with a next action."""
    finding = get_finding(finding_id)
    if "error" in finding:
        return finding
    paths = trace_impact(finding_id)
    evidence = get_evidence(finding_id)
    priority = score_priority(finding_id)
    tier = current_priority_tier(finding, evidence)
    return {
        "finding": finding,
        "impact_paths": paths,
        "evidence": evidence,
        "priority": priority,
        "current_priority_tier": tier,
        "current_state": "REGRESSION_MONITORING" if tier == 2 else "UNRESOLVED",
        "correlated_findings": correlated_findings(finding_id),
        "next_action": recommend_next_action(finding, evidence, paths),
        "claim_boundaries": [
            "A graph dependency path is potential impact, not an exploit path.",
            "A scanner observation is evidence for the tested condition, not proof of every exploit scenario.",
            "Priority is a heuristic, not probability of compromise.",
            "A successful retest verifies the tested scenario; it does not prove the entire application is vulnerability-free.",
        ],
    }


def rank_findings(finding_ids: list[str]) -> dict:
    """Rank 2–10 findings by current work state, then inherent graph impact."""
    ids = list(dict.fromkeys(x.strip() for x in finding_ids if x.strip()))
    if not 2 <= len(ids) <= 10:
        raise ValueError("Supply 2 to 10 distinct finding IDs")
    valid, errors = [], []
    for finding_id in ids:
        result = investigate(finding_id)
        if "error" in result:
            errors.append(result)
        else:
            valid.append(result)
    valid.sort(key=lambda x: (
        x.get("current_priority_tier", 9),
        -int(x.get("priority", {}).get("priority_score", 0)),
        x.get("finding", {}).get("id", ""),
    ))
    return {
        "ranked_investigations": valid,
        "errors": errors,
        "rule": "Unresolved confirmed findings first, then unresolved unverified findings, then remediated findings for regression monitoring; inherent graph risk breaks ties.",
    }


def what_if_classification(finding_id: str, hypothetical_classification: str = "public") -> dict:
    """Simulate graph-data impact without mutating FalkorDB."""
    allowed = {"public", "internal", "sensitive"}
    if hypothetical_classification not in allowed:
        raise ValueError(f"classification must be one of {sorted(allowed)}")
    finding = get_finding(finding_id)
    if "error" in finding:
        return finding
    original = score_priority(finding_id)
    paths = trace_impact(finding_id)
    if not any(p.get("asset") for p in paths):
        return {
            "finding_id": finding_id,
            "error": "no_linked_data_asset",
            "note": "Cannot simulate classification without a linked DataAsset.",
        }

    altered = [
        dict(p, classification=hypothetical_classification) if p.get("asset") else dict(p)
        for p in paths
    ]
    severity = max(0, min(5, int(finding["severity_level"])))
    exposed = any(p.get("website") is not None for p in altered)
    sensitive = any(p.get("classification") == "sensitive" for p in altered)
    internal = any(p.get("classification") not in (None, "public", "sensitive") for p in altered)
    db_reachable = any(p.get("database") is not None for p in altered)
    exposure = 5 if exposed else 1
    data_impact = 5 if sensitive else (2 if internal else 0)
    reachability = 4 if exposed and db_reachable else (2 if db_reachable else 1)
    hypothetical = round(
        20 * (0.30 * severity + 0.25 * exposure + 0.25 * data_impact + 0.20 * reachability)
    )
    actual = original["priority_score"]
    return {
        "finding_id": finding_id,
        "scenario": f"If linked assets were classified {hypothetical_classification}",
        "actual_score": actual,
        "hypothetical_score": hypothetical,
        "change": hypothetical - actual,
        "graph_modified": False,
        "note": "Only data classification is changed in memory. Severity and exposure are held constant. This demonstrates heuristic sensitivity, not exploit likelihood.",
    }


def record_investigation(finding_id: str) -> dict:
    """Persist a proposed defensive next action and investigation trail."""
    result = investigate(finding_id)
    if "error" in result:
        return result
    graph = get_graph()
    run_id = f"INV-{uuid4().hex[:12].upper()}"
    action_id = f"ACT-{uuid4().hex[:12].upper()}"
    action = result["next_action"]
    graph.query(
        """
        MATCH (f:Finding {id:$finding_id})
        CREATE (i:Investigation {
            id:$run_id, created_at:$created_at,
            source:'graph_intelligence', status:'RECORDED'
        })
        CREATE (a:Action {
            id:$action_id, kind:$action_kind,
            justification:$justification,
            verification:$verification,
            requires_approval:$requires_approval,
            status:'PROPOSED'
        })
        CREATE (i)-[:INVESTIGATES]->(f)
        CREATE (i)-[:PROPOSES]->(a)
        RETURN i.id, a.id
        """,
        params={
            "finding_id": finding_id,
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "action_id": action_id,
            "action_kind": action["action"],
            "justification": action["why"],
            "verification": action["verification"],
            "requires_approval": action["requires_approval"],
        },
    )
    return {"investigation_id": run_id, "action_id": action_id, "investigation": result}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TraceShield graph intelligence")
    sub = parser.add_subparsers(dest="mode", required=True)
    single = sub.add_parser("investigate")
    single.add_argument("finding_id")
    compare = sub.add_parser("compare")
    compare.add_argument("finding_ids", nargs="+")
    whatif = sub.add_parser("whatif")
    whatif.add_argument("finding_id")
    whatif.add_argument("classification", choices=["public", "internal", "sensitive"])
    record = sub.add_parser("record")
    record.add_argument("finding_id")
    args = parser.parse_args()

    if args.mode == "investigate":
        output = investigate(args.finding_id)
    elif args.mode == "compare":
        output = rank_findings(args.finding_ids)
    elif args.mode == "whatif":
        output = what_if_classification(args.finding_id, args.classification)
    else:
        output = record_investigation(args.finding_id)
    print(json.dumps(output, indent=2, default=str))
