"""Coupon store.

Item 8  — the discount is computed here from the server-side coupon table; the client
          only ever sends a code.
Item 14 — the code's shape is validated before it is used as a dictionary key.
"""
import json
import logging
import os
import re
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

COUPONS_FILE = os.getenv("COUPONS_FILE", "./coupons.json")
_CODE_RE = re.compile(r"^[A-Z0-9_-]{3,32}$")
_lock = threading.Lock()


class CouponNotFound(Exception):
    pass


class CouponExhausted(Exception):
    pass


class InvalidCouponCode(Exception):
    pass


def _validate_code(code: str) -> str:
    normalized = (code or "").strip().upper()
    if not _CODE_RE.match(normalized):
        raise InvalidCouponCode(code)
    return normalized


def _load() -> dict:
    path = Path(COUPONS_FILE)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Could not read coupon file: %s", exc)
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: dict) -> None:
    path = Path(COUPONS_FILE)
    tmp = path.with_suffix(".tmp")
    # 0600: the coupon table is a business secret and lives next to the app.
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(data, handle, indent=2)
    os.replace(tmp, path)


def apply_coupon(code: str, price_cents: int) -> int:
    """Validate a coupon, consume one use and return the discount in centavos.

    The discount is clamped to the price so a malformed entry (a 150% coupon, a fixed
    value larger than the order) can never produce a negative total.
    """
    normalized = _validate_code(code)

    with _lock:
        data = _load()
        coupon = data.get(normalized)
        if coupon is None:
            raise CouponNotFound(normalized)

        uses_left = coupon.get("uses_left", 0)
        if uses_left == 0:
            raise CouponExhausted(normalized)

        if coupon.get("type") == "percent":
            percent = max(0, min(100, int(coupon.get("value", 0))))
            discount = price_cents * percent // 100
        else:
            discount = max(0, int(coupon.get("value", 0)))

        discount = min(discount, price_cents)

        if uses_left > 0:
            data[normalized]["uses_left"] = uses_left - 1
            _save(data)

        return discount
