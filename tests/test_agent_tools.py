"""Unit tests for agent graph tools and tool registration."""
import json
from unittest.mock import MagicMock, patch
import pytest

from agent_graph_tools_v2 import (
    investigate_graph_context,
    compare_graph_contexts,
    simulate_data_classification_change,
    record_graph_investigation,
)
from agent import (
    read_finding,
    trace_finding_impact,
    inspect_finding_evidence,
    calculate_finding_priority,
    compare_security_findings,
    build_agent,
)


def test_agent_tool_error_handling_when_db_down():
    """Tools must catch exceptions and return structured JSON error instead of crashing."""
    with patch("agent.get_finding", side_effect=ConnectionError("FalkorDB unreachable")):
        res = read_finding.invoke({"finding_id": "F-001"})
        data = json.loads(res)
        assert "error" in data
        assert "FalkorDB unreachable" in data["error"]

    with patch("agent.trace_impact", side_effect=ConnectionError("FalkorDB unreachable")):
        res = trace_finding_impact.invoke({"finding_id": "F-001"})
        data = json.loads(res)
        assert "error" in data

    with patch("agent.get_evidence", side_effect=ConnectionError("FalkorDB unreachable")):
        res = inspect_finding_evidence.invoke({"finding_id": "F-001"})
        data = json.loads(res)
        assert "error" in data

    with patch("agent.score_priority", side_effect=ConnectionError("FalkorDB unreachable")):
        res = calculate_finding_priority.invoke({"finding_id": "F-001"})
        data = json.loads(res)
        assert "error" in data


def test_agent_v2_tools_registered():
    """All 9 tools (5 core + 4 v2) must be registered in build_agent()."""
    mock_llm = MagicMock()
    with patch("agent.create_llm", return_value=mock_llm), \
         patch("agent.create_agent") as mock_create_agent:
        build_agent()
        assert mock_create_agent.called
        kwargs = mock_create_agent.call_args.kwargs
        tool_names = [t.name for t in kwargs["tools"]]
        
        # Verify both legacy and v2 tools are present
        assert "read_finding" in tool_names
        assert "trace_finding_impact" in tool_names
        assert "inspect_finding_evidence" in tool_names
        assert "calculate_finding_priority" in tool_names
        assert "compare_security_findings" in tool_names
        assert "investigate_graph_context" in tool_names
        assert "compare_graph_contexts" in tool_names
        assert "simulate_data_classification_change" in tool_names
        assert "record_graph_investigation" in tool_names
        assert len(tool_names) == 9
