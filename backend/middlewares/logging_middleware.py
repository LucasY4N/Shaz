"""
backend/middlewares/logging_middleware.py
Middleware de logging para todas as requisições HTTP.
"""
from __future__ import annotations

import time
from fastapi import Request
from fastapi.responses import Response
from logs.logger import get_module_logger

log = get_module_logger("backend.http")


async def logging_middleware(request: Request, call_next) -> Response:
    """Loga todas as requisições com método, path e duração."""
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 1)
    log.info(f"{request.method} {request.url.path} → {response.status_code} ({duration_ms}ms)")
    return response
