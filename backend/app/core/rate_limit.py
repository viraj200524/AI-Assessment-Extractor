"""In-memory sliding-window rate limiting for parsing endpoints."""

import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request

from app.core.config import Settings, get_settings


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: float) -> float | None:
        """Record a request hit. Returns None if allowed, or remaining seconds to wait if limited."""
        if limit <= 0:
            return None

        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= limit:
                return max(1.0, window_seconds - (now - hits[0]))
            hits.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


parse_rate_limiter = SlidingWindowRateLimiter()


def client_identifier(request: Request) -> str:
    """Extract client IP address from proxy headers or connection info."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    client = request.client
    return client.host if client else "unknown"


def limit_parse_requests(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Throttle parse submissions per client IP. Disabled when the limit is 0."""
    limit = settings.parse_rate_limit_per_hour
    if limit <= 0:
        return

    retry_after = parse_rate_limiter.check(client_identifier(request), limit, window_seconds=3600.0)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit reached: at most {limit} assessment(s) per hour. "
                "Please try again later."
            ),
            headers={"Retry-After": str(int(retry_after))},
        )
