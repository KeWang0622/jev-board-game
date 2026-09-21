"""Jev-backed agent for Avalon (The Resistance).

Knowledge (enforced by the game):

* **evil** players know each other;
* **Merlin** (good) knows who is evil but must stay hidden;
* loyal **servants** know only public quest history.

Jev judgements:

* suspicion  -> `Choice` over the other players (belief over who is evil; logged);
* approval   -> `Noul` on a proposed quest team (probability to approve);
* sabotage   -> `Noul` for an evil player on a quest (probability to fail it);
* assassinate-> `Choice` over the good players (the Assassin's Merlin guess).
"""

from __future__ import annotations

from ..engine.events import Player
from ..jev.client import JevBackend
from ..jev.types import Choice, ChoiceAnswer, Noul
from .jev_agent import Assessment


class AvalonAgent:
    SUSPECT_Q = "Which other player is most likely on the evil side?"
    APPROVE_Q = "Should this proposed quest team be approved?"
    SABOTAGE_Q = "As an evil player on this quest, should you play a FAIL card?"
    ASSASSIN_Q = "You are the Assassin. Which good player is Merlin?"

    def __init__(self, player: Player, backend: JevBackend, known_evil: frozenset[str]) -> None:
        self.player = player
        self.backend = backend
        self.known_evil = known_evil  # non-empty for evil players and for Merlin

    @property
    def id(self) -> str:
        return self.player.id

    def suspect(
        self, candidates: dict[str, dict[str, object]], history: list[str]
    ) -> Assessment:
        criteria: dict[str, str | None] = {}
        for pid, ctx in candidates.items():
            if ctx.get("known") == "evil":
                criteria[pid] = "you secretly KNOW this player is EVIL"
            else:
                on = ctx.get("on_teams", 0)
                failed = ctx.get("failed_teams", 0)
                criteria[pid] = f"was on {on} quest team(s), {failed} of which FAILED"
        state = {
            "quest_history": history,
            "task": "Find the evil players. Players who were on failed quests are suspicious.",
        }
        q = Choice(instructions=self.SUSPECT_Q, criteria=criteria)
        ans = self.backend.ask(state, {"evil": q}).choice("evil")
        return Assessment(distribution=dict(ans.probabilities), confidence=ans.confidence)

    def approve(self, team: list[str], team_suspects: str, history: list[str]) -> float:
        state = {
            "proposed_team": team,
            "your_read_on_the_team": team_suspects,
            "quest_history": history,
            "task": "Approve teams you trust; reject teams that likely contain evil.",
        }
        q = Noul(instructions=self.APPROVE_Q)
        return self.backend.ask(state, {"ok": q}).noul("ok").noul

    def sabotage(self, quest_index: int, history: list[str]) -> float:
        state = {
            "you_are": "evil, on this quest team",
            "quest_number": quest_index + 1,
            "quest_history": history,
            "task": "Failing advances evil, but too many fails exposes the pack.",
        }
        q = Noul(instructions=self.SABOTAGE_Q)
        return self.backend.ask(state, {"fail": q}).noul("fail").noul

    def assassinate(self, good_players: list[str], history: list[str]) -> ChoiceAnswer:
        state = {
            "good_players_remaining": good_players,
            "quest_history": history,
            "task": "Merlin subtly steered the town; identify who it was to steal the win.",
        }
        q = Choice(instructions=self.ASSASSIN_Q, criteria=dict.fromkeys(good_players))
        return self.backend.ask(state, {"merlin": q}).choice("merlin")
