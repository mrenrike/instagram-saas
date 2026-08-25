import json
from pathlib import Path
from unittest.mock import patch

import pytest


def make_coupons_file(tmp_path, data):
    f = tmp_path / "coupons.json"
    f.write_text(json.dumps(data))
    return str(f)


def test_valid_percent_coupon(tmp_path):
    path = make_coupons_file(tmp_path, {"TESTER10": {"type": "percent", "value": 100, "uses_left": 5}})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import apply_coupon
        discount = apply_coupon("TESTER10", 6700)
        assert discount == 6700  # 100% off


def test_valid_fixed_coupon(tmp_path):
    path = make_coupons_file(tmp_path, {"DISC10": {"type": "fixed", "value": 1000, "uses_left": -1}})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import apply_coupon
        discount = apply_coupon("DISC10", 6700)
        assert discount == 1000


def test_exhausted_coupon_raises(tmp_path):
    path = make_coupons_file(tmp_path, {"USED": {"type": "percent", "value": 50, "uses_left": 0}})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import CouponExhausted, apply_coupon
        with pytest.raises(CouponExhausted):
            apply_coupon("USED", 6700)


def test_invalid_coupon_raises(tmp_path):
    path = make_coupons_file(tmp_path, {})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import CouponNotFound, apply_coupon
        with pytest.raises(CouponNotFound):
            apply_coupon("NOPE", 6700)


def test_uses_left_decrements(tmp_path):
    path = make_coupons_file(tmp_path, {"CUP": {"type": "percent", "value": 10, "uses_left": 3}})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import apply_coupon
        apply_coupon("CUP", 6700)
        data = json.loads(Path(path).read_text())
        assert data["CUP"]["uses_left"] == 2


def test_unlimited_coupon_not_decremented(tmp_path):
    path = make_coupons_file(tmp_path, {"INF": {"type": "percent", "value": 10, "uses_left": -1}})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import apply_coupon
        apply_coupon("INF", 6700)
        data = json.loads(Path(path).read_text())
        assert data["INF"]["uses_left"] == -1


# --- Item 14: the code's shape is validated before it is used as a key --------
@pytest.mark.parametrize(
    "bad_code",
    ["", "C", "../../etc/passwd", "CODE WITH SPACES", "X" * 40, "<script>"],
)
def test_malformed_coupon_code_is_rejected(tmp_path, bad_code):
    path = make_coupons_file(tmp_path, {})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import InvalidCouponCode, apply_coupon

        with pytest.raises(InvalidCouponCode):
            apply_coupon(bad_code, 6700)


def test_coupon_is_case_insensitive(tmp_path):
    path = make_coupons_file(tmp_path, {"TESTER10": {"type": "percent", "value": 50, "uses_left": 1}})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import apply_coupon

        assert apply_coupon("tester10", 6700) == 3350


# --- Item 8: a malformed coupon can never produce a negative total ------------
def test_discount_is_clamped_to_the_price(tmp_path):
    path = make_coupons_file(tmp_path, {"HUGE": {"type": "fixed", "value": 999_999, "uses_left": 1}})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import apply_coupon

        assert apply_coupon("HUGE", 6700) == 6700


def test_percent_above_100_is_clamped(tmp_path):
    path = make_coupons_file(tmp_path, {"OVER": {"type": "percent", "value": 500, "uses_left": 1}})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import apply_coupon

        assert apply_coupon("OVER", 6700) == 6700


def test_negative_fixed_value_yields_no_discount(tmp_path):
    path = make_coupons_file(tmp_path, {"NEG": {"type": "fixed", "value": -500, "uses_left": 1}})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import apply_coupon

        assert apply_coupon("NEG", 6700) == 0
