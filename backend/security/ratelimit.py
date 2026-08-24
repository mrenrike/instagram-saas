"""Item 11 — limit attempts (login, checkout, webhooks, polling)."""
from __future__ import annotations

import asyncio
import ipaddress
import time
from collections import deque
from collections.abc import Callable

from starlette.requests import Request

# Header set by Railway/Nginx/Cloudflare. Trusting it blindly lets any client forge its
# own IP and bypass every limit, so it is only read when the deployment actually sits
# behind a proxy that overwrites it.
_FORWARDED_HEADERS = ("x-forwarded-for", "x-real-ip")


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded, retry in {retry_after}s")


def client_ip(request: Request, *, trust_proxy: bool = True) -> str:
    """Best-effort client identity for rate limiting.

    With trust_proxy the *left-most* entry of X-Forwarded-For is the original client,
    but it is also fully client-controlled. We therefore take the right-most entry that
    is not a private address, falling back to the socket peer — that is the closest we
    can get to an identity the client cannot pick for itself behind one proxy hop.
    """
    if trust_proxy:
        for header in _FORWARDED_HEADERS:
            raw = request.headers.get(header)
            if not raw:
                continue
            candidates = [part.strip() for part in raw.split(",") if part.strip()]
            for candidate in reversed(candidates):
                try:
                    addr = ipaddress.ip_address(candidate)
                except ValueError:
                    continue
                if not (addr.is_private or addr.is_loopback):
                    return candidate
            if candidates:
                return candidates[-1]

    return request.client.host if request.client else "unknown"


class RateLimiter:
    """In-process sliding-window limiter.

    Deliberately simple: no Redis, no extra dependency, so it can be dropped into any
    project. The trade-off is that the window is per-process — with several workers the
    effective limit is ``max_requests * workers``. Set the limit accordingly, or swap
    the backing store for Redis once a project runs more than one instance.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        *,
        name: str = "default",
        trust_proxy: bool = True,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.name = name
        self.trust_proxy = trust_proxy
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()
        self._last_sweep = 0.0

    async def check(self, key: str) -> None:
        """Record one hit for ``key``; raise RateLimitExceeded when over the limit."""
        now = time.monotonic()
        async with self._lock:
            self._sweep(now)
            bucket = self._hits.setdefault(key, deque())
            cutoff = now - self.window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                retry_after = max(1, int(bucket[0] + self.window_seconds - now) + 1)
                raise RateLimitExceeded(retry_after)

            bucket.append(now)

    async def reset(self, key: str) -> None:
        """Clear a key's history — call this after a *successful* login."""
        async with self._lock:
            self._hits.pop(key, None)

    def _sweep(self, now: float) -> None:
        """Drop empty buckets periodically so the dict cannot grow without bound."""
        if now - self._last_sweep < self.window_seconds:
            return
        self._last_sweep = now
        cutoff = now - self.window_seconds
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]:
            del self._hits[key]


def rate_limit(
    limiter: RateLimiter,
    *,
    key_func: Callable[[Request], str] | None = None,
) -> Callable:
    """FastAPI dependency factory: ``Depends(rate_limit(my_limiter))``."""
    from fastapi import HTTPException

    async def dependency(request: Request) -> None:
        key = key_func(request) if key_func else client_ip(request, trust_proxy=limiter.trust_proxy)
        try:
            await limiter.check(f"{limiter.name}:{key}")
        except RateLimitExceeded as exc:
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas. Tente novamente em instantes.",
                headers={"Retry-After": str(exc.retry_after)},
            ) from exc

    return dependency
