import json
import threading
from pathlib import Path

COUPONS_FILE = "./coupons.json"
_lock = threading.Lock()


class CouponNotFound(Exception):
    pass


class CouponExhausted(Exception):
    pass


def _load() -> dict:
    p = Path(COUPONS_FILE)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def _save(data: dict) -> None:
    Path(COUPONS_FILE).write_text(json.dumps(data, indent=2))


def apply_coupon(code: str, price_cents: int) -> int:
    """Validate coupon, decrement uses_left, return discount in centavos."""
    with _lock:
        data = _load()
        if code not in data:
            raise CouponNotFound(code)
        coupon = data[code]
        if coupon["uses_left"] == 0:
            raise CouponExhausted(code)

        # Calculate discount
        if coupon["type"] == "percent":
            discount = int(price_cents * coupon["value"] / 100)
        else:  # fixed
            discount = min(coupon["value"], price_cents)

        # Decrement uses_left (skip if unlimited)
        if coupon["uses_left"] > 0:
            data[code]["uses_left"] -= 1
            _save(data)

        return discount
