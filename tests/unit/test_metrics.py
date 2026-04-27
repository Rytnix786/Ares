import numpy as np

from ares.metrics.drift import compute_drift_report, kl_divergence, population_stability_index


def test_kl_divergence_zero_for_same_distribution():
    assert kl_divergence(np.array([0.5, 0.5]), np.array([0.5, 0.5])) == 0.0


def test_psi_non_negative():
    assert population_stability_index(np.arange(10), np.arange(10)) >= 0


def test_compute_drift_report():
    assert compute_drift_report("x", np.arange(20), np.arange(20)).feature == "x"