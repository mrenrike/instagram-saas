"""Item 18 — security response headers."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

# Endpoints that legitimately serve HTML we generate ourselves (e.g. FastAPI docs)
# still get the same headers; the CSP below is API-oriented and denies everything by
# default, so any project serving HTML from the API should pass a relaxed csp=.
DEFAULT_CSP = (
    "default-src 'none'; "
    "base-uri 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'none'"
)

DEFAULT_PERMISSIONS_POLICY = (
    "accelerometer=(), autoplay=(), camera=(), display-capture=(), "
    "encrypted-media=(), fullscreen=(), geolocation=(), gyroscope=(), "
    "magnetometer=(), microphone=(), midi=(), payment=(), "
    "picture-in-picture=(), usb=(), xr-spatial-tracking=()"
)


def build_csp(
    *,
    script_src: str = "'self'",
    style_src: str = "'self'",
    img_src: str = "'self' data:",
    connect_src: str = "'self'",
    font_src: str = "'self'",
    frame_ancestors: str = "'none'",
) -> str:
    """Build a Content-Security-Policy for a project that serves HTML.

    Every directive defaults to 'self'. Callers widen only what they actually need —
    never use 'unsafe-inline' for script-src; move inline handlers to a file instead.
    """
    return "; ".join(
        [
            "default-src 'none'",
            f"script-src {script_src}",
            f"style-src {style_src}",
            f"img-src {img_src}",
            f"connect-src {connect_src}",
            f"font-src {font_src}",
            "object-src 'none'",
            "base-uri 'none'",
            "form-action 'self'",
            f"frame-ancestors {frame_ancestors}",
            "upgrade-insecure-requests",
        ]
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach the standard hardening headers to every response.

    HSTS is only emitted when the request arrived over HTTPS (directly or via a
    trusted proxy), because sending it over plain HTTP is meaningless and browsers
    ignore it — emitting it unconditionally just hides misconfiguration in dev.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        csp: str = DEFAULT_CSP,
        hsts_max_age: int = 63072000,  # 2 years
        hsts_preload: bool = False,
        permissions_policy: str = DEFAULT_PERMISSIONS_POLICY,
        trust_proxy: bool = True,
    ) -> None:
        super().__init__(app)
        self.csp = csp
        self.hsts_max_age = hsts_max_age
        self.hsts_preload = hsts_preload
        self.permissions_policy = permissions_policy
        self.trust_proxy = trust_proxy

    def _is_https(self, request: Request) -> bool:
        if request.url.scheme == "https":
            return True
        if self.trust_proxy:
            return request.headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https"
        return False

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        headers = response.headers

        headers.setdefault("Content-Security-Policy", self.csp)
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Permissions-Policy", self.permissions_policy)
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        # Responses carrying personal data must never be stored by shared caches.
        headers.setdefault("Cache-Control", "no-store")

        if self._is_https(request):
            hsts = f"max-age={self.hsts_max_age}; includeSubDomains"
            if self.hsts_preload:
                hsts += "; preload"
            headers.setdefault("Strict-Transport-Security", hsts)

        # Server fingerprinting (item 17 — return only what is needed).
        if "server" in headers:
            del headers["server"]

        return response
