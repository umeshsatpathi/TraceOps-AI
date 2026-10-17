"""Persist synthetic-user authorization test results into the graph.

Reconciles finding IDs with seed_graph.py (F-001) while preserving scan history,
deterministic lifecycle transitions, and unique evidence nodes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from graph_db import get_graph
from ingestion.schemas import (
    compute_finding_fingerprint,
    determine_lifecycle_transition,
    generate_evidence_id,
)


def save_bola_test(
    observed: str,
    owner_http: int,
    other_http: int,
    endpoint_path: str = "/api/orders/{id}",
    target_finding_id: str = "F-001",
) -> dict:
    """Persist BOLA test result.
    
    observed: CONFIRMED, DENIED, or INCONCLUSIVE.
    Enforces finding lifecycle transition:
    - CONFIRMED: UNVERIFIED -> CONFIRMED, REMEDIATED -> REOPENED
    - DENIED: CONFIRMED/REOPENED -> REMEDIATED
    - INCONCLUSIVE: retains previous state
    """
    if observed not in {"CONFIRMED", "DENIED", "INCONCLUSIVE"}:
        raise ValueError(f"Invalid test result outcome: {observed}")

    graph = get_graph()
    checked_at = datetime.now(timezone.utc).isoformat()
    test_id = "TEST-" + uuid4().hex[:12].upper()
    evidence_id = generate_evidence_id(target_finding_id, prefix="EV-BOLA")
    fingerprint = compute_finding_fingerprint("shop-demo", "BOLA", endpoint_path)

    summary = (
        f"Local synthetic-account authorization test on {endpoint_path}: "
        f"owner HTTP {owner_http}; other user HTTP {other_http}; outcome={observed}. "
        "No real user data."
    )

    # 1. Ensure core topology exists and is fully connected
    graph.query("""
        MERGE (w:Website {id:'shop-demo'})
        SET w.name='DemoShop', w.environment='local-only'
        MERGE (ep:Endpoint {id:'ep-orders'})
        SET ep.path=$path, ep.method='GET'
        MERGE (s:Service {id:'orders'})
        SET s.name='Orders Service'
        MERGE (d:Database {id:'shop-db'})
        SET d.name='Shop Database'
        MERGE (a:DataAsset {id:'customer-orders'})
        SET a.name='Customer Orders', a.classification='sensitive'
        MERGE (w)-[:EXPOSES]->(ep)
        MERGE (ep)-[:ROUTES_TO]->(s)
        MERGE (s)-[:QUERIES]->(d)
        MERGE (d)-[:STORES]->(a)
    """, params={"path": endpoint_path})

    # 2. Check current status for lifecycle transition
    existing = graph.ro_query(
        "MATCH (f:Finding {id:$id}) RETURN f.status",
        params={"id": target_finding_id},
    ).result_set

    current_status = existing[0][0] if existing and existing[0] else None
    next_status = determine_lifecycle_transition(current_status, observed).value

    # Target finding IDs: canonical F-001, plus F-004 if present to resolve legacy fixtures
    target_ids = [target_finding_id]
    check_f4 = graph.ro_query("MATCH (f:Finding {id:'F-004'}) RETURN f.id").result_set
    if check_f4:
        target_ids.append("F-004")

    if observed == "CONFIRMED":
        for fid in target_ids:
            graph.query("""
                MATCH (ep:Endpoint {id:'ep-orders'})
                MERGE (f:Finding {id:$fid})
                SET f.title='Confirmed synthetic-account cross-user order access',
                    f.type='BOLA', f.severity_level=4,
                    f.status=$status,
                    f.source='synthetic_account_http_test',
                    f.fingerprint=$fp,
                    f.last_checked_at=$at
                CREATE (ev:Evidence {
                    id:$evid,
                    summary:$summary,
                    confirmed:true,
                    kind:'cross_user_http_observation',
                    observed_at:$at
                })
                MERGE (f)-[:AFFECTS]->(ep)
                MERGE (f)-[:SUPPORTED_BY]->(ev)
            """, params={
                "fid": fid,
                "status": next_status,
                "fp": fingerprint,
                "at": checked_at,
                "evid": evidence_id if fid == target_finding_id else f"{evidence_id}-legacy",
                "summary": summary,
            })
    elif observed == "DENIED":
        for fid in target_ids:
            graph.query("""
                MATCH (f:Finding {id:$fid})
                MATCH (ep:Endpoint {id:'ep-orders'})
                SET f.status='REMEDIATED',
                    f.last_checked_at=$at
                CREATE (ev:Evidence {
                    id:$evid,
                    summary:$summary,
                    confirmed:true,
                    kind:'verified_ownership_enforcement',
                    observed_at:$at
                })
                MERGE (f)-[:SUPPORTED_BY]->(ev)
            """, params={
                "fid": fid,
                "at": checked_at,
                "evid": f"{evidence_id}-VERIFY",
                "summary": summary,
            })

    # 3. Record TestResult observation node
    graph.query("""
        MATCH (ep:Endpoint {id:'ep-orders'})
        CREATE (t:TestResult {
            id:$id, kind:'synthetic_account_bola_check',
            outcome:$outcome, owner_http:$owner,
            other_http:$other, checked_at:$at,
            summary:$summary
        })
        CREATE (t)-[:TESTED]->(ep)
    """, params={
        "id": test_id, "outcome": observed, "owner": owner_http,
        "other": other_http, "at": checked_at, "summary": summary,
    })

    # 4. Link TestResult to evaluated finding(s)
    for fid in target_ids:
        graph.query("""
            MATCH (t:TestResult {id:$tid})
            MATCH (f:Finding {id:$fid})
            MERGE (t)-[:EVALUATES]->(f)
        """, params={"tid": test_id, "fid": fid})

    return {
        "test_id": test_id,
        "outcome": observed,
        "finding_id": target_finding_id,
        "status": next_status,
    }


def get_bola_history():
    """Retrieve chronologically ordered BOLA test records."""
    graph = get_graph()
    rows = graph.ro_query("""
        MATCH (t:TestResult {kind:'synthetic_account_bola_check'})
        RETURN t.checked_at, t.id, t.outcome, t.owner_http, t.other_http
        ORDER BY t.checked_at DESC
    """).result_set
    return [
        dict(zip(("checked_at", "test_id", "outcome", "owner_http", "other_http"), row))
        for row in rows
    ]
