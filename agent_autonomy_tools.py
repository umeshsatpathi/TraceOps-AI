"""LangChain tools that let the TraceShield agent act on connected data safely."""
import json
from langchain.tools import tool

from autonomous_investigator import autonomous_investigate, get_investigation_memory, plan_investigation


@tool
def plan_safe_graph_action(finding_id: str) -> str:
    """Plan the next safe action for a finding using live FalkorDB context.
    This has no side effects and must be used before executing an autonomous action.
    """
    return json.dumps(plan_investigation(finding_id), default=str)


@tool
def run_autonomous_security_investigation(finding_id: str) -> str:
    """Execute TraceShield's graph-directed investigation for one finding.
    The executor is hard-limited to allow-listed read-only localhost DemoShop scans,
    persists its Decision/Action/Investigation audit trail in FalkorDB, and never
    accepts an arbitrary URL or shell command.
    """
    return json.dumps(autonomous_investigate(finding_id, execute=True), default=str)


@tool
def recall_investigation_history(finding_id: str) -> str:
    """Read persistent prior Investigation, Decision, and Action records from FalkorDB.
    Use this to understand what previous TraceShield runs did across sessions.
    """
    return json.dumps(get_investigation_memory(finding_id), default=str)
