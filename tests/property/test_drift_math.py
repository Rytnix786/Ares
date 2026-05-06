from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ares.metrics.drift import (
    compute_drift_report,
    kl_divergence,
    population_stability_index,
)


def _normalize(values: list[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    return array / array.sum()


@given(
    st.lists(
        st.floats(min_value=0.001, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=8,
    ),
    st.lists(
        st.floats(min_value=0.001, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=8,
    ),
)
def test_kl_divergence_is_non_negative(p_values: list[float], q_values: list[float]) -> None:
    if len(p_values) != len(q_values):
        q_values = q_values[: len(p_values)] or [0.5] * len(p_values)
        if len(q_values) < len(p_values):
            q_values = q_values + [0.5] * (len(p_values) - len(q_values))
    p = _normalize(p_values)
    q = _normalize(q_values)
    assert kl_divergence(p, q) >= 0.0


@given(
    st.lists(
        st.floats(min_value=0.001, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=20,
        max_size=80,
    ),
    st.lists(
        st.floats(min_value=0.001, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=20,
        max_size=80,
    ),
)
def test_population_stability_index_is_non_negative(
    expected_values: list[float],
    actual_values: list[float],
) -> None:
    psi = population_stability_index(np.asarray(expected_values), np.asarray(actual_values))
    assert psi >= 0.0


@given(
    st.lists(
        st.floats(min_value=0.001, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=8,
    )
)
def test_kl_divergence_of_distribution_with_itself_is_zero(values: list[float]) -> None:
    distribution = _normalize(values)
    assert kl_divergence(distribution, distribution) == pytest.approx(0.0, abs=1e-9)


@given(
    st.lists(
        st.floats(min_value=0.001, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=50,
        max_size=50,
    ),
    st.floats(min_value=0.001, max_value=0.20, allow_nan=False, allow_infinity=False),
)
def test_drift_severity_grows_monotonically_with_larger_distribution_shift(
    baseline_values: list[float],
    shift: float,
) -> None:
    baseline = np.asarray(baseline_values, dtype=float)
    small_shift = baseline.copy()
    large_shift = baseline.copy()
    small_shift[0] += shift
    large_shift[0] += shift * 2.0
    small_report = compute_drift_report("feature", baseline, small_shift)
    large_report = compute_drift_report("feature", baseline, large_shift)
    severity_order = {"none": 0, "warning": 1, "critical": 2}
    assert severity_order[small_report.severity] <= severity_order[large_report.severity]
