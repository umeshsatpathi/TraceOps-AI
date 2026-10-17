"""TraceShield AI — Phase 4 API Endpoint Integration Tests.

Validates all 12 endpoints defined in docs/API_SPEC.md:
1. GET /api/health
2. GET /api/projects
3. GET /api/projects/{project_id}
4. POST /api/projects/{project_id}/scans
5. GET /api/scans/{scan_id}
6. GET /api/findings
7. GET /api/findings/{finding_id}
8. GET /api/graph
9. GET /api/graph/nodes/{node_id}/neighbors
10. POST /api/investigations
11. GET /api/investigations/{investigation_id}
12. POST /api/verification/bola
+ Error format and schema validation handling.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from ingestion.schemas import ScanExecutionStatus, ScanRunResult

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Health Endpoint Tests
# ---------------------------------------------------------------------------

def test_get_health_ok():
    mock_graph = MagicMock()
    mock_graph.ro_query.return_value.result_set = [[1]]

    with patch("api.routes.health.get_graph", return_value=mock_graph):
        resp = client.get("/api/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["dependencies"]["graph_db"] == "ok"
    assert "timestamp" in data


def test_get_health_db_unavailable():
    with patch("api.routes.health.get_graph", side_effect=RuntimeError("Connection refused")):
        resp = client.get("/api/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["dependencies"]["graph_db"] == "unavailable"


# ---------------------------------------------------------------------------
# 2. Projects Endpoints Tests
# ---------------------------------------------------------------------------

def test_get_projects_list():
    resp = client.get("/api/projects?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "pagination" in data
    assert data["pagination"]["limit"] == 10
    assert len(data["items"]) >= 1


def test_get_project_by_id_found():
    resp = client.get("/api/projects/project-demoshop")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "project-demoshop"
    assert data["name"] == "DemoShop"


def test_get_project_by_id_not_found():
    resp = client.get("/api/projects/non-existent-proj-999")
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"


# ---------------------------------------------------------------------------
# 3. Scans Endpoints Tests
# ---------------------------------------------------------------------------

def test_create_scan_success():
    mock_scan_res = ScanRunResult(
        scan_id="scan-test-001",
        project_id="project-demoshop",
        scanner_name="http_headers",
        status=ScanExecutionStatus.COMPLETED_CLEAN,
        started_at="2026-10-17T10:00:00Z",
        completed_at="2026-10-17T10:00:02Z",
        target_url="http://127.0.0.1:5001/",
        raw_findings=[],
        findings_count=0,
    )

    with patch("api.services.scan_service.run_header_scan", return_value=mock_scan_res), \
         patch("api.services.scan_service.save_scan_run", return_value=None):

        payload = {"scanner": "http_headers", "target": "http://127.0.0.1:5001"}
        resp = client.post("/api/projects/project-demoshop/scans", json=payload)

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "scan-test-001"
    assert data["scanner"] == "http_headers"
    assert data["status"] == "completed_clean"



def test_create_scan_unauthorized_target_rejected():
    payload = {"scanner": "http_headers", "target": "https://evil.attacker.com/probe"}
    resp = client.post("/api/projects/project-demoshop/scans", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "BAD_REQUEST"
    assert "Unauthorized" in data["error"]["message"]


def test_create_scan_unsupported_scanner_rejected():
    payload = {"scanner": "unknown_exploit_scanner", "target": "http://127.0.0.1:5001"}
    resp = client.post("/api/projects/project-demoshop/scans", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "BAD_REQUEST"
    assert "Unsupported scanner" in data["error"]["message"]


def test_get_scan_status_found_and_not_found():
    # Found
    resp = client.get("/api/scans/scan-test-001")
    assert resp.status_code == 200
    assert resp.json()["id"] == "scan-test-001"

    # Missing
    resp_missing = client.get("/api/scans/scan-ghost-999")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


# ---------------------------------------------------------------------------
# 4. Findings Endpoints Tests
# ---------------------------------------------------------------------------

def test_get_findings_list():
    mock_graph = MagicMock()
    items_mock = MagicMock(result_set=[
        [
            "F-001", "BOLA on /api/orders", "api_security", "BOLA",
            "critical", 5, "OPEN", "bola_check",
            "2026-10-17T10:00:00Z", "2026-10-17T10:00:00Z",
            "fp-1234", "project-demoshop",
        ]
    ])
    count_mock = MagicMock(result_set=[[1]])
    mock_graph.ro_query.side_effect = [items_mock, count_mock]

    with patch("api.services.finding_service.get_graph", return_value=mock_graph):
        resp = client.get("/api/findings?limit=10&status=OPEN")


    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["id"] == "F-001"


def test_get_finding_detail_found():
    mock_finding = {
        "id": "F-001",
        "title": "BOLA on /api/orders",
        "type": "BOLA",
        "severity_level": 5,
        "status": "OPEN",
        "source": "bola_check",
    }
    mock_paths = [
        {"website": "DemoShop", "endpoint": "/api/orders", "service": "order-service",
         "database": "Shop Database", "asset": "Customer PII", "classification": "sensitive"}
    ]
    mock_evidence = [{"id": "ev-01", "summary": "BOLA read confirmed", "confirmed": True}]

    mock_graph = MagicMock()
    # Endpoint query
    mock_graph.ro_query.return_value.result_set = [["ep-orders", "/api/orders", "GET", True]]

    with patch("api.services.finding_service.get_finding", return_value=mock_finding), \
         patch("api.services.finding_service.get_graph", return_value=mock_graph), \
         patch("api.services.finding_service.trace_impact", return_value=mock_paths), \
         patch("api.services.finding_service.get_evidence", return_value=mock_evidence), \
         patch("api.services.finding_service.score_priority", return_value={"priority_score": 85}):

        resp = client.get("/api/findings/F-001")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "F-001"
    assert data["endpoint"]["path"] == "/api/orders"
    assert len(data["evidence"]) == 1
    assert len(data["impact_paths"]) == 1
    assert "guidance" in data


def test_get_finding_detail_not_found():
    with patch("api.services.finding_service.get_finding", return_value={"error": "not_found"}):
        resp = client.get("/api/findings/F-999")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


# ---------------------------------------------------------------------------
# 5. Graph Exploration Endpoints Tests
# ---------------------------------------------------------------------------

def test_get_graph_bounded():
    mock_graph = MagicMock()
    mock_graph.ro_query.return_value.result_set = [
        [
            "F-001", ["Finding"], {"title": "BOLA"},
            "ep-orders", ["Endpoint"], {"path": "/api/orders"},
            "AFFECTS", {},
        ]
    ]

    with patch("api.services.graph_service.get_graph", return_value=mock_graph):
        resp = client.get("/api/graph?limit=50&depth=2")

    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert "meta" in data
    assert len(data["nodes"]) >= 2
    assert len(data["edges"]) >= 1


def test_get_graph_neighbors_found():
    mock_graph = MagicMock()
    # Root query
    mock_graph.ro_query.side_effect = [
        # root query
        MagicMock(result_set=[["ep-orders", ["Endpoint"], {"path": "/api/orders"}]]),
        # neighbors query
        MagicMock(result_set=[
            ["svc-orders", ["Service"], {"name": "Orders Service"}, "ROUTES_TO", {}, "ep-orders", "svc-orders"]
        ]),
    ]

    with patch("api.services.graph_service.get_graph", return_value=mock_graph):
        resp = client.get("/api/graph/nodes/ep-orders/neighbors?direction=both")

    assert resp.status_code == 200
    data = resp.json()
    assert data["node"]["id"] == "ep-orders"
    assert len(data["neighbors"]) == 1
    assert data["neighbors"][0]["id"] == "svc-orders"


def test_get_graph_neighbors_invalid_direction():
    resp = client.get("/api/graph/nodes/ep-orders/neighbors?direction=invalid_direction")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


def test_get_graph_neighbors_not_found():
    mock_graph = MagicMock()
    mock_graph.ro_query.return_value.result_set = []

    with patch("api.services.graph_service.get_graph", return_value=mock_graph):
        resp = client.get("/api/graph/nodes/missing-node-999/neighbors")

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


# ---------------------------------------------------------------------------
# 6. Investigation Endpoints Tests
# ---------------------------------------------------------------------------

def test_post_investigations_grounded():
    mock_finding = {
        "id": "F-001",
        "title": "BOLA on /api/orders",
        "type": "BOLA",
        "severity_level": 5,
        "status": "OPEN",
        "source": "bola_check",
    }
    mock_graph = MagicMock()
    mock_graph.ro_query.return_value.result_set = [["F-001"]]

    with patch("api.services.investigation_service.execute_llm_agent", return_value=None), \
         patch("api.services.investigation_service.get_finding", return_value=mock_finding), \
         patch("api.services.investigation_service.trace_impact", return_value=[]), \
         patch("api.services.investigation_service.get_evidence", return_value=[]), \
         patch("api.services.investigation_service.score_priority", return_value={"priority_score": 75}), \
         patch("api.services.investigation_service.get_graph", return_value=mock_graph):

        payload = {
            "project_id": "shop-demo",
            "question": "What is the blast radius of finding F-001?",
            "finding_ids": ["F-001"],
        }
        resp = client.post("/api/investigations", json=payload)

    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["status"] == "completed"
    assert "observed_facts" in data
    assert "uncertainties" in data
    assert "next_actions" in data

    # Test retrieval of investigation by ID
    inv_id = data["id"]
    get_resp = client.get(f"/api/investigations/{inv_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == inv_id


def test_get_investigation_not_found():
    resp = client.get("/api/investigations/inv-missing-999")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


# ---------------------------------------------------------------------------
# 7. Verification Endpoints Tests
# ---------------------------------------------------------------------------

def test_post_verification_bola_confirmed():
    mock_scan_res = ScanRunResult(
        scan_id="scan-bola-v-001",
        project_id="shop-demo",
        scanner_name="bola_check",
        status=ScanExecutionStatus.COMPLETED_WITH_FINDINGS,
        started_at="2026-10-17T10:00:00Z",
        completed_at="2026-10-17T10:00:01Z",
        target_url="http://127.0.0.1:5001/",
        raw_findings=[{"type": "BOLA", "endpoint": "/api/orders/4375"}],
        findings_count=1,
    )


    with patch("api.services.scan_service.run_bola_scan", return_value=mock_scan_res), \
         patch("api.services.scan_service.save_bola_test", return_value=None):

        payload = {"project_id": "shop-demo", "target_url": "http://127.0.0.1:5001"}
        resp = client.post("/api/verification/bola", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["outcome"] == "CONFIRMED_UNAUTHORIZED_ACCESS"
    assert data["status"] == "CONFIRMED"
    assert data["finding_id"] == "F-001"


def test_post_verification_bola_unauthorized_target_rejected():
    payload = {"project_id": "shop-demo", "target_url": "http://169.254.169.254/secret"}
    resp = client.post("/api/verification/bola", json=payload)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


def test_post_verification_bola_denied():
    mock_scan_res = ScanRunResult(
        scan_id="scan-bola-v-002",
        project_id="shop-demo",
        scanner_name="bola_check",
        status=ScanExecutionStatus.COMPLETED_CLEAN,
        started_at="2026-10-17T10:00:00Z",
        completed_at="2026-10-17T10:00:01Z",
        target_url="http://127.0.0.1:5001/",
        raw_findings=[],
        findings_count=0,
        execution_metadata={"owner_http": 200, "other_http": 403},
    )

    with patch("api.services.scan_service.run_bola_scan", return_value=mock_scan_res), \
         patch("api.services.scan_service.save_bola_test", return_value=None):

        payload = {"project_id": "shop-demo", "target_url": "http://127.0.0.1:5001"}
        resp = client.post("/api/verification/bola", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["outcome"] == "DENIED_ACCESS"
    assert data["status"] == "REMEDIATED"


def test_post_verification_bola_inconclusive():
    mock_scan_res = ScanRunResult(
        scan_id="scan-bola-v-003",
        project_id="shop-demo",
        scanner_name="bola_check",
        status=ScanExecutionStatus.FAILED,
        started_at="2026-10-17T10:00:00Z",
        completed_at="2026-10-17T10:00:01Z",
        target_url="http://127.0.0.1:5001/",
        raw_findings=[],
        findings_count=0,
        error_summary="Test inconclusive: owner HTTP 500",
        execution_metadata={"observed_outcome": "INCONCLUSIVE"},
    )

    with patch("api.services.scan_service.run_bola_scan", return_value=mock_scan_res):
        payload = {"project_id": "shop-demo", "target_url": "http://127.0.0.1:5001"}
        resp = client.post("/api/verification/bola", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["outcome"] == "INCONCLUSIVE"
    assert data["status"] == "INCONCLUSIVE"



# ---------------------------------------------------------------------------
# 8. Schema Validation & Safe Error Envelope Tests
# ---------------------------------------------------------------------------

def test_schema_validation_error_format():
    # Missing required field 'question'
    payload = {"project_id": "shop-demo"}
    resp = client.post("/api/investigations", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "Request validation failed"
    assert isinstance(data["error"]["details"], list)
    assert "request_id" in data["error"]
