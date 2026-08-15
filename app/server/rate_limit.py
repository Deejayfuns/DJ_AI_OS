"""
DJ AI OS — Rate Limiting Middleware

In-memory fixed-window rate limiter keyed by client IP + endpoint path.
No external dependencies.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting per endpoint pattern."""
    rpm: int  # requests per minute
    window_seconds: int = 60


# Default rate limit configuration
# Can be overridden via environment variables:
# RATE_LIMIT_ACTIVATE_RPM=30
# RATE_LIMIT_ENTITLEMENTS_RPM=30
# RATE_LIMIT_CHECKOUT_RPM=10
# RATE_LIMIT_CUSTOMER_PORTAL_RPM=10
DEFAULT_LIMITS: Dict[str, RateLimitConfig] = {
    "/api/activate": RateLimitConfig(rpm=30),
    "/api/entitlements": RateLimitConfig(rpm=30),
    "/api/checkout": RateLimitConfig(rpm=10),
    "/api/customer-portal": RateLimitConfig(rpm=10),
}

# Endpoints excluded from rate limiting
EXCLUDED_PATHS = {
    "/health",
    "/api/webhooks/stripe",
}


class FixedWindowRateLimiter:
    """
    In-memory fixed-window rate limiter.

    Key: (client_ip, endpoint_path)
    Window: 60 seconds (configurable per endpoint)
    """

    def __init__(self, limits: Optional[Dict[str, RateLimitConfig]] = None):
        self.limits = limits or DEFAULT_LIMITS
        # (client_ip, path) -> (window_start_ts, count)
        self._windows: Dict[tuple, tuple] = {}

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request.

        Uses request.client.host directly. Does NOT trust X-Forwarded-For
        unless a trusted proxy configuration is explicitly added in the future.
        """
        if request.client:
            return request.client.host
        return "unknown"

    def _get_limit(self, path: str) -> Optional[RateLimitConfig]:
        """Find matching rate limit config for path."""
        # Exact match first
        if path in self.limits:
            return self.limits[path]
        # Prefix match for potential future nested routes
        for pattern, config in self.limits.items():
            if path.startswith(pattern):
                return config
        return None

    def is_excluded(self, path: str) -> bool:
        """Check if path is excluded from rate limiting."""
        if path in EXCLUDED_PATHS:
            return True
        # Exclude static/admin routes if they exist
        if path.startswith("/static") or path.startswith("/admin"):
            return True
        return False

    def check_limit(self, request: Request) -> tuple[bool, Optional[int], Optional[int]]:
        """
        Check if request is within rate limit.

        Returns: (allowed, retry_after_seconds, limit)
        """
        path = request.url.path

        if self.is_excluded(path):
            return True, None, None

        config = self._get_limit(path)
        if not config:
            return True, None, None

        client_ip = self._get_client_ip(request)
        key = (client_ip, path)
        now = time.time()
        window_start = int(now // config.window_seconds) * config.window_seconds

        stored = self._windows.get(key)
        if stored:
            stored_window_start, count = stored
            if stored_window_start == window_start:
                # Same window
                if count >= config.rpm:
                    retry_after = int(window_start + config.window_seconds - now) + 1
                    return False, retry_after, config.rpm
                self._windows[key] = (window_start, count + 1)
                return True, None, config.rpm
            else:
                # New window
                self._windows[key] = (window_start, 1)
                return True, None, config.rpm
        else:
            # First request in this window
            self._windows[key] = (window_start, 1)
            return True, None, config.rpm

    def cleanup_expired(self, max_age_seconds: int = 300) -> int:
        """Remove expired window entries. Returns count of removed entries."""
        now = time.time()
        expired_keys = [
            key for key, (window_start, _) in self._windows.items()
            if now - window_start > max_age_seconds
        ]
        for key in expired_keys:
            del self._windows[key]
        return len(expired_keys)


# Global limiter instance (single-process)
_rate_limiter: Optional[FixedWindowRateLimiter] = None


def get_rate_limiter() -> FixedWindowRateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = FixedWindowRateLimiter()
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, limiter: Optional[FixedWindowRateLimiter] = None):
        super().__init__(app)
        self.limiter = limiter or get_rate_limiter()

    async def dispatch(self, request: Request, call_next):
        allowed, retry_after, limit = self.limiter.check_limit(request)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "retry_after": retry_after},
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)

        # Add rate limit headers to successful responses
        if limit is not None:
            response.headers["X-RateLimit-Limit"] = str(limit)

        return response


def create_rate_limit_middleware(limiter: Optional[FixedWindowRateLimiter] = None):
    """Factory to create RateLimitMiddleware for app.middleware('http')."""
    return RateLimitMiddleware