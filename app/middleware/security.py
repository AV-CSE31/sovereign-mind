"""
Security middleware for Sovereign-Mind.

Provides:
- Rate limiting (slowapi)
- Security headers (CSP, HSTS, X-Frame-Options)
- API key authentication
"""

import secrets
import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

# =============================================================================
# Rate Limiting
# =============================================================================

limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded", "detail": str(exc.detail)},
    )


# =============================================================================
# Security Headers Middleware
# =============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        settings = get_settings()
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
            )

        return response


# =============================================================================
# API Key Authentication Middleware
# =============================================================================


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Optional API key authentication for production deployments."""

    EXEMPT_PATHS = {"/", "/docs", "/redoc", "/openapi.json", "/v1/system/health"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()

        # Skip auth if no API key is configured or in debug mode
        if not settings.api_key or settings.debug:
            return await call_next(request)

        # Skip exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Check API key
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if not api_key or not secrets.compare_digest(api_key, settings.api_key):
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "detail": "Invalid or missing API key"},
            )

        return await call_next(request)


# =============================================================================
# Request Timing Middleware
# =============================================================================


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Add request timing header for observability."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start_time) * 1000
        response.headers["X-Request-Duration-Ms"] = f"{duration_ms:.2f}"
        return response


# =============================================================================
# Setup function
# =============================================================================


def setup_middleware(app: FastAPI) -> None:
    """Configure all security middleware on the FastAPI app."""
    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # API key auth
    app.add_middleware(APIKeyMiddleware)

    # Request timing
    app.add_middleware(RequestTimingMiddleware)
