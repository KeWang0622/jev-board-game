"""Abstract social-deduction game contract shared by Undercover, Werewolf, Avalon."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .events import GameResult


class SocialDeductionGame(ABC):
    """A hidden-role game driven by Jev-backed agents.

    Concrete games own their rules (roles, win conditions, round structure) and
    emit a :class:`~jev_board_game.engine.events.GameResult` that always includes a
    per-round belief trajectory, so the analysis harness is game-agnostic.
    """

    name: str

    @abstractmethod
    def play(self) -> GameResult:
        """Run one full game to completion and return its result."""
