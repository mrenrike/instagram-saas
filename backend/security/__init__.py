"""
Portable security baseline for FastAPI/Starlette projects.

This package is intentionally dependency-free (stdlib + starlette only) so it can be
copied verbatim into any project. It implements the shared, framework-level half of
the 20-point security checklist documented in SECURITY.md:

  6.  Server-side authentication helpers  -> constant_time_compare, verify_secret
  7.  Record access restriction           -> safe_identifier, sign/verify resource tokens
  9.  Session cookie protection           -> set_session_cookie
 11.  Login attempt limiting              -> RateLimiter, rate_limit dependency
 12.  Bot protection                      -> Turnstile/hCaptcha verification + honeypot
 14.  Input validation                    -> StrictModel, bounded string types
 15.  User content escaping               -> escape_html, escape_attr
 16.  Upload restriction                  -> BodySizeLimitMiddleware, validate_upload
 17.  Minimal API responses               -> public_error
 18.  Security headers                    -> SecurityHeadersMiddleware
 19.  HTTPS enforcement                   -> HTTPSRedirectMiddleware, HSTS

Items 1-5, 10, 13, 20 are project-level concerns (secrets, git history, database
configuration, password storage, parameterized queries, dependency scanning) and are
covered by the settings loader, the CI workflows and the checklist.
"""

from .bots import CaptchaFailed, honeypot_tripped, verify_captcha
from .cookies import clear_session_cookie, set_session_cookie
from .headers import SecurityHeadersMiddleware, build_csp
from .https import HTTPSRedirectMiddleware
from .limits import BodySizeLimitMiddleware
from .outbound import UnsafeURL, safe_urlopen
from .ratelimit import RateLimiter, RateLimitExceeded, client_ip, rate_limit
from .responses import PUBLIC_ERROR_MESSAGES, public_error
from .secrets import constant_time_compare, generate_secret, hash_secret, verify_secret
from .tokens import InvalidResourceToken, sign_resource_token, verify_resource_token
from .validation import (
    InvalidIdentifier,
    LongText,
    MediumText,
    ShortText,
    Slug,
    StrictModel,
    UploadRejected,
    escape_attr,
    escape_html,
    safe_identifier,
    sanitize_for_spreadsheet,
    validate_upload,
)

__all__ = [
    "SecurityHeadersMiddleware",
    "build_csp",
    "HTTPSRedirectMiddleware",
    "BodySizeLimitMiddleware",
    "RateLimiter",
    "RateLimitExceeded",
    "safe_urlopen",
    "UnsafeURL",
    "rate_limit",
    "client_ip",
    "constant_time_compare",
    "verify_secret",
    "hash_secret",
    "generate_secret",
    "sign_resource_token",
    "verify_resource_token",
    "InvalidResourceToken",
    "StrictModel",
    "ShortText",
    "MediumText",
    "LongText",
    "Slug",
    "safe_identifier",
    "InvalidIdentifier",
    "escape_html",
    "escape_attr",
    "sanitize_for_spreadsheet",
    "validate_upload",
    "UploadRejected",
    "set_session_cookie",
    "clear_session_cookie",
    "verify_captcha",
    "honeypot_tripped",
    "CaptchaFailed",
    "public_error",
    "PUBLIC_ERROR_MESSAGES",
]
