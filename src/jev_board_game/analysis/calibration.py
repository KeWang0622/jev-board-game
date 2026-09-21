"""Calibration metrics for belief records.

Each :class:`~jev_board_game.engine.events.BeliefRecord` is a probabilistic guess
over which candidate holds the hidden role. We flatten every (record, candidate)
pair into a binary prediction ``p = P(candidate is the spy)`` with label ``1`` iff
that candidate is the ground-truth spy, and measure how well those probabilities
are calibrated.

The scientific point of the repo: a calibrated System-One model should make these
numbers good *natively*, without the post-hoc recalibration that autoregressive
verbalized-confidence probing requires.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ..engine.events import BeliefRecord


@dataclass(frozen=True)
class CalibrationReport:
    n_records: int
    n_binary: int
    top1_accuracy: float
    mean_mass_on_truth: float
    brier: float
    ece: float
    reliability_bins: list[tuple[float, float, int]]  # (mean_pred, mean_true, count)

    def summary(self) -> str:
        return (
            f"records={self.n_records}  top1_acc={self.top1_accuracy:.3f}  "
            f"mass_on_truth={self.mean_mass_on_truth:.3f}  "
            f"brier={self.brier:.4f}  ECE={self.ece:.4f}"
        )


def _binary_pairs(records: Sequence[BeliefRecord]) -> tuple[np.ndarray, np.ndarray]:
    preds: list[float] = []
    labels: list[float] = []
    for r in records:
        truths = r.truths()
        for cand, p in r.distribution.items():
            preds.append(float(p))
            labels.append(1.0 if cand in truths else 0.0)
    return np.asarray(preds, dtype=float), np.asarray(labels, dtype=float)


def expected_calibration_error(
    preds: np.ndarray, labels: np.ndarray, n_bins: int = 10
) -> tuple[float, list[tuple[float, float, int]]]:
    if preds.size == 0:
        return 0.0, []
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    bins: list[tuple[float, float, int]] = []
    total = preds.size
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        # include right edge in the last bin
        mask = (preds >= lo) & (preds < hi)
        if hi == 1.0:
            mask |= preds == 1.0
        count = int(mask.sum())
        if count == 0:
            continue
        mean_pred = float(preds[mask].mean())
        mean_true = float(labels[mask].mean())
        ece += (count / total) * abs(mean_pred - mean_true)
        bins.append((mean_pred, mean_true, count))
    return ece, bins


def brier_score(records: Sequence[BeliefRecord]) -> float:
    """Mean multiclass Brier score over records (0 best, 2 worst)."""

    if not records:
        return 0.0
    total = 0.0
    for r in records:
        truths = r.truths()
        s = 0.0
        for cand, p in r.distribution.items():
            y = 1.0 if cand in truths else 0.0
            s += (p - y) ** 2
        total += s
    return total / len(records)


def top1_accuracy(records: Sequence[BeliefRecord]) -> float:
    if not records:
        return 0.0
    hits = 0
    for r in records:
        if not r.distribution:
            continue
        pick = max(r.distribution, key=lambda k: r.distribution[k])
        hits += int(pick in r.truths())
    return hits / len(records)


def analyze(records: Sequence[BeliefRecord], n_bins: int = 10) -> CalibrationReport:
    preds, labels = _binary_pairs(records)
    ece, bins = expected_calibration_error(preds, labels, n_bins=n_bins)
    mean_mass = float(np.mean([r.mass_on_truth() for r in records])) if records else 0.0
    return CalibrationReport(
        n_records=len(records),
        n_binary=int(preds.size),
        top1_accuracy=top1_accuracy(records),
        mean_mass_on_truth=mean_mass,
        brier=brier_score(records),
        ece=ece,
        reliability_bins=bins,
    )
