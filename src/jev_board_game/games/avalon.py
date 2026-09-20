"""Avalon (The Resistance) — planned. Shares the engine + belief-logging contract.

Roadmap: team-proposal / quest structure, roles (Merlin, Percival, Morgana,
Assassin, loyal servants, minions), Jev-backed judgements for team approval
(Noul per proposal), quest sabotage inference, and the Assassin's Merlin guess
(Choice). The belief object is each player's distribution over "who is evil",
logged every quest, feeding the same calibration analysis as Undercover.
"""

from __future__ import annotations

from ..engine.events import GameResult
from ..engine.game import SocialDeductionGame


class Avalon(SocialDeductionGame):
    name = "avalon"

    def play(self) -> GameResult:
        raise NotImplementedError(
            "Avalon is scaffolded but not yet implemented. See docstring for the "
            "planned design; Undercover is the reference implementation."
        )
