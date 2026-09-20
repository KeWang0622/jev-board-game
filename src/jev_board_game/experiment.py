"""Run many games under one or more configurations and aggregate the analysis."""

from __future__ import annotations

from dataclasses import dataclass, field

from .analysis.calibration import CalibrationReport, analyze
from .analysis.trajectories import TrajectoryPoint, belief_trajectory
from .engine.events import BeliefRecord, Team
from .games.undercover import Undercover
from .jev.client import JevBackend


@dataclass
class ExperimentConfig:
    n_players: int = 5
    max_reveal: int = 2
    games: int = 20
    base_seed: int = 0

    def label(self) -> str:
        return f"players={self.n_players},max_reveal={self.max_reveal}"


@dataclass
class ExperimentResult:
    config: ExperimentConfig
    games_played: int
    civilian_win_rate: float
    mean_rounds: float
    calibration: CalibrationReport
    trajectory: list[TrajectoryPoint] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"[{self.config.label()}] games={self.games_played} "
            f"civ_win_rate={self.civilian_win_rate:.3f} "
            f"mean_rounds={self.mean_rounds:.2f} | {self.calibration.summary()}"
        )


def run_experiment(backend: JevBackend, config: ExperimentConfig) -> ExperimentResult:
    all_beliefs: list[BeliefRecord] = []
    civ_wins = 0
    total_rounds = 0
    for g in range(config.games):
        game = Undercover(
            backend=backend,
            n_players=config.n_players,
            max_reveal=config.max_reveal,
            seed=config.base_seed + g,
        )
        result = game.play()
        all_beliefs.extend(result.beliefs)
        civ_wins += int(result.winner is Team.CIVILIAN)
        total_rounds += result.rounds_played
    return ExperimentResult(
        config=config,
        games_played=config.games,
        civilian_win_rate=civ_wins / config.games if config.games else 0.0,
        mean_rounds=total_rounds / config.games if config.games else 0.0,
        calibration=analyze(all_beliefs),
        trajectory=belief_trajectory(all_beliefs),
    )


def sweep(
    backend: JevBackend,
    player_counts: list[int],
    reveal_levels: list[int],
    games: int = 20,
    base_seed: int = 0,
) -> list[ExperimentResult]:
    results: list[ExperimentResult] = []
    for n in player_counts:
        for r in reveal_levels:
            cfg = ExperimentConfig(
                n_players=n, max_reveal=r, games=games, base_seed=base_seed
            )
            results.append(run_experiment(backend, cfg))
    return results
