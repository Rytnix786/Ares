"""Unit tests for metrics/significance.py."""

from __future__ import annotations

from ares.metrics.significance import (
    cohens_h,
    is_improvement_significant,
    standard_error,
    wilson_confidence_interval,
)


class TestStandardError:
    """Test standard error calculation."""

    def test_standard_error_basic(self):
        """Test basic standard error calculation."""
        se = standard_error(0.5, 100)
        assert se > 0
        assert se < 1  # Should be reasonable

    def test_standard_edge_case(self):
        """Test standard error with edge case values."""
        se = standard_error(0.0, 100)
        assert se == 0

    def test_standard_error_small_sample(self):
        """Test standard error with small sample."""
        se = standard_error(0.5, 10)
        assert se > 0


class TestIsImprovementSignificant:
    """Test significance testing."""

    def test_significant_improvement(self):
        """Test that significant improvement is detected."""
        # Large improvement with reasonable sample size
        result, _ = is_improvement_significant(0.6, 0.5, 1000, 0.05)
        assert result is True

    def test_no_improvement(self):
        """Test that no improvement is not significant."""
        result, _ = is_improvement_significant(0.5, 0.5, 1000, 0.05)
        assert result is False

    def test_small_improvement_large_sample(self):
        """Test that small improvement can be significant with large sample."""
        result, _ = is_improvement_significant(0.51, 0.5, 10000, 0.05)
        assert result is True

    def test_small_improvement_small_sample(self):
        """Test that small improvement is not significant with small sample."""
        result, _ = is_improvement_significant(0.51, 0.5, 10, 0.05)
        assert result is False

    def test_different_alpha(self):
        """Test that different alpha levels affect significance."""
        result_strict, _ = is_improvement_significant(0.51, 0.5, 1000, 0.01)
        result_lenient, _ = is_improvement_significant(0.51, 0.5, 1000, 0.10)
        # More lenient alpha should be more likely to be significant
        assert result_lenient >= result_strict


class TestWilsonConfidenceInterval:
    """Test Wilson confidence interval calculation."""

    def test_wilson_interval_basic(self):
        """Test basic Wilson interval calculation."""
        lower, upper = wilson_confidence_interval(50, 100, 0.95)  # 50 successes out of 100
        assert 0 <= lower < 1
        assert 0 <= upper <= 1
        assert upper - lower > 0

    def test_wilson_interval_edge_case(self):
        """Test Wilson interval with edge case (p=0)."""
        lower, upper = wilson_confidence_interval(0, 100, 0.95)
        assert lower >= 0  # Can be very close to 0 but not exactly
        assert upper > 0

    def test_wilson_interval_edge_case_one(self):
        """Test Wilson interval with edge case (p=1)."""
        lower, upper = wilson_confidence_interval(100, 100, 0.95)
        assert lower < 1
        assert upper <= 1  # Can be very close to 1 but not exactly

    def test_wilson_interval_small_sample(self):
        """Test Wilson interval with small sample."""
        lower, upper = wilson_confidence_interval(5, 10, 0.95)  # 5 successes out of 10
        assert 0 <= lower <= 1
        assert 0 <= upper <= 1
        # Small sample should have wider interval
        assert upper - lower > 0.3


class TestCohensH:
    """Test Cohen's h effect size calculation."""

    def test_cohens_h_basic(self):
        """Test basic Cohen's h calculation."""
        h = cohens_h(0.6, 0.5)
        assert h > 0
        assert h < 1  # Should be reasonable

    def test_cohens_h_no_difference(self):
        """Test Cohen's h with no difference."""
        h = cohens_h(0.5, 0.5)
        assert h == 0

    def test_cohens_h_large_difference(self):
        """Test Cohen's h with large difference."""
        h = cohens_h(0.9, 0.1)
        assert h > 1  # Large effect size

    def test_cohens_h_symmetry(self):
        """Test that Cohen's h magnitude is symmetric (sign flips)."""
        h1 = cohens_h(0.6, 0.4)
        h2 = cohens_h(0.4, 0.6)
        # Magnitude should be the same, sign should be opposite
        assert abs(abs(h1) - abs(h2)) < 0.001
        assert h1 == -h2
