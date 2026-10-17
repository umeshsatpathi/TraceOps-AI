"""TraceShield AI — Phase 3 Investigation Agent & Service Tests.

Validates:
- Tool invocation across all registered graph tools
- Evidence grounding and cross-referencing against FalkorDB
- Separation of observed facts, inferred relationships, and explicit uncertainties
- Multi-hop architectural impact verification
- Deterministic fallback when LLM is unavailable or unconfigured
- Retrieval of past investigations by ID
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from api.schemas import InvestigationRequest, InvestigationResponse
from api.services.investigation_service import (
    collect_grounded_context,
    generate_deterministic_investigation_answer,
    get_investigation_by_id,
    resolve_requested_findings,
    run_investigation,
    verify_referenced_entities,
)


def test_resolve_requested_findings_explicit():
    res = resolve_requested_findings("What is the impact?", ["F-001", "F-004"])
    # F-004 should canonicalize to F-001, deduped
    assert res == ["F-001"]


def test_resolve_requested_findings_from_question_regex():
    res = resolve_requested_findings("Investigate finding f-001 and F-002 please")
    assert "F-001" in res
    assert "F-002" in res


def test_verify_referenced_entities_with_mocked_graph():
    mock_graph = MagicMock()
    # F-001 exists, F-999 does not
    def mock_ro_query(query, params=None):
        mock_res = MagicMock()
        if params and params.get("id") == "F-001":
            mock_res.result_set = [["F-001"]]
        elif params and params.get("id") == "ev-valid":
            mock_res.result_set = [["ev-valid"]]
        else:
            mock_res.result_set = []
        return mock_res

    mock_graph.ro_query.side_effect = mock_ro_query

    with patch("api.services.investigation_service.get_graph", return_value=mock_graph):
        verified_f, verified_e, missing = verify_referenced_entities(
            ["F-001", "F-999"], ["ev-valid", "ev-ghost"]
        )

    assert "F-001" in verified_f
    assert "F-999" not in verified_f
    assert "ev-valid" in verified_e
    assert "ev-ghost" not in verified_e
    assert "F-999" in missing
    assert "ev-ghost" in missing


def test_collect_grounded_context_multi_hop():
    mock_finding = {
        "id": "F-001",
        "title": "BOLA Order Access",
        "type": "BOLA",
        "severity_level": 5,
        "status": "OPEN",
        "source": "scanners/bola_check.py",
    }
    mock_paths = [
        {
            "website": "DemoShop",
            "endpoint": "/api/orders",
            "service": "order-service",
            "database": "Shop Database",
            "asset": "Customer PII",
            "classification": "sensitive",
        }
    ]
    mock_evidence = [
        {"id": "ev-bola-1", "summary": "BOLA cross-tenant access confirmed", "confirmed": True}
    ]

    with patch("api.services.investigation_service.get_finding", return_value=mock_finding), \
         patch("api.services.investigation_service.trace_impact", return_value=mock_paths), \
         patch("api.services.investigation_service.get_evidence", return_value=mock_evidence), \
         patch("api.services.investigation_service.score_priority", return_value={"priority_score": 88}):

        ctx = collect_grounded_context(["F-001"])

    assert len(ctx["findings"]) == 1
    assert len(ctx["evidence"]) == 1
    assert len(ctx["affected_components"]) == 1
    comp = ctx["affected_components"][0]
    assert comp["service"] == "order-service"
    assert comp["data_asset"] == "Customer PII"

    # Verify separation of observed facts, inferred relationships, and uncertainties
    assert any("recorded status 'OPEN'" in f for f in ctx["observed_facts"])
    assert any("order-service, which queries database Shop Database" in r for r in ctx["inferred_relationships"])
    assert any("does not prove" in u.lower() or "not confirmed" in u.lower() for u in ctx["uncertainties"])
    assert len(ctx["actions"]) >= 1
    assert ctx["actions"][0]["requires_approval"] is True


def test_run_investigation_deterministic_fallback():
    mock_finding = {
        "id": "F-001",
        "title": "BOLA on /api/orders",
        "type": "BOLA",
        "severity_level": 5,
        "status": "OPEN",
        "source": "bola_check",
    }
    mock_paths = [
        {
            "website": "DemoShop",
            "endpoint": "/api/orders",
            "service": "orders",
            "database": "orders-db",
            "asset": "Orders Data",
            "classification": "sensitive",
        }
    ]
    mock_evidence = [
        {"id": "ev-01", "summary": "Unauthorized order read returned 200", "confirmed": True}
    ]

    mock_graph = MagicMock()
    mock_graph.ro_query.return_value.result_set = [["F-001"]]

    # Ensure LLM returns None (simulating absent GOOGLE_API_KEY)
    with patch("api.services.investigation_service.execute_llm_agent", return_value=None), \
         patch("api.services.investigation_service.get_finding", return_value=mock_finding), \
         patch("api.services.investigation_service.trace_impact", return_value=mock_paths), \
         patch("api.services.investigation_service.get_evidence", return_value=mock_evidence), \
         patch("api.services.investigation_service.score_priority", return_value={"priority_score": 90}), \
         patch("api.services.investigation_service.get_graph", return_value=mock_graph):

        req = InvestigationRequest(
            project_id="shop-demo",
            question="Investigate finding F-001 and recommend safe next steps",
            finding_ids=["F-001"],
        )
        res = run_investigation(req)

    assert isinstance(res, InvestigationResponse)
    assert res.status == "completed"
    assert "F-001" in res.finding_ids
    assert len(res.observed_facts) > 0
    assert len(res.uncertainties) > 0
    assert len(res.next_actions) > 0
    assert "Security Investigation Report" in res.answer
    assert "Customer" in res.answer or "Orders" in res.answer or "BOLA" in res.answer

    # Verify cached retrieval
    cached = get_investigation_by_id(res.id)
    assert cached is not None
    assert cached.id == res.id


def test_run_investigation_with_mocked_llm():
    mock_finding = {
        "id": "F-002",
        "title": "Missing Content Security Policy",
        "type": "CSP",
        "severity_level": 2,
        "status": "OPEN",
        "source": "http_headers",
    }

    mock_graph = MagicMock()
    mock_graph.ro_query.return_value.result_set = [["F-002"]]

    llm_mock_report = "Agent Report: Verified missing CSP on root endpoint."

    with patch("api.services.investigation_service.execute_llm_agent", return_value=llm_mock_report), \
         patch("api.services.investigation_service.get_finding", return_value=mock_finding), \
         patch("api.services.investigation_service.trace_impact", return_value=[]), \
         patch("api.services.investigation_service.get_evidence", return_value=[]), \
         patch("api.services.investigation_service.score_priority", return_value={"priority_score": 40}), \
         patch("api.services.investigation_service.get_graph", return_value=mock_graph):

        req = InvestigationRequest(
            project_id="shop-demo",
            question="Analyze F-002",
            finding_ids=["F-002"],
        )
        res = run_investigation(req)

    assert res.answer == llm_mock_report
    assert "F-002" in res.finding_ids
