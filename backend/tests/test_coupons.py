import pytest
import json
from pathlib import Path
from unittest.mock import patch


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
        from backend.coupons import apply_coupon, CouponExhausted
        with pytest.raises(CouponExhausted):
            apply_coupon("USED", 6700)


def test_invalid_coupon_raises(tmp_path):
    path = make_coupons_file(tmp_path, {})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import apply_coupon, CouponNotFound
        with pytest.raises(CouponNotFound):
            apply_coupon("NOPE", 6700)


def test_uses_left_decrements(tmp_path):
    path = make_coupons_file(tmp_path, {"C": {"type": "percent", "value": 10, "uses_left": 3}})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import apply_coupon
        apply_coupon("C", 6700)
        data = json.loads(Path(path).read_text())
        assert data["C"]["uses_left"] == 2


def test_unlimited_coupon_not_decremented(tmp_path):
    path = make_coupons_file(tmp_path, {"INF": {"type": "percent", "value": 10, "uses_left": -1}})
    with patch("backend.coupons.COUPONS_FILE", path):
        from backend.coupons import apply_coupon
        apply_coupon("INF", 6700)
        data = json.loads(Path(path).read_text())
        assert data["INF"]["uses_left"] == -1
