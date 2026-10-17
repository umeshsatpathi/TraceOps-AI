"""Read-only graph tools; ready for scanners, APIs, and an LLM agent."""
from graph_db import get_graph


def get_finding(finding_id: str) -> dict:
    graph = get_graph()
    result = graph.ro_query(
        "MATCH (f:Finding {id:$id}) RETURN f.id, f.title, f.type, f.severity_level, f.status, f.source, f.fingerprint",
        params={"id": finding_id},
    ).result_set
    if not result:
        return {"error": "finding_not_found", "finding_id": finding_id}
    row = result[0]
    return dict(zip(("id", "title", "type", "severity_level", "status", "source", "fingerprint"), row))


def trace_impact(finding_id: str) -> list[dict]:
    """Traverse finding -> endpoint -> service -> database -> data asset.

    A path is possible architecture impact, NOT proof of successful exploitation.
    """
    graph = get_graph()
    rows = graph.ro_query(
        """
        MATCH (f:Finding {id:$id})-[:AFFECTS]->(e:Endpoint)
        OPTIONAL MATCH (w:Website)-[:EXPOSES]->(e)
        OPTIONAL MATCH (e)-[:ROUTES_TO]->(s:Service)
        OPTIONAL MATCH (s)-[:QUERIES]->(d:Database)
        OPTIONAL MATCH (d)-[:STORES]->(a:DataAsset)
        RETURN w.name, e.path, s.name, d.name, a.name, a.classification
        """,
        params={"id": finding_id},
    ).result_set
    return [
        dict(zip(("website", "endpoint", "service", "database", "asset", "classification"), row))
        for row in rows
    ]


def get_evidence(finding_id: str) -> list[dict]:
    graph = get_graph()
    rows = graph.ro_query(
        """
        MATCH (f:Finding {id:$id})-[:SUPPORTED_BY]->(e:Evidence)
        RETURN e.id, e.summary, e.confirmed
        """,
        params={"id": finding_id},
    ).result_set
    return [dict(zip(("id", "summary", "confirmed"), row)) for row in rows]


def score_priority(finding_id: str) -> dict:
    """Transparent triage heuristic; never return this as exploit probability."""
    finding = get_finding(finding_id)
    if "error" in finding:
        return finding
    paths = trace_impact(finding_id)
    severity = max(0, min(5, int(finding["severity_level"])))
    exposed = any(path["website"] is not None for path in paths)
    sensitive = any(path["classification"] == "sensitive" for path in paths)
    internal = any(path["classification"] not in (None, "public", "sensitive") for path in paths)
    db_reachable = any(path["database"] is not None for path in paths)
    # `exposed` is defined by known graph mapping, not a live network scan.
    exposure = 5 if exposed else 1
    data_impact = 5 if sensitive else (2 if internal else 0)
    reachability = 4 if exposed and db_reachable else (2 if db_reachable else 1)
    risk = round(20 * (0.30 * severity + 0.25 * exposure + 0.25 * data_impact + 0.20 * reachability))
    return {
        "finding_id": finding_id,
        "priority_score": risk,
        "factors": {"severity": severity, "exposure": exposure, "data_impact": data_impact, "reachability": reachability},
        "evidence_status": finding["status"],
        "note": "Heuristic priority, not a probability or proof of exploitability; graph records may be synthetic.",
    }
