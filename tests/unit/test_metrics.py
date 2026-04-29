import numpy as np
import pytest

import ares.metrics.drift as drift_module
from ares.metrics.drift import compute_drift_report, kl_divergence, population_stability_index


def test_kl_divergence_zero_for_same_distribution():
    assert kl_divergence(np.array([0.5, 0.5]), np.array([0.5, 0.5])) == 0.0


def test_psi_non_negative():
    assert population_stability_index(np.arange(10), np.arange(10)) >= 0


def test_compute_drift_report():
    assert compute_drift_report("x", np.arange(20), np.arange(20)).feature == "x"


def test_population_stability_index_rejects_empty_inputs() -> None:
    with pytest.raises(ValueError, match="expected and actual must be non-empty"):
        population_stability_index(np.array([]), np.array([1.0]))


def test_population_stability_index_handles_single_breakpoint() -> None:
    assert population_stability_index(np.ones(10), np.ones(10)) == 0.0


def test_compute_drift_report_severity_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(drift_module, "kl_divergence", lambda *_args, **_kwargs: 0.11)
    monkeypatch.setattr(drift_module, "population_stability_index", lambda *_args, **_kwargs: 0.05)
    warning = compute_drift_report(
        "warning",
        np.array([0, 0, 0, 1, 1, 1], dtype=float),
        np.array([0, 0, 1, 1, 1, 1], dtype=float),
        kl_threshold=0.10,
        psi_threshold=0.20,
    )
    assert warning.severity == "warning"
    assert warning.is_alerting is True

    monkeypatch.setattr(drift_module, "kl_divergence", lambda *_args, **_kwargs: 0.16)
    monkeypatch.setattr(drift_module, "population_stability_index", lambda *_args, **_kwargs: 0.24)
    critical = compute_drift_report("critical", np.array([0] * 50 + [1] * 50), np.array([0] * 5 + [1] * 95), kl_threshold=0.01, psi_threshold=0.01)
    assert critical.severity == "critical"
    assert critical.is_alerting is True

    monkeypatch.setattr(drift_module, "kl_divergence", lambda *_args, **_kwargs: 0.0)
    monkeypatch.setattr(drift_module, "population_stability_index", lambda *_args, **_kwargs: 0.0)
    none = compute_drift_report("stable", np.arange(20), np.arange(20), kl_threshold=1.0, psi_threshold=1.0)
    assert none.severity == "none"
    assert none.is_alerting is False


def test_request_id_propagation() -> None:
    """Verify request_id is bound to log context."""
    from ares.observability.metrics import get_current_request_id, request_id_var

    token = request_id_var.set("test-request-123")
    try:
        assert get_current_request_id() == "test-request-123"
    finally:
        request_id_var.reset(token)