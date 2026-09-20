"""Jev-backed agent for Undercover.

Design invariant: the agent knows only its own secret word and the public
transcript. It is NEVER told its team (in Undercover no one is told whether their
word is the majority or the minority), so its suspicion of others is a genuine
inference. Ground-truth team is used only by the offline analysis harness.

The agent uses two Jev judgements:

* clue selection  -> Choice over its word's candidate clues ("select not generate")
* suspicion       -> Choice over the other living players; that probability
                     distribution IS the agent's calibrated belief.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..engine.events import Clue, Player
from ..jev.client import JevBackend
from ..jev.types import Choice, ChoiceAnswer


@dataclass
class Assessment:
    distribution: dict[str, float]
    confidence: float


class UndercoverAgent:
    def __init__(self, player: Player, backend: JevBackend) -> None:
        self.player = player
        self.backend = backend

    @property
    def id(self) -> str:
        return self.player.id

    CLUE_QUESTION = (
        "Which clue should you say next to blend in without revealing that "
        "your word might differ from the others?"
    )
    SUSPECT_QUESTION = "Which other player most likely has the odd word (the spy)?"

    def choose_clue(
        self, candidate_clues: list[str], transcript: list[Clue], round_index: int
    ) -> ChoiceAnswer:
        """Pick a clue that describes my word while blending with what was said.

        Returns the full Jev decision (chosen clue + distribution over all
        candidate clues + confidence), so callers can log every judgement.
        """

        state = {
            "your_secret_word": self.player.secret or "",
            "clues_already_spoken_this_game": [
                f"{c.speaker_id}: {c.text}" for c in transcript
            ],
            "task": (
                "You do not know whether your word is the same as most players' or "
                "different. Choose a clue about your word that fits in with the group "
                "so you are not singled out, while staying truthful to your word."
            ),
        }
        question = Choice(
            instructions=self.CLUE_QUESTION,
            criteria={clue: None for clue in candidate_clues},
        )
        return self.backend.ask(state, {"clue": question}).choice("clue")

    def assess(
        self,
        candidates: dict[str, list[str]],
        transcript: list[Clue],
        round_index: int,
    ) -> Assessment:
        """Form a calibrated belief over which candidate holds the odd word.

        ``candidates`` maps each *other* living player's id -> the clues they have
        spoken. The returned distribution is Jev's Choice probabilities.
        """

        state = {
            "your_secret_word": self.player.secret or "",
            "full_transcript": [f"{c.speaker_id}: {c.text}" for c in transcript],
            "task": (
                "One player secretly has a different word from the majority. Find the "
                "player whose clues fit the group least — they are the likely spy."
            ),
        }
        question = Choice(
            instructions=self.SUSPECT_QUESTION,
            criteria={
                pid: "clues given: " + " | ".join(clues) if clues else "no clues yet"
                for pid, clues in candidates.items()
            },
        )
        answer = self.backend.ask(state, {"suspect": question}).choice("suspect")
        return Assessment(distribution=dict(answer.probabilities), confidence=answer.confidence)

    @staticmethod
    def vote_from(assessment: Assessment) -> str:
        """Deterministic vote: the most-suspected candidate."""

        return max(assessment.distribution, key=lambda k: assessment.distribution[k])
