"""Transparent programmatic metrics for a single experiment trace."""

from __future__ import annotations

from collections.abc import Iterable
from math import isfinite, sqrt


def _safe_rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_trace(
    committed: Iterable[bool],
    hard_violations: Iterable[int],
    repair_successes: Iterable[bool],
    target_tension: Iterable[float] = (),
    predicted_tension: Iterable[float] = (),
) -> dict[str, float]:
    commits = list(committed)
    violations = list(hard_violations)
    repairs = list(repair_successes)
    target = list(target_tension)
    predicted = list(predicted_tension)

    if len(commits) != len(violations):
        raise ValueError("committed and hard_violations must have equal length")
    if len(target) != len(predicted):
        raise ValueError("target_tension and predicted_tension must have equal length")
    if any(value < 0 for value in violations):
        raise ValueError("hard_violations cannot be negative")
    if any(not isfinite(value) for value in target + predicted):
        raise ValueError("tension curves must contain only finite values")

    invalid_commits = sum(v > 0 and c for c, v in zip(commits, violations, strict=False))
    committed_count = sum(commits)
    result = {
        "valid_commit_rate": (1.0 - invalid_commits / committed_count if committed_count else 0.0),
        "hard_violations_per_candidate": _safe_rate(sum(violations), len(violations)),
        "repair_at_k": _safe_rate(sum(repairs), len(repairs)),
    }
    if target:
        errors = [a - b for a, b in zip(target, predicted, strict=True)]
        result["tension_mae"] = sum(abs(error) for error in errors) / len(errors)
        result["tension_rmse"] = sqrt(sum(error * error for error in errors) / len(errors))
    return result
