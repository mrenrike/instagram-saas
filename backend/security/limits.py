"""Item 16 — bound the size of anything a client can send."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

DEFAULT_MAX_BODY_BYTES = 256 * 1024  # 256 KiB — generous for a JSON API


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized request bodies before they are buffered into memory.

    Content-Length is checked first so the common case costs nothing. Chunked uploads
    send no Content-Length, so the body is also counted as it streams and the request
    is cut off the moment it crosses the limit.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
        overrides: dict[str, int] | None = None,
    ) -> None:
        super().__init__(app)
        self.max_body_bytes = max_body_bytes
        # Path prefix -> limit, for the few routes that accept real uploads.
        self.overrides = overrides or {}

    def _limit_for(self, path: str) -> int:
        for prefix, limit in self.overrides.items():
            if path.startswith(prefix):
                return limit
        return self.max_body_bytes

    async def dispatch(self, request: Request, call_next):
        limit = self._limit_for(request.url.path)

        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > limit:
                    return JSONResponse({"detail": "Request too large"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)

        # Guard chunked bodies, which arrive without a Content-Length.
        received = 0
        original_receive = request.receive

        async def counting_receive():
            nonlocal received
            message = await original_receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _BodyTooLarge()
            return message

        request._receive = counting_receive  # noqa: SLF001 — the documented ASGI hook

        try:
            return await call_next(request)
        except _BodyTooLarge:
            return JSONResponse({"detail": "Request too large"}, status_code=413)


class _BodyTooLarge(Exception):
    pass
