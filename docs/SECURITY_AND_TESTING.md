# TraceShield-AI — Security and Testing Guidelines

## 1. Purpose

This document defines the security requirements, testing strategy, and validation criteria for TraceShield-AI.

TraceShield-AI combines security scanners, graph-based analysis, and an AI investigation agent. Because it processes potentially untrusted security data and may execute scanning operations, the application must enforce clear boundaries between user input, scanner execution, graph persistence, AI-generated conclusions, and application responses.

These guidelines apply to the existing Python modules, FalkorDB integration, Streamlit dashboard, planned FastAPI backend, and planned React frontend.

## 2. Project Security Context

TraceShield-AI currently includes components for:

- Security-header analysis.
- Synthetic BOLA verification against the local DemoShop.
- Scanner-result normalization and graph ingestion.
- FalkorDB graph queries and persistence.
- AI-assisted security investigation.
- A Streamlit dashboard.

A FastAPI API layer and React frontend are planned components. Security requirements for these components must be implemented and verified when they are introduced.

The application must not be considered production-secure merely because individual scanners or graph queries work correctly.

## 3. Core Security Principles

### 3.1 Authorization Before Scanning

Only scan targets that the operator owns or has explicit authorization to assess.

- Default to local, explicitly configured test targets.
- Do not accept arbitrary targets without validation and authorization checks.
- Do not allow frontend input to bypass backend target restrictions.
- Do not follow redirects to an unapproved host without revalidating the destination.
- Do not permit scanners to access internal infrastructure, cloud metadata endpoints, or unrelated network services by default.
- Do not perform destructive tests unless a separately authorized, isolated test procedure explicitly permits them.

### 3.2 Least Privilege

Every component must have only the permissions required for its task.

- Restrict database exposure to the required application services.
- Avoid running application processes with unnecessary administrative privileges.
- Limit filesystem access and subprocess execution.
- Keep scanning capabilities separate from ordinary read-only graph queries where practical.
- Do not grant the AI agent unrestricted shell, filesystem, database administration, or network access.

### 3.3 Evidence-Based Conclusions

Security conclusions must be supported by collected evidence.

- Distinguish confirmed findings from hypotheses and inferred relationships.
- Preserve the source and timestamp of evidence.
- Do not mark a finding as resolved based only on an AI-generated explanation.
- Do not claim a scan succeeded when it failed or did not complete.
- Do not treat missing evidence as proof that a vulnerability does not exist.
- Present uncertainty and incomplete graph coverage explicitly.

### 3.4 Defense in Depth

Validate data at each boundary rather than relying on a single validation step.

The backend must independently validate requests, enforce authorization, constrain scanner operations, validate graph queries, and check outputs before returning them to clients.

Frontend validation is useful for usability but is not a security boundary.

## 4. Secrets and Configuration

### Requirements

- Store API keys, database credentials, and other secrets in environment variables or an approved secrets manager.
- Use `.env.example` for variable names and safe placeholders only.
- Never commit real `.env` files, tokens, passwords, or private keys.
- Never expose Gemini API keys or database credentials through React environment variables.
- Remember that Vite variables prefixed with `VITE_` are exposed to frontend code and must not contain secrets.
- Avoid printing credentials, authorization headers, or sensitive request payloads in logs.
- Validate required configuration at application startup and report missing variables without revealing secret values.
- Use separate credentials and configurations for development, testing, and deployment.

### Validation checklist

- [ ] `.gitignore` excludes local secret files.
- [ ] `.env.example` contains placeholders only.
- [ ] No secrets are embedded in source code or frontend bundles.
- [ ] Startup errors identify missing configuration without displaying secret values.
- [ ] Logs redact credentials and tokens.

If a secret is accidentally committed, revoke or rotate it. Removing the secret from the latest commit alone may not remove it from repository history.

## 5. Target and Network Security

### 5.1 Target Allowlisting

Scanning targets should be defined through an explicit project configuration or another trusted authorization mechanism.

The backend must validate:

- URL scheme.
- Hostname or IP address.
- Port.
- Redirect destination.
- Resolved IP addresses where relevant.
- Scanner-specific target restrictions.

A hostname allowlist alone may be insufficient if DNS resolution can direct a request to an internal or otherwise prohibited address. Where network access is involved, validate resolved addresses and enforce network-level restrictions as well.

### 5.2 Server-Side Request Forgery (SSRF)

If the application accepts URLs for scanning or fetching resources, treat them as untrusted input.

Block access to prohibited destinations, including:

- Loopback interfaces when they are not the explicitly authorized target.
- Private network ranges outside the approved test environment.
- Link-local addresses.
- Cloud metadata endpoints.
- Unapproved redirect destinations.

The local DemoShop may require loopback access during development. Allow that access only through an explicit, narrowly scoped development configuration rather than a global bypass.

### 5.3 Request Limits

Apply limits to scanner operations, including:

- Connection and read timeouts.
- Maximum redirect count.
- Maximum response size.
- Maximum scan duration.
- Maximum concurrent jobs.
- Request rate or concurrency limits where appropriate.

These controls reduce the risk of resource exhaustion and accidental disruption.

## 6. Scanner Safety

### Requirements

- Run tests against the local DemoShop or another explicitly authorized environment.
- Keep ordinary security-header checks non-destructive.
- Keep BOLA verification restricted to controlled test accounts and synthetic records.
- Avoid destructive actions against real users, records, or services.
- Validate scanner arguments before execution.
- Avoid constructing shell commands from user-controlled input.
- Prefer library APIs over shell commands.
- If subprocesses are necessary, use fixed executable paths or trusted commands, argument arrays, and explicit timeouts.
- Capture scanner failures as structured errors.
- Distinguish `completed_with_findings`, `completed_clean`, `failed`, and `cancelled` outcomes where supported.
- Ensure cancellation and timeout handling do not incorrectly report a clean scan.

A scan that finds no issues is not equivalent to a scan that failed to execute.

## 7. Graph Database Security and Integrity

### 7.1 Database Access

- Keep FalkorDB inaccessible to untrusted external clients.
- Bind development services to the required local interfaces.
- Do not expose database ports publicly unless a reviewed deployment architecture explicitly requires it.
- Use authentication and network controls appropriate to the deployed FalkorDB configuration.
- Separate database administration from ordinary application access where practical.
- Document graph persistence, backup, reset, and cleanup behavior.

### 7.2 Query Safety

- Use parameterized queries where supported.
- Validate labels, relationship types, identifiers, and other query components that cannot be safely parameterized.
- Never concatenate arbitrary user input into executable graph-query syntax.
- Limit graph traversal depth, returned nodes, returned edges, and query execution time where supported.
- Reject malformed identifiers and unsupported query parameters.
- Handle missing nodes and empty query results without crashing.

### 7.3 Graph Data Integrity

The application must maintain consistent identifiers and relationships across seeding, ingestion, scanning, and investigation.

- Use stable finding fingerprints.
- Associate findings with the scan runs that produced them.
- Preserve evidence provenance.
- Avoid unintended duplicate nodes and relationships.
- Ensure evidence is linked to the correct finding.
- Ensure endpoints and services refer to the correct project.
- Avoid updating unrelated findings during retesting.
- Prevent a partial or failed ingestion from silently appearing as a complete scan.

### 7.4 Data Migration

Before changing the graph schema:

1. Inspect existing labels, relationships, identifiers, and queries.
2. Determine which existing data and modules depend on them.
3. Design a migration or compatibility strategy.
4. Test the migration on disposable data or a backup.
5. Verify relationships and finding counts after migration.
6. Document rollback or recovery steps.

Do not delete or rebuild the existing graph automatically during normal application startup.

## 8. AI Agent and LLM Security

### 8.1 Treat Retrieved Data as Untrusted

Scanner output, evidence text, source-code snippets, endpoint responses, and graph properties may contain malicious or misleading instructions.

The AI agent must treat this material as data to analyze, not instructions to obey.

For example, a scanner result or source-code comment that says to ignore prior instructions or reveal credentials must not change the agent's operating rules.

### 8.2 Tool Permissions

- Expose only the tools required for the investigation task.
- Prefer read-only graph tools for ordinary investigations.
- Validate tool arguments before execution.
- Apply query and result-size limits.
- Require explicit authorization and appropriate safeguards for state-changing operations.
- Do not allow model-generated text to become an unrestricted shell command or arbitrary database query.
- Separate analysis from execution: an AI recommendation must not automatically trigger a high-impact action.

### 8.3 Grounded Investigation Results

Investigation responses should distinguish:

- **Observed evidence:** Directly recorded scanner results or graph facts.
- **Graph-derived inference:** A conclusion supported by connected entities and relationships.
- **Hypothesis:** A plausible explanation requiring additional verification.
- **Recommended action:** A proposed next step that has not necessarily been executed.

Where possible, return stable finding IDs and evidence references so the client can retrieve the underlying records.

If evidence is unavailable, contradictory, or insufficient, the agent must say so.

### 8.4 Model Failures

Handle:

- Provider timeouts.
- Rate limits.
- Invalid or incomplete model output.
- Tool invocation failures.
- Empty graph results.
- Context or token limits.
- Unavailable model credentials.

A model failure must not be silently converted into a successful investigation or a clean security assessment.

### 8.5 Investigation Testing

Evaluate the agent against scenarios that include:

- A finding supported by direct evidence.
- A multi-hop relationship across findings, endpoints, and evidence.
- Missing or disconnected graph relationships.
- Conflicting evidence.
- Prompt-injection text in retrieved content.
- An unavailable graph database.
- An unavailable model provider.

The agent must preserve the evidence boundary in each scenario.

## 9. API Security Requirements

These requirements apply when the planned FastAPI layer is implemented.

### 9.1 Request Validation

- Define explicit Pydantic request and response models.
- Validate IDs, URLs, enum values, pagination parameters, and payload sizes.
- Reject unsupported fields or values where appropriate.
- Do not trust project IDs or target URLs merely because they originate from the frontend.
- Return structured errors without exposing stack traces, secrets, or internal infrastructure details.

### 9.2 Authentication and Authorization

A local prototype may operate in a trusted development environment, but it must not be exposed to untrusted users without an appropriate access-control model.

Before remote deployment:

- Implement authentication.
- Authorize project and scan access on every relevant endpoint.
- Prevent users from accessing other users' projects or investigations.
- Restrict scan creation and verification to authorized operators.
- Protect state-changing operations against unauthorized requests.
- Review session and token handling.

CORS is not authentication and does not replace authorization.

### 9.3 Resource Management

- Add timeouts and request-size limits.
- Rate-limit expensive operations where appropriate.
- Use background jobs for long-running scans and investigations when needed.
- Return a job or scan identifier when work is asynchronous.
- Track job states and failures.
- Avoid allowing one client to exhaust all scanner, database, or model-provider capacity.

### 9.4 Error Handling

Use consistent HTTP status codes and a stable error response format.

Examples:

- `400 Bad Request`: Invalid request parameters.
- `401 Unauthorized`: Authentication is required or invalid.
- `403 Forbidden`: The caller is not permitted to perform the operation.
- `404 Not Found`: The requested resource does not exist or is not accessible.
- `409 Conflict`: A conflicting state prevents the operation.
- `422 Unprocessable Entity`: Request data fails semantic validation, where applicable.
- `429 Too Many Requests`: Rate or concurrency limit exceeded.
- `500 Internal Server Error`: Unexpected application failure.
- `502 Bad Gateway` or `503 Service Unavailable`: Relevant upstream dependency failure, where appropriate.

Do not return raw tracebacks or secret-bearing configuration in client-facing errors.

## 10. Frontend Security Requirements

These requirements apply when the planned React frontend is implemented.

- Communicate with the backend through the documented API.
- Never connect directly to FalkorDB.
- Never include server-side credentials in frontend code.
- Render untrusted scanner output and evidence as text rather than executable HTML.
- Avoid unsafe HTML rendering. If rich HTML is necessary, sanitize it with an established sanitizer.
- Validate navigation and external links derived from untrusted data.
- Keep loading, empty, error, and success states distinct.
- Do not treat hidden UI controls as authorization.
- Do not store sensitive credentials in browser storage without a reviewed security design.
- If cookie-based authentication is used, review `HttpOnly`, `Secure`, and `SameSite` settings and implement appropriate CSRF protection for state-changing requests.

The frontend must display evidence and uncertainty clearly instead of presenting every AI-generated statement as a verified fact.

## 11. Logging, Privacy, and Data Retention

- Record operational events needed for debugging and auditing.
- Include scan IDs, project IDs, timestamps, and status values where useful.
- Do not log passwords, API keys, session tokens, or complete authorization headers.
- Avoid collecting unnecessary personal or production data during testing.
- Limit retention of raw scanner output and sensitive evidence according to the project's intended use.
- Document whether data persists after container restarts.
- Ensure error logs distinguish scanner, graph, API, and model-provider failures.
- Prevent untrusted log content from being interpreted as executable commands or trusted instructions.

## 12. Testing Strategy

Testing must cover individual modules, integration boundaries, application workflows, and security controls.

### 12.1 Unit Tests

Test each component independently.

**Scanners**
- Valid response with a finding.
- Valid response with no findings.
- Timeout or connection failure.
- Malformed response.
- Unexpected redirect.
- Invalid target input.

**Normalizer**
- Valid scanner output.
- Missing optional and required fields.
- Invalid severity or status.
- Evidence normalization.
- Malformed scanner payload.
- Stable output for equivalent input.

**Graph writer**
- Node and relationship creation.
- Stable identifiers.
- Repeated ingestion.
- Duplicate finding prevention.
- Evidence association.
- Finding status updates after retesting.
- Failure handling.

**Graph tools**
- Correct query results.
- Empty graph.
- Missing node.
- Invalid arguments.
- Query limits.
- Database unavailable.

**Investigation agent**
- Correct tool registration.
- Successful tool invocation.
- Evidence-reference validation.
- Empty or contradictory evidence.
- Model timeout and invalid output.
- Prompt-injection resistance.

### 12.2 Integration Tests

Verify the boundaries between modules.

| Integration | Required validation |
|---|---|
| Scanner → normalizer | Scanner output becomes a valid normalized record |
| Normalizer → graph writer | Findings and evidence are persisted consistently |
| Seed data → graph queries | Seeded entities can be retrieved through expected queries |
| Graph tools → agent | Registered tools return usable, grounded results |
| FastAPI → graph services | API returns the documented data contract |
| FastAPI → scanner service | Supported scan requests produce trackable results |
| React → FastAPI | Frontend handles successful and failed requests |
| End-to-end | A finding can be scanned, stored, retrieved, visualized, and investigated |

Use an isolated test graph or disposable database where possible. Integration tests must not destroy developer data.

### 12.3 API Tests

When FastAPI is implemented, test:

- Valid requests and response schemas.
- Invalid request bodies and query parameters.
- Missing resources.
- Authorization failures.
- Upstream dependency failures.
- Pagination and filtering.
- Timeouts and asynchronous job status.
- Rate limits, where implemented.
- CORS configuration.
- Error responses without sensitive details.

### 12.4 Frontend Tests

When React is implemented, test:

- Initial loading states.
- Successful API responses.
- Empty projects and findings.
- Failed API requests.
- Invalid or partial data.
- Finding-detail navigation.
- Graph rendering and node selection.
- Investigation output and evidence references.
- Long text, large graphs, and responsive layouts.

### 12.5 End-to-End Tests

Use the local DemoShop as the primary controlled test environment.

The supported workflow should verify:

1. The application starts with the documented configuration.
2. The backend connects to FalkorDB.
3. The authorized local target is available.
4. A supported scanner executes.
5. Results are normalized and stored.
6. Findings and evidence can be retrieved from the graph.
7. The API returns the expected response.
8. The frontend displays the results.
9. The investigation agent can explain a finding using its evidence.
10. A retest updates the appropriate finding without resolving unrelated findings.

Repeat relevant scenarios against the secure DemoShop mode to verify that the scanner distinguishes expected behavior from the intentionally vulnerable configuration. A clean result applies only to the tested checks and scope; it does not establish that the entire application is secure.

## 13. Test Environment and Data Management

- Use a dedicated test configuration.
- Use synthetic accounts and records for BOLA verification.
- Avoid production credentials and real customer data.
- Make tests deterministic wherever practical.
- Mock external model calls for unit tests.
- Keep tests that require real API credentials or running services clearly marked.
- Provide setup and cleanup instructions for integration tests.
- Do not make ordinary tests depend on arbitrary public websites.
- Ensure cleanup targets only test-owned data.

Tests that intentionally verify failure conditions must not leave the environment in an unknown state.

## 14. CI and Quality Gates

As the test suite matures, automate the following checks:

- [ ] Python syntax and import validation.
- [ ] Automated unit tests.
- [ ] Linting and formatting checks, once configured.
- [ ] Dependency and secret checks.
- [ ] Frontend build and tests, once the frontend exists.
- [ ] API tests, once FastAPI exists.
- [ ] Selected integration tests using isolated services.
- [ ] Documentation updates for changed contracts.

A failed required check must be reported clearly. Do not skip tests silently or claim that an unexecuted check passed.

The CI workflow should avoid requiring production secrets. Tests that depend on external services should be isolated and explicitly configured.

## 15. Security Acceptance Checklist

Before a demonstration outside the developer's local machine or any broader deployment, review the following:

### Configuration and infrastructure
- [ ] Secrets are externalized and protected.
- [ ] FalkorDB is not unintentionally exposed.
- [ ] Services expose only the required ports.
- [ ] Dependencies and setup instructions are documented.

### Scanning and network access
- [ ] Scan targets are explicitly authorized.
- [ ] Redirects and resolved network addresses are validated.
- [ ] Timeouts and resource limits are configured.
- [ ] Destructive behavior is excluded unless explicitly authorized in an isolated environment.

### Graph and AI
- [ ] Findings and evidence have stable identities and provenance.
- [ ] Retests do not falsely resolve unrelated findings.
- [ ] Graph queries validate user-controlled input.
- [ ] The agent treats retrieved content as untrusted data.
- [ ] Investigation claims can be traced to evidence.
- [ ] Model failures are not reported as successful scans.

### API and frontend
- [ ] Requests are validated server-side.
- [ ] Authentication and authorization are implemented before untrusted remote access.
- [ ] Errors do not expose secrets or tracebacks.
- [ ] Untrusted evidence is rendered safely.
- [ ] The frontend contains no server-side secrets.

### Testing and operations
- [ ] Required automated tests pass.
- [ ] The supported end-to-end workflow is verified.
- [ ] Failure scenarios are tested.
- [ ] Persistence, cleanup, and recovery behavior are documented.
- [ ] Known limitations are disclosed.

## 16. Implementation Priority

Apply these guidelines in the following order:

**P0 — Immediate**
- Restrict scanner targets.
- Protect secrets and database access.
- Validate scanner results and graph-query inputs.
- Establish tests for graph identity, evidence provenance, and finding lifecycle.
- Verify agent-tool registration and evidence grounding.

**P1 — API development**
- Implement request validation, structured errors, and resource limits.
- Establish authentication and authorization requirements before remote exposure.
- Add API tests and dependency-failure handling.

**P2 — Frontend development**
- Use only the backend API.
- Render untrusted content safely.
- Present evidence and uncertainty accurately.
- Test loading, empty, success, and failure states.

**P3 — Release hardening**
- Automate quality checks.
- Review dependency vulnerabilities and secret exposure.
- Verify clean setup, recovery, and deployment configuration.
- Conduct a final security review against the intended deployment environment.

## 17. Definition of Done

A security-sensitive feature is complete only when:

1. Its inputs and trust boundaries are documented.
2. Authorization and validation requirements are enforced.
3. Errors and failure states are handled explicitly.
4. Relevant automated tests have been added.
5. The required tests have been executed and their results recorded.
6. Data integrity and evidence provenance are preserved.
7. Documentation reflects the actual implementation.
8. Known limitations and remaining risks are disclosed.

Passing automated tests is necessary but not sufficient to prove security. The final security assessment must consider the application's configuration, deployment environment, permissions, and operational behavior.
