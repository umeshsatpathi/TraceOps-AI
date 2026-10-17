# TraceShield-AI — API Specification

## 1. Purpose and Status

This document defines the proposed REST contract between the React/Vite JavaScript frontend and the Python security-analysis system: scanners, ingestion, FalkorDB graph queries, graph intelligence, and the AI investigation agent.

It covers project management, scans, findings, evidence, graph exploration, investigations, and controlled verification. All endpoints are **proposed** until implemented and verified. The existing Streamlit dashboard is not a REST API; browser code must not assume these endpoints exist.

## 2. Mandatory Implementation Context

Before implementing an endpoint, inspect `README.md`, `requirements.txt`, `.env.example`, `graph_db.py`, `graph_tools.py`, `graph_intelligence.py`, `agent.py`, `agent_graph_tools_v2.py`, scanner and ingestion modules, `seed_graph.py`, `dashboard.py`, and `docker-compose.yml`.

Inspect actual signatures, result shapes, failures, and side effects. Reuse existing behavior where appropriate; do not invent function names or rewrite unrelated modules. Also read [ARCHITECTURE.md](ARCHITECTURE.md), [GRAPH_SCHEMA.md](GRAPH_SCHEMA.md), and [GRAPH_SCHEMA_PREREQUISITES.md](GRAPH_SCHEMA_PREREQUISITES.md).

The frontend never imports Python or connects directly to FalkorDB. FastAPI validates inputs, coordinates backend services, and owns database access and security operations.

## 3. API Conventions

- Development base URL: `http://localhost:8000`
- Prefix: `/api`
- JSON bodies/responses use `application/json`.
- The public frontend configuration may use `VITE_API_URL=http://localhost:8000`; it must never hold secrets.
- IDs are opaque strings. The frontend uses returned IDs and never derives them from names or timestamps.
- Timestamps use timezone-aware ISO 8601, preferably UTC.
- List endpoints use `limit` and `offset`, defaulting to `50` and `0`; the backend enforces a maximum page size such as `100`.

### Error response

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found",
    "details": null,
    "request_id": "req-example-001"
  }
}
```

Errors must never expose stack traces, database credentials, internal configuration, or secret-bearing exceptions. If uniform errors are required, FastAPI validation exceptions need a dedicated handler.

## 4. Common Response Models

The final Pydantic models in `api/schemas.py` must reconcile these structures with the implemented graph schema.

### Project

```json
{"id":"project-demoshop","name":"DemoShop","target_type":"web_app","created_at":"2026-10-17T10:00:00Z"}
```

Never return target credentials or sensitive configuration.

### Scan

```json
{"id":"scan-example-001","project_id":"project-demoshop","scanner":"http_headers","status":"completed","started_at":"2026-10-17T10:00:00Z","completed_at":"2026-10-17T10:00:08Z","findings_count":1}
```

Scan statuses are `queued`, `running`, `completed`, `failed`, and `cancelled`. Document whether `findings_count` means new or all observed findings.

### Finding

```json
{"id":"finding-example-001","project_id":"project-demoshop","title":"Missing Content Security Policy","category":"security_headers","severity":"medium","status":"open","first_seen_at":"2026-10-17T10:00:00Z","last_seen_at":"2026-10-17T10:00:00Z"}
```

Severity must be one of `critical`, `high`, `medium`, `low`, `informational`, or `unknown`. Lifecycle values must match the canonical implemented graph schema.

### Evidence

```json
{"id":"evidence-example-001","source":"http_headers","evidence_type":"http_header","summary":"The response did not include the expected security header.","observed_at":"2026-10-17T10:00:08Z","scan_id":"scan-example-001"}
```

Detailed artifacts are not returned by default and require authorized, sanitized access.

### Graph view

```json
{
  "nodes": [{"id":"finding-example-001","label":"Finding","properties":{"title":"Missing Content Security Policy","severity":"medium","status":"open"}}],
  "edges": [{"id":"edge-example-001","source":"finding-example-001","target":"evidence-example-001","type":"SUPPORTED_BY"}],
  "meta": {"node_count": 2, "edge_count": 1, "truncated": false}
}
```

Only return graph data needed for the requested view; never expose FalkorDB internals or sensitive node properties.

## 5. Proposed Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | API and dependency health |
| `GET` | `/api/projects` | Paginated registered projects |
| `GET` | `/api/projects/{project_id}` | Project details and reliable summary |
| `POST` | `/api/projects/{project_id}/scans` | Request an allowed scan |
| `GET` | `/api/scans/{scan_id}` | Scan state and safe summary |
| `GET` | `/api/findings` | Filtered, paginated findings |
| `GET` | `/api/findings/{finding_id}` | Finding, evidence, and affected entities |
| `GET` | `/api/graph` | Bounded frontend graph view |
| `GET` | `/api/graph/nodes/{node_id}/neighbors` | Scoped neighboring nodes and edges |
| `POST` | `/api/investigations` | Start an AI-assisted investigation |
| `GET` | `/api/investigations/{investigation_id}` | Investigation state and result |
| `POST` | `/api/verification/bola` | Authorized BOLA verification workflow |

### Health: `GET /api/health`

Return process health and dependency state without falsely reporting healthy when FalkorDB is unavailable.

```json
{"status":"ok","dependencies":{"graph_db":"ok"}}
```

### Projects

`GET /api/projects` accepts `limit` and `offset` and returns `{ "items": [], "pagination": { "limit": 50, "offset": 0, "total": 0 } }`.

`GET /api/projects/{project_id}` returns the registered project and only reliably calculated summary fields. Return `404` when absent. Seeded graph nodes are not automatically a complete project-management system.

### Start scan: `POST /api/projects/{project_id}/scans`

An illustrative request is:

```json
{"scanner":"http_headers","target":"http://127.0.0.1:8000"}
```

Prefer a registered project target to an unrestricted URL. Support only approved scanner IDs, validate scope server-side, prevent SSRF, enforce timeouts/rate limits, and never run client-supplied commands. Return `202` only for genuinely asynchronous work; otherwise document synchronous `200` behavior.

### Scan status: `GET /api/scans/{scan_id}`

Return status, timestamps, findings count, and a sanitized `error_summary`; return `404` if absent. Never expose raw exceptions.

### Findings: `GET /api/findings` and `GET /api/findings/{finding_id}`

List filters: `project_id`, `scan_id`, `severity`, `status`, `category`, `limit`, and `offset`. Unknown filters must fail validation, ordering must be deterministic, and filtering by `scan_id` means findings observed by that scan.

Finding details contain only actual graph evidence and affected entities. Use empty arrays for missing relationships rather than fabricating them.

### Graph: `GET /api/graph`

Accept proposed `project_id`, `finding_id`, `depth`, and `limit`. Validate a conservative maximum depth and result size, scope by project, deduplicate response nodes/edges, retain relationship direction/type, remove sensitive properties, and set `meta.truncated` when relevant.

`GET /api/graph/nodes/{node_id}/neighbors` accepts `direction` (`in`, `out`, or `both`), optional `relationship_type`, and `limit`; it returns the selected node, neighboring nodes, connecting edges, and metadata without leaking unrelated project data.

### Investigations

`POST /api/investigations` accepts a project ID, question, and optional/validated finding IDs. Example:

```json
{"project_id":"project-demoshop","question":"Which endpoints are associated with this finding and what evidence supports it?","finding_ids":["finding-example-001"]}
```

Choose and document synchronous or asynchronous execution. The agent uses registered backend tools and returns only evidence it actually retrieved.

`GET /api/investigations/{investigation_id}` returns status, answer, used finding/evidence IDs, related node IDs, and timestamps. A result endpoint requires persistent investigation/job tracking if work is asynchronous.

### BOLA verification: `POST /api/verification/bola`

Use only an authorized project and a predefined validated test profile. Preserve distinct outcomes for denied access, confirmed unauthorized access, inconclusive checks, and errors. Do not permit arbitrary target execution; persist results through supported verification and ingestion paths.

## 6. HTTP Status Rules

| Status | Meaning |
|---|---|
| `200` | Successful request |
| `201` | Synchronously created resource |
| `202` | Accepted asynchronous operation |
| `400` | Invalid/unsupported request |
| `401` | Authentication required or invalid |
| `403` | Forbidden operation |
| `404` | Missing resource |
| `409` | State conflict |
| `422` | Validation failure |
| `429` | Rate-limited request |
| `500` | Unexpected server failure |
| `503` | Required dependency unavailable |

## 7. Frontend Contract

Centralize requests in `frontend/src/services/`; do not scatter fetch calls through React components. The service file convention is JavaScript: `api.js`, `projects.js`, `scans.js`, `findings.js`, `graph.js`, and `investigations.js` as needed.

The frontend uses returned IDs, displays loading/error/empty states, handles optional fields safely, does not assume immediate completion, renders the returned nodes/edges, and never stores backend secrets.

## 8. Backend Guidance

Routes parse/validate requests and serialize responses. Services coordinate scanning, ingestion, graph queries, and the agent. Existing modules retain core logic. Routes must not contain raw Cypher or large scanner implementations.

Possible future structure includes `api/dependencies.py`, `api/routes/health.py`, and service modules for scans, findings, graph, and investigations; add them only when their behavior is being implemented.

Map known errors to safe responses, log diagnostics server-side, configure CORS only for actual frontend origins (commonly `http://localhost:5173`), and select an appropriate asynchronous model only when the workload requires it.

## 9. Testing and Delivery

Every implemented route needs unit, integration, and API tests for validation, serialization, error mapping, graph scope/traversal limits, scanner/ingestion flow, investigation evidence references, dependency outages, and unauthorized scan rejection.

Implement incrementally: inspect/reuse modules, create FastAPI and health, add findings, add graph serialization, connect React, add scans and status tracking, then investigations and verification. The first milestone is existing FalkorDB findings retrieved through FastAPI and explored from React.

The API is complete only when the service starts and reports health, schemas validate contracts, findings/graph data are stable JSON, frontend access is API-only, scan/investigation status is accurate, errors are safe, target scope is enforced, tests pass, and documentation matches implementation.

## 10. Future Extensions

Future capabilities may include repository registration, SAST/SCA integrations, external report import, analyst annotations, remediation workflows, authentication/RBAC, report exports, and live progress events. Add them only with supporting workflows and data models.
