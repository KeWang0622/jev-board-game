"""Werewolf (Mafia) — planned. Shares the engine + belief-logging contract.

Roadmap: night/day cycle, roles (Werewolf, Seer, Doctor, Villager), Jev-backed
per-phase judgements (accusation targeting, seer inspection choice, defence
credibility). The belief object is each villager's distribution over "who is a
werewolf", logged every day phase for the same calibration analysis as Undercover.
"""

from __future__ import annotations

from ..engine.events import GameResult
from ..engine.game import SocialDeductionGame


class Werewolf(SocialDeductionGame):
    name = "werewolf"

    def play(self) -> GameResult:
        raise NotImplementedError(
            "Werewolf is scaffolded but not yet implemented. See docstring for the "
            "planned design; Undercover is the reference implementation."
        )
