"""TraceShield AI — FastAPI Dependencies & Context.

Provides reusable dependencies for request tracing and graph access.
"""
from __future__ import annotations

from uuid import uuid4
from fastapi import Request


def get_request_id(request: Request) -> str:
    """Retrieve or generate a correlation request ID."""
    req_id = request.headers.get("X-Request-ID")
    if not req_id:
        req_id = f"req-{uuid4().hex[:8]}"
    return req_id
