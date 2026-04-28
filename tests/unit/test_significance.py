import math

import pytest

from ares.metrics.significance import (
    cohens_h,
    is_improvement_significant,
    standard_error,
    wilson_confidence_interval,
)


def test_standard_error_positive():
    assert standard_error(0.5, 100) == 0.05


def test_standard_error_rejects_non_positive_n() -> None:
    with pytest.raises(ValueError, match="n must be positive"):
        standard_error(0.5, 0)


def test_wilson_interval_bounds():
    lo, hi = wilson_confidence_interval(80, 100)
    assert 0 < lo < hi < 1


def test_wilson_interval_rejects_non_positive_n() -> None:
    with pytest.raises(ValueError, match="n must be positive"):
        wilson_confidence_interval(1, 0)


def test_is_improvement_significant_handles_zero_standard_error() -> None:
    assert is_improvement_significant(0.8, 1.0, 10) == (False, 1.0)
    assert is_improvement_significant(1.0, 1.0, 10) == (False, 1.0)


def test_is_improvement_significant_computes_probability_branch() -> None:
    significant, p_value = is_improvement_significant(0.7, 0.5, 100)
    assert significant is True
    assert 0.0 <= p_value < 0.05


def test_cohens_h_returns_expected_value() -> None:
    value = cohens_h(0.8, 0.2)
    assert math.isclose(value, 1.287, rel_tol=1e-3)