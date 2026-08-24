"""Application settings.

Item 1 — every secret is read from the environment. Nothing here has a real value as
a default: a missing secret raises at import time with the variable's name, instead of
falling back to a placeholder that would silently ship to production.
"""
import base64
import os
from functools import lru_cache


class ConfigError(RuntimeError):
    """Raised when the environment is missing or misconfigured."""


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"Variável de ambiente obrigatória ausente: {name}. "
            f"Veja backend/.env.example para a lista completa."
        )
    return value


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} deve ser um inteiro, recebido: {raw!r}") from exc


def _csv(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    items = tuple(part.strip() for part in raw.split(",") if part.strip())
    return items or default


def _encryption_key(name: str) -> bytes:
    raw = _required(name)
    try:
        key = base64.b64decode(raw, validate=True)
    except Exception as exc:  # noqa: BLE001 — any decode failure is the same user error
        raise ConfigError(f"{name} deve ser base64 de 32 bytes (gere com `openssl rand -base64 32`)") from exc
    if len(key) != 32:
        raise ConfigError(f"{name} deve ter 32 bytes após o decode base64, tem {len(key)}")
    return key


class Config:
    def __init__(self) -> None:
        # --- Environment -------------------------------------------------------
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production").strip().lower()
        self.IS_PRODUCTION: bool = self.ENVIRONMENT == "production"

        # --- Session -----------------------------------------------------------
        self.SESSION_ENCRYPTION_KEY: bytes = _encryption_key("SESSION_ENCRYPTION_KEY")
        self.SESSIONS_DIR: str = os.getenv("SESSIONS_DIR", "./sessions")
        # Item 7 — access tokens are signed with a key derived from (not equal to) the
        # encryption key, so a signing-oracle bug can never leak the encryption key.
        self.SESSION_TOKEN_KEY: bytes = _derive_key(self.SESSION_ENCRYPTION_KEY, b"session-access-token")
        self.SESSION_TTL_HOURS: int = _int("SESSION_TTL_HOURS", 24)

        # --- Transport (items 18, 19) ------------------------------------------
        # Railway/Nginx terminate TLS and forward X-Forwarded-Proto; trusting that
        # header is only safe because nothing but the platform proxy can reach the app.
        self.TRUST_PROXY: bool = _bool("TRUST_PROXY", True)
        self.FORCE_HTTPS: bool = _bool("FORCE_HTTPS", self.IS_PRODUCTION)
        self.HSTS_MAX_AGE: int = _int("HSTS_MAX_AGE", 63_072_000)

        # CORS: an explicit allowlist. "*" is rejected in production because it lets
        # any site on the internet call this API with the visitor's browser.
        self.ALLOWED_ORIGINS: tuple[str, ...] = _csv(
            "ALLOWED_ORIGINS", () if self.IS_PRODUCTION else ("http://localhost:8080",)
        )
        if self.IS_PRODUCTION:
            if not self.ALLOWED_ORIGINS:
                raise ConfigError(
                    "ALLOWED_ORIGINS é obrigatório em produção. "
                    "Ex.: ALLOWED_ORIGINS=https://seudominio.com.br,https://www.seudominio.com.br"
                )
            if "*" in self.ALLOWED_ORIGINS:
                raise ConfigError("ALLOWED_ORIGINS não pode ser '*' em produção.")

        self.MAX_BODY_BYTES: int = _int("MAX_BODY_BYTES", 256 * 1024)

        # --- Rate limiting (item 11) -------------------------------------------
        self.RATE_LIMIT_ENABLED: bool = _bool("RATE_LIMIT_ENABLED", True)

        # --- Bot protection (item 12) ------------------------------------------
        # Optional: when unset the captcha step is skipped and only the rate limiter and
        # honeypot apply. Configure it before any paid traffic reaches the funnel.
        self.TURNSTILE_SECRET: str = os.getenv("TURNSTILE_SECRET", "").strip()
        self.CAPTCHA_PROVIDER: str = os.getenv("CAPTCHA_PROVIDER", "turnstile").strip()

        # --- Pricing -----------------------------------------------------------
        self.REPORT_PRICE_BRL: int = _int("REPORT_PRICE_BRL", 6700)

        # --- OpenPix -----------------------------------------------------------
        self.OPENPIX_APP_ID: str = _required("OPENPIX_APP_ID")
        self.OPENPIX_WEBHOOK_SECRET: str = _required("OPENPIX_WEBHOOK_SECRET")

        # --- Meta OAuth --------------------------------------------------------
        self.META_APP_ID: str = _required("META_APP_ID")
        self.META_APP_SECRET: str = _required("META_APP_SECRET")
        self.META_REDIRECT_URI: str = _required("META_REDIRECT_URI")

        # --- Anthropic ---------------------------------------------------------
        self.ANTHROPIC_API_KEY: str = _required("ANTHROPIC_API_KEY")

        # --- Resend ------------------------------------------------------------
        self.RESEND_API_KEY: str = _required("RESEND_API_KEY")
        self.FROM_EMAIL: str = os.getenv("FROM_EMAIL", "relatorios@example.com.br")

        # --- Admin (items 6, 10) -----------------------------------------------
        self.ADMIN_EMAIL: str = _required("ADMIN_EMAIL")
        # Prefer ADMIN_SECRET_HASH (pbkdf2, produced by `python -m backend.tools.hash_secret`).
        # ADMIN_SECRET stays supported for existing deployments and is compared in
        # constant time either way.
        self.ADMIN_SECRET_HASH: str = os.getenv("ADMIN_SECRET_HASH", "").strip()
        self.ADMIN_SECRET: str = os.getenv("ADMIN_SECRET", "").strip()
        if not (self.ADMIN_SECRET_HASH or self.ADMIN_SECRET):
            raise ConfigError("Defina ADMIN_SECRET_HASH (recomendado) ou ADMIN_SECRET.")
        if self.ADMIN_SECRET and len(self.ADMIN_SECRET) < 32:
            raise ConfigError("ADMIN_SECRET deve ter ao menos 32 caracteres aleatórios.")

        # --- Frontend ----------------------------------------------------------
        # Redirect targets are built from this, never from a client-supplied URL, so
        # the OAuth callback cannot be turned into an open redirect.
        self.FRONTEND_BASE_URL: str = os.getenv("FRONTEND_BASE_URL", "").strip().rstrip("/")

        # --- Google Sheets -----------------------------------------------------
        self.GOOGLE_SHEETS_ID: str = _required("GOOGLE_SHEETS_ID")
        self.GOOGLE_SERVICE_ACCOUNT_JSON: str = _required("GOOGLE_SERVICE_ACCOUNT_JSON")

        # --- Agency upsell -----------------------------------------------------
        self.AGENCY_NAME: str = os.getenv("AGENCY_NAME", "Nossa Agência")
        self.AGENCY_LINK: str = os.getenv("AGENCY_LINK", "https://agencia.com.br")
        self.AGENCY_HANDLE: str = os.getenv("AGENCY_HANDLE", "@agencia")
        self.AGENCY_EMAIL: str = os.getenv("AGENCY_EMAIL", "contato@agencia.com.br")


def _derive_key(master: bytes, info: bytes) -> bytes:
    """HKDF-Expand (RFC 5869) — one master secret, distinct keys per purpose."""
    import hashlib
    import hmac

    okm, previous, counter = b"", b"", 1
    while len(okm) < 32:
        previous = hmac.new(master, previous + info + bytes([counter]), hashlib.sha256).digest()
        okm += previous
        counter += 1
    return okm[:32]


@lru_cache
def get_config() -> Config:
    return Config()
