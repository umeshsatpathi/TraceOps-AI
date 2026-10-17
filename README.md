# TraceOps-AI

TraceOps-AI (TraceShield) is an explainable, graph-powered security investigation and remediation system. It connects security findings, service dependencies, empirical evidence, deployment topology, and verification results in FalkorDB to help security engineers understand vulnerability blast radius and assess root-cause hypotheses with AI assistance.

The project is a hackathon prototype for authorized local or deterministic demo data. It is not a production auto-remediation platform.

## Goals

- Investigate incidents using recorded evidence.
- Map affected services, endpoints, databases, and data assets in FalkorDB.
- Build an evidence timeline and compare plausible root-cause hypotheses.
- Clearly separate observed facts, graph-derived inferences, and recommendations.
- Require a human approval decision before a simulated remediation.
- Record verification results and final incident status.

## Architecture

```text
React + Vite frontend (JavaScript)
            │
            │ HTTP API calls through frontend/src/services/api.js
            ▼
FastAPI application
            │
            ├── Investigation and graph services
            ├── LangGraph-powered investigation agent
            ├── Evidence ingestion and permitted scanners
            ▼
FalkorDB security knowledge graph
```

The browser never connects directly to FalkorDB or runs scanner scripts. FastAPI validates requests, enforces project scope and approval rules, and returns typed API responses.

## Planned Repository Layout

```text
TraceShield-AI/
├── docs/                         # Architecture, API, graph, plan, and security docs
├── frontend/                     # React + Vite (JavaScript)
│   └── src/
│       ├── services/
│       │   └── api.js            # All frontend API calls
│       ├── pages/
│       ├── components/
│       └── features/
├── api/                          # FastAPI application
│   ├── __init__.py
│   ├── main.py
│   ├── routes/
│   │   ├── projects.py
│   │   ├── findings.py
│   │   ├── graph.py
│   │   ├── investigations.py
│   │   ├── scans.py
│   │   └── verification.py
│   └── schemas.py
├── agent.py                      # LangGraph/LLM investigation orchestration
├── graph_db.py                   # FalkorDB connection setup
├── graph_tools.py                # Graph retrieval and scoring helpers
├── graph_intelligence.py         # Investigation and evidence reasoning
├── scanners/                     # Permitted evidence collectors
├── ingestion/                    # Evidence normalization and persistence
└── requirements.txt
```

## Current Status

Phases 0 through 4 of the roadmap are implemented and verified:
- **Phase 0 & 1:** Canonical finding lifecycles, deterministic fingerprints, and retest transitions.
- **Phase 2:** Strongly-typed scan contracts (`ScanRunResult`, `validate_target_url`), DemoShop test modes, and safe persistence.
- **Phase 3:** Grounded AI investigation pipeline (`api/services/investigation_service.py`), multi-hop verification, explicit uncertainty disclosure, and deterministic graph fallback when LLM keys are absent.
- **Phase 4:** FastAPI application (`api/main.py`) exposing all 12 REST endpoints with Pydantic schemas, safe error envelopes, and CORS support.

### Running FastAPI

Start the backend API server on port 8000:

```bash
uvicorn api.main:app --reload --port 8000
```

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

### Running Tests

Execute the automated test suite (82 passing unit, integration, and API tests):

```bash
pytest -v
```


## Safety Boundaries

- Collect observations only from local or explicitly authorized targets.
- Do not scan, probe, exploit, or remediate public or third-party systems.
- Keep all remediation simulated and require explicit human approval.
- Do not permit the AI agent to approve its own recommendation.
- Treat graph paths and LLM conclusions as hypotheses unless supported by recorded evidence.

## Technology Stack

- React, Vite, JavaScript
- FastAPI, Pydantic, Pytest
- FalkorDB and Cypher
- LangGraph and an LLM with tool calling/structured outputs
- Docker and Docker Compose for local services where appropriate

## Development Notes

Read [Agents.md](Agents.md) and the relevant files in [docs](docs) before changing the project. They define component boundaries, the proposed API, graph decisions, approval rules, and the implementation order.
