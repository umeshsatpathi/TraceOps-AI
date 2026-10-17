"""TraceShield AI — Investigation Service.

Provides evidence-grounded AI security investigations, deterministic graph fallbacks,
multi-hop relationship verification, and explicit uncertainty reporting.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from api.schemas import InvestigationRequest, InvestigationResponse
from graph_db import get_graph
from graph_intelligence import (
    correlated_findings,
    investigate,
    recommend_next_action,
)
from graph_tools import (
    get_evidence,
    get_finding,
    score_priority,
    trace_impact,
)

logger = logging.getLogger("traceshield.investigation")


# In-memory store for investigation history
_INVESTIGATION_CACHE: Dict[str, InvestigationResponse] = {}

LEGACY_FINDING_ALIASES = {
    "F-004": "F-001",
    "F-003": "F-002",
}



def canonicalize_finding_id_alias(finding_id: str) -> str:
    """Map legacy finding aliases (F-004, F-003) to canonical seed finding IDs."""
    cleaned = finding_id.strip().upper()
    return LEGACY_FINDING_ALIASES.get(cleaned, cleaned)


def resolve_requested_findings(question: str, explicit_ids: Optional[List[str]] = None) -> List[str]:
    """Extract and canonicalize target finding IDs from explicit parameters or question text."""
    resolved: List[str] = []
    
    if explicit_ids:
        for fid in explicit_ids:
            canonical = canonicalize_finding_id_alias(fid)
            if canonical and canonical not in resolved:
                resolved.append(canonical)
        return resolved

    # Search for finding ID patterns like F-001, F-002, etc.
    matches = re.findall(r"\b[Ff]-?\d{3}\b", question)
    for m in matches:
        clean = m.upper()
        if not clean.startswith("F-"):
            clean = f"F-{clean[1:]}"
        canonical = canonicalize_finding_id_alias(clean)
        if canonical not in resolved:
            resolved.append(canonical)


    if not resolved:
        # Default to canonical primary finding if graph contains any
        try:
            graph = get_graph()
            rows = graph.ro_query("MATCH (f:Finding) RETURN f.id ORDER BY f.id ASC LIMIT 5").result_set
            resolved = [r[0] for r in rows if r and r[0]]
        except Exception:
            resolved = ["F-001"]

    return resolved


def verify_referenced_entities(
    finding_ids: List[str],
    evidence_ids: List[str],
) -> Tuple[List[str], List[str], List[str]]:
    """Cross-reference finding and evidence IDs directly against FalkorDB.
    
    Returns:
        (verified_finding_ids, verified_evidence_ids, unverified_or_missing_ids)
    """
    verified_findings: List[str] = []
    verified_evidence: List[str] = []
    missing_ids: List[str] = []

    try:
        graph = get_graph()
        for fid in finding_ids:
            res = graph.ro_query("MATCH (f:Finding {id:$id}) RETURN f.id", params={"id": fid}).result_set
            if res:
                verified_findings.append(fid)
            else:
                missing_ids.append(fid)

        for eid in evidence_ids:
            res = graph.ro_query("MATCH (e:Evidence {id:$id}) RETURN e.id", params={"id": eid}).result_set
            if res:
                verified_evidence.append(eid)
            else:
                missing_ids.append(eid)
    except Exception as exc:
        logger.warning("FalkorDB unavailable during entity verification: %s", exc)
        # In degraded/disconnected mode, treat requested IDs as unverified
        missing_ids.extend([f"db_unreachable:{fid}" for fid in finding_ids])

    return verified_findings, verified_evidence, missing_ids


def collect_grounded_context(finding_ids: List[str]) -> Dict[str, Any]:
    """Retrieve multi-hop facts, evidence, impact paths, and heuristic priority scores."""
    findings_data = []
    all_evidence = []
    all_paths = []
    all_actions = []
    observed_facts: List[str] = []
    inferred_relationships: List[str] = []
    uncertainties: List[str] = []
    affected_components: List[Dict[str, Any]] = []

    seen_components: Set[str] = set()

    for fid in finding_ids:
        try:
            f_info = get_finding(fid)
            if "error" in f_info:
                uncertainties.append(f"Finding {fid} could not be retrieved from graph: {f_info.get('error')}")
                continue

            findings_data.append(f_info)
            observed_facts.append(
                f"Finding {fid} ({f_info.get('title')}) has recorded status '{f_info.get('status')}' "
                f"and technical severity level {f_info.get('severity_level')}/5."
            )

            # Evidence
            evs = get_evidence(fid)
            all_evidence.extend(evs)
            for ev in evs:
                summary = ev.get("summary", "No details")
                conf_str = "confirmed" if ev.get("confirmed") else "unconfirmed observation"
                observed_facts.append(f"Evidence {ev.get('id')} ({conf_str}): {summary}")

            # Impact Paths (multi-hop traversal)
            paths = trace_impact(fid)
            all_paths.extend(paths)
            for p in paths:
                ep = p.get("endpoint")
                svc = p.get("service")
                db = p.get("database")
                asset = p.get("asset")
                cls = p.get("classification")

                comp_key = f"{ep}:{svc}:{db}:{asset}"
                if comp_key not in seen_components:
                    seen_components.add(comp_key)
                    affected_components.append({
                        "finding_id": fid,
                        "endpoint": ep,
                        "service": svc,
                        "database": db,
                        "data_asset": asset,
                        "classification": cls,
                    })

                if svc and db and asset:
                    inferred_relationships.append(
                        f"Endpoint {ep} routes to {svc}, which queries database {db} storing {asset} "
                        f"(classification: {cls}). This represents an architectural dependency path."
                    )

            # Heuristics & Actions
            prio = score_priority(fid)
            action = recommend_next_action(f_info, evs, paths)
            all_actions.append(action)

            # Standard Uncertainty Disclaimers
            uncertainties.append(
                f"Architectural dependency from {fid} to sensitive assets indicates potential blast radius, "
                "not confirmed remote exploitability."
            )
            if not any(ev.get("confirmed") for ev in evs):
                uncertainties.append(f"Finding {fid} lacks independently verified penetration-test confirmation.")

        except Exception as exc:
            logger.error("Error collecting graph context for %s: %s", fid, exc)
            uncertainties.append(f"Graph context collection failed for {fid}: {exc}")

    # Deduplicate lists while preserving order
    def _dedup(seq: List[str]) -> List[str]:
        return list(dict.fromkeys(seq))

    return {
        "findings": findings_data,
        "evidence": all_evidence,
        "paths": all_paths,
        "actions": all_actions,
        "observed_facts": _dedup(observed_facts),
        "inferred_relationships": _dedup(inferred_relationships),
        "uncertainties": _dedup(uncertainties),
        "affected_components": affected_components,
    }


def execute_llm_agent(question: str) -> Optional[str]:
    """Attempt invocation of the LangChain / Google Gemini agent if configured."""
    try:
        from agent import build_agent
        agent = build_agent()
        result = agent.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config={"recursion_limit": 15},
        )
        final_message = result.get("messages", [])[-1]
        content = getattr(final_message, "content", None) or str(final_message)
        return str(content)
    except Exception as exc:
        logger.info("LLM agent execution unavailable or failed: %s; falling back to deterministic reasoning.", exc)
        return None


def generate_deterministic_investigation_answer(
    question: str,
    context: Dict[str, Any],
) -> str:
    """Produce an explainable, evidence-grounded security investigation report."""
    findings = context.get("findings", [])
    if not findings:
        return (
            "No findings were identified in the security knowledge graph matching the query. "
            "Please check that target findings have been ingested and that FalkorDB is accessible."
        )

    lines: List[str] = [
        "### TraceShield AI — Security Investigation Report",
        f"**Query**: {question}",
        "",
        "#### 1. Graph Finding Overview",
    ]

    for f in findings:
        lines.append(
            f"- **Finding ID**: `{f.get('id')}`\n"
            f"  - **Title**: {f.get('title')}\n"
            f"  - **Type**: {f.get('type')}\n"
            f"  - **Severity**: Level {f.get('severity_level')}/5\n"
            f"  - **Lifecycle Status**: `{f.get('status')}`\n"
            f"  - **Source Scanner**: {f.get('source')}"
        )

    lines.extend([
        "",
        "#### 2. Verified Evidence Grounding",
    ])
    evidence_items = context.get("evidence", [])
    if evidence_items:
        for ev in evidence_items:
            confirmed_tag = "[CONFIRMED]" if ev.get("confirmed") else "[OBSERVATION]"
            lines.append(f"- `{ev.get('id')}` {confirmed_tag}: {ev.get('summary')}")
    else:
        lines.append("- *No supporting evidence nodes currently linked in the graph.*")

    lines.extend([
        "",
        "#### 3. Multi-Hop Dependency & Architectural Impact",
    ])
    components = context.get("affected_components", [])
    if components:
        for c in components:
            lines.append(
                f"- Endpoint `{c.get('endpoint')}` ➔ Service `{c.get('service')}` ➔ "
                f"Database `{c.get('database')}` ➔ Asset `{c.get('data_asset')}` "
                f"*(Classification: {c.get('classification')})*"
            )
    else:
        lines.append("- *No multi-hop downstream dependencies mapped for this finding.*")

    lines.extend([
        "",
        "#### 4. Recommended Defensive Actions (Human Approval Required)",
    ])
    actions = context.get("actions", [])
    for act in actions:
        lines.append(
            f"- **Action**: `{act.get('action')}`\n"
            f"  - **Target**: {act.get('target')}\n"
            f"  - **Rationale**: {act.get('why')}\n"
            f"  - **Proposed Method**: {act.get('method')}\n"
            f"  - **Verification Criteria**: {act.get('verification')}\n"
            f"  - **Requires Human Approval**: {'Yes' if act.get('requires_approval') else 'No'}"
        )

    lines.extend([
        "",
        "#### 5. Explicit Uncertainty & Risk Boundaries",
    ])
    uncertainties = context.get("uncertainties", [])
    for unc in uncertainties:
        lines.append(f"- {unc}")

    return "\n".join(lines)


def run_investigation(request: InvestigationRequest) -> InvestigationResponse:
    """Execute end-to-end grounded investigation with evidence validation and fallback."""
    started_at = datetime.now(timezone.utc).isoformat()
    inv_id = f"inv-{uuid4().hex[:8]}"

    target_finding_ids = resolve_requested_findings(request.question, request.finding_ids)
    context = collect_grounded_context(target_finding_ids)

    # Cross-reference evidence IDs present in context
    collected_ev_ids = [e.get("id") for e in context.get("evidence", []) if e.get("id")]
    verified_findings, verified_evidence, missing_items = verify_referenced_entities(
        target_finding_ids, collected_ev_ids
    )

    if missing_items:
        context["uncertainties"].append(
            f"Unverified or missing graph entities detected during cross-referencing: {', '.join(missing_items)}"
        )

    # Try LLM agent; if unavailable or fails, fall back deterministically
    llm_output = execute_llm_agent(request.question)
    if llm_output:
        answer = llm_output
    else:
        answer = generate_deterministic_investigation_answer(request.question, context)

    completed_at = datetime.now(timezone.utc).isoformat()

    response = InvestigationResponse(
        id=inv_id,
        project_id=request.project_id,
        question=request.question,
        status="completed",
        answer=answer,
        finding_ids=verified_findings if verified_findings else target_finding_ids,
        evidence_ids=verified_evidence if verified_evidence else collected_ev_ids,
        affected_components=context.get("affected_components", []),
        observed_facts=context.get("observed_facts", []),
        inferred_relationships=context.get("inferred_relationships", []),
        uncertainties=context.get("uncertainties", []),
        next_actions=context.get("actions", []),
        started_at=started_at,
        completed_at=completed_at,
    )

    _INVESTIGATION_CACHE[inv_id] = response
    return response


def get_investigation_by_id(investigation_id: str) -> Optional[InvestigationResponse]:
    """Retrieve an existing investigation from cache."""
    return _INVESTIGATION_CACHE.get(investigation_id)


def list_investigations() -> List[InvestigationResponse]:
    """Return all cached investigations."""
    return list(_INVESTIGATION_CACHE.values())
