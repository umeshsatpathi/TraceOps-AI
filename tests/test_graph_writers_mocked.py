"""Unit tests for graph_writer and bola_writer using mocked FalkorDB client."""
from unittest.mock import MagicMock, patch
import pytest

from ingestion.graph_writer import save_finding
from ingestion.bola_writer import save_bola_test
from ingestion.normalizer import normalize_missing_csp, normalize_csp_remediation


class MockResultSet:
    def __init__(self, result_set):
        self.result_set = result_set


def test_save_finding_mocked():
    """save_finding must construct parameterized query and return finding ID."""
    mock_graph = MagicMock()
    # Mock ro_query check for existing finding (not found initially)
    mock_graph.ro_query.return_value = MockResultSet([])
    # Mock query execution returning finding ID
    mock_graph.query.return_value = MockResultSet([["F-002"]])

    finding_data = normalize_missing_csp("http://127.0.0.1:5001/", 200)

    with patch("ingestion.graph_writer.get_graph", return_value=mock_graph):
        res = save_finding(finding_data)
        assert res == "F-002"

        # Verify query was called
        assert mock_graph.query.call_count >= 1
        args, kwargs = mock_graph.query.call_args_list[0]
        params = kwargs.get("params", {})
        assert params["finding_id"] == "F-002"
        assert params["endpoint_id"] == "ep-root"
        assert params["project_id"] == "shop-demo"
        assert len(params["fingerprint"]) == 64


def test_save_finding_remediation_transition_mocked():
    """save_finding with CSP present must transition status to REMEDIATED."""
    mock_graph = MagicMock()
    # Mock existing finding returning UNVERIFIED status
    mock_graph.ro_query.return_value = MockResultSet([["UNVERIFIED"]])
    mock_graph.query.return_value = MockResultSet([["F-002"]])

    remediation_data = normalize_csp_remediation(
        "http://127.0.0.1:5001/", 200, "default-src 'self'"
    )

    with patch("ingestion.graph_writer.get_graph", return_value=mock_graph):
        res = save_finding(remediation_data)
        assert res == "F-002"

        args, kwargs = mock_graph.query.call_args_list[0]
        params = kwargs.get("params", {})
        assert params["status"] == "REMEDIATED"


def test_save_bola_test_confirmed_mocked():
    """save_bola_test with CONFIRMED outcome targets F-001 and ep-orders."""
    mock_graph = MagicMock()
    # Existing status: UNVERIFIED
    mock_graph.ro_query.side_effect = [
        MockResultSet([["UNVERIFIED"]]),  # existing F-001 status check
        MockResultSet([]),                # check for legacy F-004
    ]

    with patch("ingestion.bola_writer.get_graph", return_value=mock_graph):
        result = save_bola_test("CONFIRMED", 200, 200)
        assert result["finding_id"] == "F-001"
        assert result["status"] == "CONFIRMED"
        assert result["outcome"] == "CONFIRMED"
        assert result["test_id"].startswith("TEST-")


def test_save_bola_test_denied_mocked():
    """save_bola_test with DENIED outcome transitions status to REMEDIATED."""
    mock_graph = MagicMock()
    # Existing status: CONFIRMED
    mock_graph.ro_query.side_effect = [
        MockResultSet([["CONFIRMED"]]),  # existing F-001 status check
        MockResultSet([]),               # check for legacy F-004
    ]

    with patch("ingestion.bola_writer.get_graph", return_value=mock_graph):
        result = save_bola_test("DENIED", 200, 403)
        assert result["finding_id"] == "F-001"
        assert result["status"] == "REMEDIATED"
        assert result["outcome"] == "DENIED"
