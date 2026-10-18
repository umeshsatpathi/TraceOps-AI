"""TraceShield AI — FastAPI Application Entry Point.

Exposes REST contracts defined in docs/API_SPEC.md for:
- Health checks
- Registered projects
- Authorized scan jobs and status
- Findings list and detail with graph relationships
- Bounded Cytoscape graph exploration and node neighborhoods
- Grounded AI-assisted investigations with explicit uncertainty
- Authorized BOLA verification workflow
"""
from __future__ import annotations

import logging
import os
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routes import (
    findings,
    graph,
    health,
    investigations,
    projects,
    scans,
    verification,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("traceshield.api")

app = FastAPI(
    title="TraceShield AI Security Investigation API",
    description="REST API for knowledge graph security findings, scanners, and AI investigations.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS Configuration (Supports local dev + Vercel/Netlify cloud deployments)
# ---------------------------------------------------------------------------
_cors_origins_env = os.getenv("CORS_ORIGINS", "")
_allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if _cors_origins_env:
    for _o in _cors_origins_env.split(","):
        _cleaned = _o.strip()
        if _cleaned and _cleaned not in _allowed_origins:
            _allowed_origins.append(_cleaned)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=os.getenv(
        "CORS_ORIGIN_REGEX",
        r"https://.*(\.vercel\.app|\.netlify\.app)"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.on_event("startup")
def startup_seed() -> None:
    """Attempt idempotent graph seed on startup if database is reachable."""
    try:
        from seed_graph import seed
        seed()
        logger.info("Graph topology verified and seeded on startup.")
    except Exception as exc:
        logger.info("Auto-seed skipped on startup (DB may not be populated yet): %s", exc)


# ---------------------------------------------------------------------------
# Standard Error Exception Handlers
# ---------------------------------------------------------------------------
def _extract_request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID") or f"req-{uuid4().hex[:8]}"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Format Pydantic schema validation failures into RFC-compliant error envelope."""
    req_id = _extract_request_id(request)
    # Sanitize error detail list
    sanitized_errors = []
    for err in exc.errors():
        sanitized_errors.append({
            "loc": [str(loc) for loc in err.get("loc", [])],
            "msg": err.get("msg", "Validation error"),
            "type": err.get("type", "value_error"),
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": sanitized_errors,
                "request_id": req_id,
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Map known HTTP exceptions into uniform error envelopes without stack traces."""
    req_id = _extract_request_id(request)

    code_map = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "RESOURCE_NOT_FOUND",
        status.HTTP_409_CONFLICT: "STATE_CONFLICT",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "VALIDATION_ERROR",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
        status.HTTP_503_SERVICE_UNAVAILABLE: "DEPENDENCY_UNAVAILABLE",
    }

    error_code = code_map.get(exc.status_code, "HTTP_ERROR")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": error_code,
                "message": str(exc.detail),
                "details": None,
                "request_id": req_id,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all error handler preventing secret disclosure or raw tracebacks."""
    req_id = _extract_request_id(request)
    logger.error("Unhandled API exception [req_id=%s]: %s", req_id, exc, exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
                "details": None,
                "request_id": req_id,
            }
        },
    )


# ---------------------------------------------------------------------------
# Route Registration (/api prefix)
# ---------------------------------------------------------------------------
app.include_router(health.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(scans.router, prefix="/api")
app.include_router(findings.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(investigations.router, prefix="/api")
app.include_router(verification.router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "TraceShield AI API",
        "version": "1.0.0",
        "docs": "/api/docs",
    }
