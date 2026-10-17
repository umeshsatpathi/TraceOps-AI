# AGENTS.md — TraceShield AI

## 1. Project Overview

TraceShield AI is an AI-assisted security-incident investigation and root-cause analysis system. It combines a React/Vite frontend, a FastAPI backend, a FalkorDB security graph, LangGraph orchestration, and evidence collected from explicitly authorized local or deterministic demo sources.

The system must:
- Investigate incidents using recorded evidence.
- Identify affected services and their dependencies.
- Generate and compare likely root-cause hypotheses.
- Explain findings with supporting and contradictory evidence.
- Recommend corrective actions.
- Require human approval before any simulated remediation.
- Verify the simulated outcome and record the result.

The primary goal is a functional, explainable hackathon prototype. It is not an unrestricted production auto-remediation or security-testing platform.

OWASP Juice Shop and a command-line interface are not part of this project architecture. Do not add a Juice Shop dependency, OWASP-specific workflows, or CLI commands unless the project specification is explicitly changed.

## 2. Required Repository Structure

Use this layout for new work. Do not place frontend code in the Python API or expose the graph directly to the browser.

```text
TraceShield-AI/
├── frontend/                     # React + Vite frontend
│   └── src/
│       ├── services/
│       │   └── api.js            # All browser-to-API calls
│       ├── pages/
│       ├── components/
│       └── features/
├── api/                          # FastAPI layer
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── routes/
│   │   ├── projects.py
│   │   ├── findings.py
│   │   ├── graph.py
│   │   ├── investigations.py
│   │   ├── scans.py
│   │   └── verification.py
│   └── schemas.py                # Pydantic request/response models
├── agent.py
├── graph_db.py
├── graph_tools.py
├── graph_intelligence.py
├── scanners/
├── ingestion/
└── requirements.txt
```

## 3. Technology Stack

Use the following stack unless an approved project specification explicitly changes it.

- **Frontend:** React, Vite, and JavaScript.
- **API:** Python, FastAPI, Pydantic, and Pytest.
- **Graph database:** FalkorDB and Cypher.
- **Agent orchestration:** LangGraph.
- **LLM:** A model supporting tool calling and structured outputs.
- **Tool integration:** Python functions initially; MCP where useful.
- **Local development:** Docker and Docker Compose where useful.

## 4. Component Boundaries

### Frontend

- Pages, components, and features render data and collect user input.
- `frontend/src/services/api.js` is the single boundary for frontend API calls.
- The frontend must not connect to FalkorDB, invoke Python scripts, manage approval state authoritatively, or embed API secrets.

### FastAPI layer

- `api/main.py` creates the app and registers route modules.
- `api/schemas.py` owns typed Pydantic request and response models.
- Route modules validate input, call application/graph services, map known failures to defined HTTP responses, and never contain Cypher business logic inline.
- `projects.py` manages project and authorized-scope context.
- `findings.py` exposes finding retrieval and lifecycle views.
- `graph.py` exposes read-only graph context and impact views.
- `investigations.py` creates, runs, and retrieves explainable investigations.
- `scans.py` starts or retrieves only permitted, explicitly scoped scan/observation jobs.
- `verification.py` records approval decisions, simulated-action verification, and outcomes.

### Core Python services

- `graph_db.py` owns FalkorDB connection setup.
- `graph_tools.py` and `graph_intelligence.py` provide validated graph operations and investigation logic.
- `agent.py` orchestrates approved tools and cannot bypass API/service validation, approval checks, target-scope controls, or access controls.
- `scanners/` and `ingestion/` collect and normalize permitted evidence; they do not make policy decisions or directly control remediation.

## 5. System Architecture Principles

Keep responsibilities separated.

- React communicates only with FastAPI through `services/api.js`.
- FastAPI validates requests, coordinates workflows, enforces authorization and approval, and returns defined schemas.
- FalkorDB stores service relationships and relevant investigation evidence.
- LangGraph orchestrates investigation steps and workflow state.
- Agent tools retrieve evidence or request permitted actions through defined service interfaces.
- External telemetry systems may retain raw logs and metrics; the graph can store relevant evidence and references.

Do not place business logic, direct database operations, target interaction logic, or authorization decisions in React components. Do not allow the LLM to bypass server-side validation or approval enforcement.

Only collect observations from local or otherwise explicitly authorized targets. Do not scan, probe, exploit, or remediate public or third-party systems.

## 6. Incident Investigation Workflow

Implement the following logical workflow:

1. Receive and validate an investigation request, project context, and authorized target configuration.
2. Create or retrieve the incident/investigation record.
3. Collect relevant logs, metrics, deployment history, service relationships, and permitted observations.
4. Query FalkorDB for dependencies and potentially affected services.
5. Construct a timeline from timestamped evidence.
6. Generate and compare plausible root-cause hypotheses.
7. Evaluate supporting evidence, contradictory evidence, and alternative explanations.
8. Produce an explainable investigation report.
9. Recommend a corrective action when justified.
10. Record an explicit human approval or rejection decision.
11. Execute only a simulated remediation after approval.
12. Verify the simulated outcome using available health signals.
13. Record the action, outcome, evidence, target scope, and final incident status.

Represent failures and incomplete investigations explicitly. Never mark a workflow successful solely because an LLM returned a success message.

## 7. Agent Tooling

Potential investigation tools include:

- `get_service_dependencies(service_name)`
- `get_recent_deployments(service_name, time_window)`
- `get_error_timeline(service_name, start_time, end_time)`
- `find_affected_services(service_name)`
- `get_deployment_changes(deployment_id)`
- `simulate_rollback(deployment_id, target_version)`
- `verify_service_health(service_name, time_window)`
- `get_target_status(target_id)`
- `collect_authorized_target_observations(target_id, scope)`

These are proposed interfaces, not proof that implementations or external integrations already exist. Implement and test them incrementally, starting with deterministic seed data. Tool inputs must be validated, outputs must use defined structures, and failures must be handled explicitly.

## 8. Evidence, Approval, and Remediation Safety

- Treat root-cause findings as hypotheses supported by evidence, not guaranteed facts.
- Distinguish observed facts, inferred relationships, and recommended actions.
- Include timestamps, affected components, and evidence references whenever available.
- Do not treat temporal correlation alone as proof of causation.
- Explain uncertainty and identify missing evidence.
- Never invent logs, metrics, deployments, graph relationships, or tool results.
- Require explicit human approval for every simulated remediation.
- Enforce approval server-side, not in React state.
- Validate the investigation, deployment, target version, and action eligibility.
- Reject unapproved, invalid, or duplicate requests as appropriate.
- Record approval decisions, attempts, verification results, and failures.
- Do not connect the prototype to real production rollback operations or uncontrolled targets.

The AI agent may recommend remediation but must never approve its own recommendation.

## 9. Shared Contracts

Before changing shared interfaces, read the relevant files in `docs/`:

- `docs/ARCHITECTURE.md` — component boundaries and system data flow.
- `docs/API_SPEC.md` — proposed endpoints and API contract rules.
- `docs/GRAPH_SCHEMA.md` — graph labels, relationships, and migration decisions.
- `docs/GRAPH_SCHEMA_PREREQUISITES.md` — mandatory repository review before graph-schema changes.
- `docs/IMPLEMENTATION_PLAN.md` — implementation order and definition of done.
- `docs/SECURITY_AND_TESTING.md` — security baseline and test strategy.

Maintain compatibility between frontend models, FastAPI schemas, application services, agent tools, and graph queries. `API_SPEC.md` and `GRAPH_SCHEMA.md` are drafts; do not treat an endpoint or graph migration as implemented merely because it is documented.
