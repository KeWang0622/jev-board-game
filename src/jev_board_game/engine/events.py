"""Immutable event and record types shared across games."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Team(str, Enum):
    CIVILIAN = "civilian"
    UNDERCOVER = "undercover"


@dataclass(frozen=True)
class Player:
    id: str
    team: Team
    # Hidden per-game payload (e.g. the secret word). Never shown to other agents.
    secret: str | None = None


@dataclass(frozen=True)
class Clue:
    round_index: int
    speaker_id: str
    text: str


@dataclass(frozen=True)
class Vote:
    round_index: int
    voter_id: str
    target_id: str


@dataclass(frozen=True)
class BeliefRecord:
    """One observer's calibrated belief over who holds the hidden role.

    ``distribution`` maps candidate player id -> probability (sums to ~1 over the
    live candidates). ``ground_truth_id`` is the player that actually holds the
    role being guessed; it is used only for offline calibration analysis, never
    surfaced to agents.
    """

    round_index: int
    observer_id: str
    distribution: dict[str, float]
    ground_truth_id: str
    confidence: float

    def mass_on_truth(self) -> float:
        return self.distribution.get(self.ground_truth_id, 0.0)


@dataclass(frozen=True)
class JevDecision:
    """One judgement Jev returned, with its full typed output.

    ``kind`` is the decision type (e.g. "clue", "suspect"); ``options`` is the
    probability distribution Jev returned over the choices; ``choice`` is the
    selected option; ``confidence`` is the distribution's peakedness.
    """

    round_index: int
    agent_id: str
    kind: str
    question: str
    options: dict[str, float]
    choice: str
    confidence: float


@dataclass
class GameResult:
    winner: Team
    rounds_played: int
    eliminated_order: list[str] = field(default_factory=list)
    beliefs: list[BeliefRecord] = field(default_factory=list)
    transcript: list[Clue] = field(default_factory=list)
    votes: list[Vote] = field(default_factory=list)
    players: list[Player] = field(default_factory=list)
    undercover_id: str = ""
    decisions: list[JevDecision] = field(default_factory=list)
