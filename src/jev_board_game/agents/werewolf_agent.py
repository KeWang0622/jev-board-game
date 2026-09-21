"""Jev-backed agent for Werewolf.

Knowledge is asymmetric and enforced by the game, not the agent:

* a **werewolf** knows the wolf pack (its teammates) and picks night victims and
  day-lynch targets to protect the pack;
* the **seer** learns one player's true alignment each night and folds that into
  its daytime suspicion;
* a **villager** only sees public statements and votes.

Every judgement is a Jev `Choice`; the town's suspicion distribution is the
calibrated belief the analysis harness scores against the wolf pack.
"""

from __future__ import annotations

from ..engine.events import Clue, Player
from ..jev.client import JevBackend
from ..jev.types import Choice, ChoiceAnswer
from .jev_agent import Assessment


def _transcript_lines(transcript: list[Clue]) -> list[str]:
    return [f"{c.speaker_id}: {c.text}" for c in transcript]


class WerewolfAgent:
    NIGHT_KILL_Q = "As a werewolf, which townsfolk should the pack eliminate tonight?"
    SEER_Q = "As the seer, which living player should you inspect tonight?"
    STATEMENT_Q = "What should you say in the day discussion?"
    SUSPECT_Q = "Which living player is most likely a werewolf?"
    WOLF_VOTE_Q = "As a werewolf, which townsperson should you vote to lynch (to protect the pack)?"

    def __init__(self, player: Player, backend: JevBackend, fellow_wolves: frozenset[str]) -> None:
        self.player = player
        self.backend = backend
        self.fellow_wolves = fellow_wolves

    @property
    def id(self) -> str:
        return self.player.id

    def night_kill(
        self, targets: list[str], transcript: list[Clue], round_index: int
    ) -> ChoiceAnswer:
        state = {
            "you_are": "a werewolf",
            "your_pack": sorted(self.fellow_wolves),
            "day_discussion_so_far": _transcript_lines(transcript),
            "task": "Eliminate the townsperson most dangerous to the pack "
            "(e.g. a likely seer or a persuasive accuser).",
        }
        q = Choice(instructions=self.NIGHT_KILL_Q, criteria=dict.fromkeys(targets))
        return self.backend.ask(state, {"kill": q}).choice("kill")

    def seer_inspect(
        self, targets: list[str], transcript: list[Clue], round_index: int
    ) -> ChoiceAnswer:
        state = {
            "you_are": "the seer",
            "day_discussion_so_far": _transcript_lines(transcript),
            "task": "Inspect the player whose alignment you most need to confirm.",
        }
        q = Choice(instructions=self.SEER_Q, criteria=dict.fromkeys(targets))
        return self.backend.ask(state, {"inspect": q}).choice("inspect")

    def day_statement(
        self, others: list[str], transcript: list[Clue], round_index: int
    ) -> ChoiceAnswer:
        candidates = [f"I think {o} is a werewolf." for o in others]
        candidates.append("I'm on the town's side — you can trust me.")
        role_hint = (
            "You are a werewolf: deflect suspicion and cast doubt on the town "
            "without exposing your pack."
            if self.player.team.value == "werewolf"
            else "You are on the town's side: say what best helps find the werewolves."
        )
        state = {
            "your_role_is_secret": role_hint,
            "day_discussion_so_far": _transcript_lines(transcript),
        }
        q = Choice(instructions=self.STATEMENT_Q, criteria=dict.fromkeys(candidates))
        return self.backend.ask(state, {"say": q}).choice("say")

    def suspect(
        self,
        candidates: dict[str, dict[str, object]],
        transcript: list[Clue],
        round_index: int,
    ) -> Assessment:
        """Town belief over who is a werewolf. ``candidates`` maps id -> context."""

        criteria: dict[str, str | None] = {}
        for pid, ctx in candidates.items():
            known = ctx.get("known")
            said = ctx.get("statements") or []
            if known == "werewolf":
                criteria[pid] = "you inspected them and CONFIRMED they are a WEREWOLF"
            elif known == "town":
                criteria[pid] = "you inspected them and confirmed they are innocent town"
            else:
                said_list = said if isinstance(said, list) else []
                criteria[pid] = (
                    "said: " + " | ".join(str(s) for s in said_list)
                    if said_list
                    else "has said little"
                )
        state = {
            "full_day_discussion": _transcript_lines(transcript),
            "task": "Find the werewolves hiding among the town based on behavior "
            "and any confirmed inspections.",
        }
        q = Choice(instructions=self.SUSPECT_Q, criteria=criteria)
        ans = self.backend.ask(state, {"wolf": q}).choice("wolf")
        return Assessment(distribution=dict(ans.probabilities), confidence=ans.confidence)

    def wolf_vote(
        self, targets: list[str], transcript: list[Clue], round_index: int
    ) -> ChoiceAnswer:
        state = {
            "you_are": "a werewolf",
            "your_pack": sorted(self.fellow_wolves),
            "day_discussion_so_far": _transcript_lines(transcript),
            "task": "Vote to lynch a townsperson while blending in with the town's suspicions.",
        }
        q = Choice(instructions=self.WOLF_VOTE_Q, criteria=dict.fromkeys(targets))
        return self.backend.ask(state, {"vote": q}).choice("vote")
