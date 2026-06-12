"""Density-diversification effect metrics.

Small pure helpers used by reports, examples, and regression tests to keep
the public CV-reduction headline computed the same way everywhere.
"""
from __future__ import annotations

import statistics
from collections.abc import Iterable


def coefficient_of_variation(values: Iterable[int | float]) -> float:
    """Return population coefficient of variation: population stdev / mean.

    Empty or all-zero populations return 0.0 rather than raising; for Aurelia's
    balancing claim, a zero-mean population has no cross-world variance to
    reduce.
    """
    vals = [float(v) for v in values]
    if not vals:
        return 0.0
    mean = statistics.fmean(vals)
    if mean == 0:
        return 0.0
    return statistics.pstdev(vals) / mean


def cv_reduction(before: Iterable[int | float], after: Iterable[int | float]) -> float:
    """Return fractional CV reduction from ``before`` to ``after``.

    ``0.90`` means the post-diversification CV is 90% lower than the baseline.
    If the baseline CV is already zero, return 0.0 because there is no variance
    available to reduce.
    """
    baseline = coefficient_of_variation(before)
    if baseline == 0:
        return 0.0
    post = coefficient_of_variation(after)
    return 1.0 - (post / baseline)
