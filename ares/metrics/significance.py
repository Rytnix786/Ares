from __future__ import annotations

import numpy as np
from scipy import stats


def standard_error(p: float, n: int) -> float:
    if n <= 0:
        raise ValueError("n must be positive")
    return float(np.sqrt(p * (1 - p) / n))


def is_improvement_significant(new_score: float, baseline_score: float, n: int, alpha: float = 0.05) -> tuple[bool, float]:
    se = standard_error(baseline_score, n)
    if se == 0:
        return new_score > baseline_score, 0.0 if new_score > baseline_score else 1.0
    z = (new_score - baseline_score) / se
    p_value = float(1 - stats.norm.cdf(z))
    return p_value < alpha, p_value


def wilson_confidence_interval(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("n must be positive")
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p_hat = successes / n
    denominator = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denominator
    margin = (z * np.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))) / denominator
    return float(center - margin), float(center + margin)


def cohens_h(p1: float, p2: float) -> float:
    return float(2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2)))