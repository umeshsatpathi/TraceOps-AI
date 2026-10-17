"""Optional LangChain tool wrappers for TraceShield's existing agent.py.

Add these tools to your agent's tools list; no other agent code needs changing.
"""
import json
from langchain.tools import tool
from graph_intelligence import investigate, rank_findings, what_if_classification, record_investigation


@tool
def investigate_graph_context(finding_id: str) -> str:
    """Investigate a finding using FalkorDB dependency traversals, related findings,
    evidence, graph-derived risk and a specific defensive next-action plan.
    Use for security investigations, prioritization, and choosing the next action.
    """
    try:
        return json.dumps(investigate(finding_id), default=str)
    except Exception as error:
        return json.dumps({"error": str(error), "finding_id": finding_id})


@tool
def compare_graph_contexts(finding_ids: list[str]) -> str:
    """Compare/rank 2-10 finding IDs using graph paths, supporting evidence,
    related findings, priorities and recommended defensive next actions.
    """
    try:
        return json.dumps(rank_findings(finding_ids), default=str)
    except Exception as error:
        return json.dumps({"error": str(error), "finding_ids": finding_ids})


@tool
def simulate_data_classification_change(finding_id: str, classification: str) -> str:
    """What-if graph context analysis: compute how an asset's hypothetical
    classification (public, internal or sensitive) changes risk scoring, without
    changing actual FalkorDB data. Use when asked why the graph matters.
    """
    try:
        return json.dumps(what_if_classification(finding_id, classification), default=str)
    except Exception as error:
        return json.dumps({"error": str(error), "finding_id": finding_id, "classification": classification})


@tool
def record_graph_investigation(finding_id: str) -> str:
    """Persist a proposed defensive next action and its investigation trail in
    FalkorDB as Investigation and Action nodes. No remediation is executed.
    Call only when explicitly asked to record or save an investigation.
    """
    try:
        return json.dumps(record_investigation(finding_id), default=str)
    except Exception as error:
        return json.dumps({"error": str(error), "finding_id": finding_id})

