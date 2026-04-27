from ares.metrics.significance import standard_error, wilson_confidence_interval


def test_standard_error_positive():
    assert standard_error(0.5, 100) == 0.05


def test_wilson_interval_bounds():
    lo, hi = wilson_confidence_interval(80, 100)
    assert 0 < lo < hi < 1