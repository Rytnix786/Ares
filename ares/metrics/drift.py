from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import entropy


@dataclass(frozen=True)
class DriftReport:
    feature: str
    kl_divergence: float
    psi: float
    is_alerting: bool
    severity: str


def kl_divergence(p: np.ndarray, q: np.ndarray, epsilon: float = 1e-10) -> float:
    p = np.asarray(p, dtype=float) + epsilon
    q = np.asarray(q, dtype=float) + epsilon
    p /= p.sum()
    q /= q.sum()
    return float(entropy(p, q))


def population_stability_index(expected: np.ndarray, actual: np.ndarray, n_bins: int = 10) -> float:
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if len(expected) == 0 or len(actual) == 0:
        raise ValueError("expected and actual must be non-empty")
    breakpoints = np.unique(np.percentile(expected, np.linspace(0, 100, n_bins + 1)))
    if len(breakpoints) < 2:
        return 0.0
    expected_pct = np.histogram(expected, bins=breakpoints)[0] / len(expected)
    actual_pct = np.histogram(actual, bins=breakpoints)[0] / len(actual)
    expected_pct = np.where(expected_pct == 0, 1e-4, expected_pct)
    actual_pct = np.where(actual_pct == 0, 1e-4, actual_pct)
    return float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))


def compute_drift_report(feature_name: str, golden_distribution: np.ndarray, live_distribution: np.ndarray, kl_threshold: float = 0.1, psi_threshold: float = 0.2) -> DriftReport:
    kl = kl_divergence(live_distribution, golden_distribution)
    psi = population_stability_index(golden_distribution, live_distribution)
    severity = "none"
    if psi > psi_threshold or kl > 0.15:
        severity = "critical"
    elif psi > 0.1 or kl > kl_threshold:
        severity = "warning"
    return DriftReport(feature_name, kl, psi, severity != "none", severity)