"""Undercover (Who-Is-The-Spy): the first fully implemented game.

Rules (single-undercover variant):
- ``n_players`` players; one secretly gets the ``undercover`` word, the rest get
  the ``civilian`` word. No one is told which they hold.
- Each round every living player speaks one clue, then everyone votes; the player
  with the most votes is eliminated.
- Civilians win if the undercover is voted out. The undercover wins if they survive
  until only two players remain.

Every round we log each living player's Jev-derived belief over who the spy is, so
the analysis harness can measure calibration against the known ground truth.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import dataclass
from importlib import resources
from typing import Any

from ..agents.jev_agent import UndercoverAgent
from ..engine.events import BeliefRecord, Clue, GameResult, Player, Team, Vote
from ..engine.game import SocialDeductionGame
from ..jev.client import JevBackend


@dataclass
class ClueBank:
    word: str
    clues: list[str]


def load_word_pairs() -> list[dict[str, Any]]:
    raw = resources.files("jev_board_game.data").joinpath("undercover_words.json").read_text(
        encoding="utf-8"
    )
    pairs: list[dict[str, Any]] = json.loads(raw)["pairs"]
    return pairs


class Undercover(SocialDeductionGame):
    name = "undercover"

    def __init__(
        self,
        backend: JevBackend,
        n_players: int = 5,
        max_reveal: int = 2,
        max_rounds: int = 6,
        seed: int | None = None,
        word_pairs: list[dict[str, Any]] | None = None,
    ) -> None:
        if n_players < 3:
            raise ValueError("Undercover needs at least 3 players")
        self.backend = backend
        self.n_players = n_players
        self.max_reveal = max_reveal
        self.max_rounds = max_rounds
        self.rng = random.Random(seed)
        self.word_pairs = word_pairs if word_pairs is not None else load_word_pairs()

    def _build_players(self) -> tuple[list[Player], dict[str, ClueBank], str]:
        pair = self.rng.choice(self.word_pairs)
        ids = [f"P{i + 1}" for i in range(self.n_players)]
        undercover_id = self.rng.choice(ids)
        players: list[Player] = []
        clue_banks: dict[str, ClueBank] = {}
        for pid in ids:
            is_spy = pid == undercover_id
            word = pair["undercover"] if is_spy else pair["civilian"]
            team = Team.UNDERCOVER if is_spy else Team.CIVILIAN
            players.append(Player(id=pid, team=team, secret=word))
            clue_banks[pid] = ClueBank(
                word=word,
                clues=[
                    c["text"] for c in pair["clues"][word] if c["reveal"] <= self.max_reveal
                ],
            )
        return players, clue_banks, undercover_id

    def play(self) -> GameResult:
        players, clue_banks, undercover_id = self._build_players()
        agents = {p.id: UndercoverAgent(p, self.backend) for p in players}
        living = {p.id for p in players}
        used_clues: dict[str, set[str]] = {p.id: set() for p in players}
        spoken: dict[str, list[str]] = {p.id: [] for p in players}

        transcript: list[Clue] = []
        beliefs: list[BeliefRecord] = []
        all_votes: list[Vote] = []
        eliminated_order: list[str] = []

        result = GameResult(winner=Team.UNDERCOVER, rounds_played=0)
        rounds_played = 0

        for round_index in range(self.max_rounds):
            if len(living) <= 2:
                break
            rounds_played = round_index + 1

            # --- clue phase (order shuffled each round) ---
            speak_order = sorted(living)
            self.rng.shuffle(speak_order)
            for pid in speak_order:
                candidates = [
                    c for c in clue_banks[pid].clues if c not in used_clues[pid]
                ] or list(clue_banks[pid].clues)
                clue_text = agents[pid].choose_clue(candidates, transcript, round_index)
                used_clues[pid].add(clue_text)
                spoken[pid].append(clue_text)
                transcript.append(Clue(round_index, pid, clue_text))

            # --- belief phase ---
            for observer in sorted(living):
                others = {pid: spoken[pid] for pid in sorted(living) if pid != observer}
                assessment = agents[observer].assess(others, transcript, round_index)
                beliefs.append(
                    BeliefRecord(
                        round_index=round_index,
                        observer_id=observer,
                        distribution=assessment.distribution,
                        ground_truth_id=undercover_id,
                        confidence=assessment.confidence,
                    )
                )

            # --- vote phase ---
            tally: Counter[str] = Counter()
            round_beliefs = {b.observer_id: b for b in beliefs if b.round_index == round_index}
            for voter in sorted(living):
                dist = round_beliefs[voter].distribution
                target = max(dist, key=lambda k: dist[k])
                all_votes.append(Vote(round_index, voter, target))
                tally[target] += 1

            eliminated = self._resolve_vote(tally, round_beliefs)
            living.discard(eliminated)
            eliminated_order.append(eliminated)

            if eliminated == undercover_id:
                result.winner = Team.CIVILIAN
                break
        else:
            rounds_played = self.max_rounds

        if undercover_id in living and undercover_id not in eliminated_order:
            result.winner = Team.UNDERCOVER

        result.rounds_played = rounds_played
        result.eliminated_order = eliminated_order
        result.beliefs = beliefs
        result.transcript = transcript
        result.votes = all_votes
        return result

    def _resolve_vote(
        self, tally: Counter[str], round_beliefs: dict[str, BeliefRecord]
    ) -> str:
        """Most-voted player is eliminated; ties broken by summed suspicion mass."""

        top = max(tally.values())
        tied = [pid for pid, v in tally.items() if v == top]
        if len(tied) == 1:
            return tied[0]

        def suspicion_mass(pid: str) -> float:
            return sum(b.distribution.get(pid, 0.0) for b in round_beliefs.values())

        return max(sorted(tied), key=suspicion_mass)
