# TraceShield-AI — Implementation Plan

## 1. Purpose

This is the phased roadmap for evolving the existing Python, FalkorDB, and AI-agent foundation into a reliable application with a FastAPI REST API and React/Vite JavaScript frontend while preserving working functionality.

## 2. Current State

Existing components include FalkorDB connection/query utilities, graph seeding, HTTP-header scanning, a synthetic BOLA check, normalization/ingestion, a Gemini/LangGraph-related agent, Streamlit dashboard, and local DemoShop.

The following are planned, not implemented: FastAPI REST API, React/Vite frontend, standardized project/scan lifecycle, consistently applied canonical graph schema, general-purpose arbitrary-target scanning, and a fully tested production-ready workflow. Verify all assumptions against source before modifying it.

## 3. Principles

1. Inspect existing functions, data, dependencies, and execution paths first.
2. Preserve Streamlit, scanners, and graph utilities unless an explicit migration replaces them.
3. Stabilize graph IDs, relationships, finding identity, and provenance before frontend work.
4. Deliver each phase as a working, testable increment.
5. Separate scanning, normalization, persistence, investigation logic, API routing, and presentation.
6. Ground agent outputs in graph evidence and communicate uncertainty.
7. Run active tests only for explicitly authorized targets.
8. Test every boundary: scanner → ingestion → graph → agent → API → frontend.
9. Describe only verified behavior as implemented.

## 4. Development Phases

### Phase 0 — Repository Audit and Baseline

**Objective:** establish the real current implementation before architecture changes.

- [ ] Inspect README, dependencies, environment template, Docker configuration, graph modules, seed data, scanners, ingestion, agent tools, and dashboard.
- [ ] Identify entry points, dependencies, environment variables, external services, labels, edges, ID conventions, and query result shapes.
- [ ] Trace one complete scanner → graph → dashboard/agent path.
- [ ] Identify existing tests and supported validation commands.
- [ ] Run supported checks and record baseline results without hiding failures.

**Exit:** the team can explain the current flow and separate confirmed behavior from the target design.

### Phase 1 — Stabilize Graph Data and Finding Lifecycle

**Objective:** make graph identity, evidence, and finding lifecycle consistent.

- [ ] Compare source with [GRAPH_SCHEMA.md](GRAPH_SCHEMA.md) and complete [GRAPH_SCHEMA_PREREQUISITES.md](GRAPH_SCHEMA_PREREQUISITES.md).
- [ ] Define canonical IDs for projects, scans, findings, evidence, endpoints, services, and assets.
- [ ] Resolve seed/ingestion ID mismatches.
- [ ] Implement stable finding fingerprints and scan-run provenance.
- [ ] Deduplicate repeated findings while preserving new evidence/history.
- [ ] Define and enforce finding transitions, including confirmed, inconclusive, remediated, and reopened states.
- [ ] Ensure retests affect only the finding actually tested.
- [ ] Add lifecycle, identity, deduplication, and relationship-integrity tests.

**Exit:** repeated ingestion is predictable, graph relationships remain connected, and state changes are justified by evidence.

### Phase 2 — Stabilize Scanners and Ingestion

**Objective:** make scanner outputs safe and predictable for all consumers.

- [ ] Define a normalized scanner-result contract.
- [ ] Represent success, findings, no findings, failures, and execution metadata distinctly.
- [ ] Normalize severity, confidence, endpoint, evidence, guidance, source, target, and timestamps.
- [ ] Validate scanner results before graph persistence.
- [ ] Make malformed/missing evidence explicit errors rather than silent corruption.
- [ ] Add normalizer edge-case and scanner → normalizer → writer integration tests.
- [ ] Verify the authorized DemoShop vulnerable and secure scenarios.

**Exit:** clean results, errors, and retests create no misleading security conclusion.

### Phase 3 — Validate the Investigation Agent

**Objective:** make evidence-grounded graph investigation dependable before API exposure.

- [x] Verify `agent.py` tool registration against `agent_graph_tools_v2.py`.
- [x] Verify every required graph tool can be invoked.
- [x] Define a structured result: summary, findings, evidence IDs, graph relationships, uncertainty, and next steps.
- [x] Verify each referenced finding/evidence item exists.
- [x] Handle empty, partial, unavailable, or inconsistent graph data plus model/provider failures.
- [x] Add deterministic graph-tool tests, mocked-model orchestration tests, and multi-hop evaluation scenarios.

**Exit:** the agent answers supported questions from retrieved evidence and explicitly identifies uncertainty.

### Phase 4 — Build FastAPI

**Objective:** expose stable capabilities through documented REST contracts.

- [x] Add FastAPI dependencies, API configuration, entry point, and dependency initialization without breaking Streamlit.
- [x] Implement health, project, scan/status, finding, bounded graph/neighbor, and investigation routes in the order defined by [API_SPEC.md](API_SPEC.md).
- [x] Add BOLA verification only after its restricted workflow is tested.
- [x] Implement Pydantic schemas, safe errors, pagination/filtering, CORS, logging, timeouts, and target validation.
- [x] Ensure long scans/investigations do not block ordinary API requests.
- [x] Add API unit and integration tests; update API documentation to actual behavior.

**Exit:** graph data and approved operations are available through stable JSON without frontend Python imports.


### Phase 5 — Implement React + Vite Frontend

**Objective:** create the JavaScript UI that consumes FastAPI.

- [x] Initialize the React/Vite app under `frontend/` and configure `VITE_API_URL`.
- [x] Build centralized service clients in `frontend/src/services/`.
- [x] Implement navigation, project overview, findings list/detail, evidence, scan views, graph explorer, and investigation interface.
- [x] Use bounded graph data for node selection and neighbor exploration.
- [x] Display evidence references and distinguish observed facts from inferred relationships.
- [x] Handle loading, empty, error, and partial states; add responsive/accessibility basics and frontend tests.

**Exit:** supported workflows work only through FastAPI; the browser has no graph or Python access.

### Phase 6 — End-to-End Integration

**Objective:** validate the complete authorized local workflow.

- [ ] Start FalkorDB, backend, and frontend with documented steps.
- [ ] Verify project loading, graph retrieval, scan ingestion, API/frontend finding display, and evidence-backed investigation.
- [ ] Test empty graph, scanner failure, database failure, model-provider failure, repeat scans, and retests.
- [ ] Confirm Streamlit remains functional while its supported dependencies remain in use.
- [ ] Record limitations and update setup/troubleshooting documentation.

**Exit:** another developer can reproduce setup through scan, graph visualization, and investigation.

### Phase 7 — Security, Reliability, and Release Preparation

**Objective:** prepare for controlled demos and further development.

- [ ] Review scanner scope, secrets, ports, CORS, validation, logging, error disclosure, query construction, and user-controlled identifiers.
- [ ] Prevent arbitrary command execution or unrestricted scans.
- [ ] Define authentication/authorization before non-local exposure.
- [ ] Document persistence, backup, reset, cleanup, and known limitations.
- [ ] Run the complete test suite and verify clean installation.
- [ ] Update README with verified commands and actual capabilities.

**Exit:** the project is reproducible, tested, scoped to its intended environment, and transparent about limitations.

## 5. Dependency Order and Priorities

Required sequence: repository audit → graph/lifecycle → scanner/ingestion → agent validation → FastAPI → React/Vite → end-to-end → security/release. Do not integrate the frontend with unstable or undocumented response shapes, and do not expand scanner scope before authorization and ingestion are reliable.

| Priority | Work |
|---|---|
| **P0 — Blocking** | ID/relationship consistency, finding lifecycle, normalization/error handling, agent tool/evidence validation, baseline tests |
| **P1 — Core** | FastAPI entry/config, core routes/schemas, React shell/API client, finding and graph views |
| **P2 — Completion** | Scan status, investigation presentation, end-to-end tests, robust UI states, reproducible setup |
| **P3 — Future** | Additional authorized scanners, repository/dependency analysis, advanced analytics, jobs/history, RBAC, deployment hardening |

## 6. Testing Matrix

| Layer | Required validation |
|---|---|
| Scanners | Findings, clean results, malformed responses, failures |
| Normalization | Contract validation, severity mapping, absent fields |
| Graph writer | Stable IDs, duplicates, edges, retest lifecycle |
| Graph tools | Queries, empty/malformed input |
| Agent | Tool invocation, evidence references, uncertainty, provider failures |
| FastAPI | Schemas, status codes, errors, scope validation |
| React | Loading, empty, success, and error states |
| Integration | Scanner → graph → API → frontend → investigation |
| Security | Target scope, secrets, validation, service exposure |

Use mocks or isolated data where appropriate. Clearly document tests requiring FalkorDB, a provider, or DemoShop. Never scan external targets in automation unless explicitly authorized.

## 7. Coding-Agent Rules

Before each phase, read this plan and the relevant architecture/schema/API docs; inspect source; report discrepancies; propose the smallest coherent change; implement in reviewable steps; test and report exact results; then update documentation. Clearly list unfinished work, failures, and assumptions.

Writing code does not complete a phase. The phase completes only after its exit criteria are validated.

## 8. Project Completion

Core completion requires consistent graph findings/evidence, correct retest behavior, evidence-grounded agent output, documented FastAPI operations, React API-only presentation, passing end-to-end tests, clean-environment setup, and documented security boundaries.

This does not imply production readiness. Production requires separate review of authentication, authorization, monitoring, data protection, and infrastructure security.

## 9. Current Execution Status

This document is a roadmap, not evidence that tasks are complete. Mark each item done only after implementation and validation review. The first actionable task is **Phase 0 — Repository Audit and Baseline**.
