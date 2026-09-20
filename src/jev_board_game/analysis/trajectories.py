"""Belief-trajectory aggregation: how suspicion of the true spy evolves per round."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ..engine.events import BeliefRecord


@dataclass(frozen=True)
class TrajectoryPoint:
    round_index: int
    mean_mass_on_truth: float
    mean_confidence: float
    n_observers: int


def belief_trajectory(records: Sequence[BeliefRecord]) -> list[TrajectoryPoint]:
    """Mean belief mass placed on the true spy, per round (averaged over observers).

    A rising curve means the group's calibrated suspicion converges on the spy.
    """

    by_round: dict[int, list[BeliefRecord]] = {}
    for r in records:
        by_round.setdefault(r.round_index, []).append(r)
    points: list[TrajectoryPoint] = []
    for rnd in sorted(by_round):
        group = by_round[rnd]
        points.append(
            TrajectoryPoint(
                round_index=rnd,
                mean_mass_on_truth=float(np.mean([r.mass_on_truth() for r in group])),
                mean_confidence=float(np.mean([r.confidence for r in group])),
                n_observers=len(group),
            )
        )
    return points


def plot_trajectory(points: Sequence[TrajectoryPoint], path: str) -> None:
    """Save a belief-trajectory plot. Requires the optional ``plots`` extra."""

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Plotting needs matplotlib. Install with: pip install 'jev-board-game[plots]'"
        ) from exc

    rounds = [p.round_index for p in points]
    mass = [p.mean_mass_on_truth for p in points]
    conf = [p.mean_confidence for p in points]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(rounds, mass, "o-", label="belief mass on true spy")
    ax.plot(rounds, conf, "s--", label="mean confidence", alpha=0.7)
    ax.set_xlabel("round")
    ax.set_ylabel("probability")
    ax.set_ylim(0, 1)
    ax.set_title("Belief trajectory")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
