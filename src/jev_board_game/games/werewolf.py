"""Werewolf (Mafia): the second fully implemented game.

Roles: ``n_werewolves`` werewolves, one seer, the rest villagers. Each round is a
night then a day:

- **Night.** The wolf pack picks a victim (Jev `Choice`, combined across wolves);
  the seer inspects one player and learns their true alignment.
- **Day.** Every living player makes a public statement (Jev `Choice` over a small
  statement bank), each town player forms a suspicion belief over who is a wolf
  (Jev `Choice`; this is the logged, calibration-scored belief), and everyone votes
  to lynch. The wolf pack votes strategically (its own Jev `Choice`).

Town wins when all wolves are gone; wolves win at parity (wolves >= town).
Beliefs are scored against the full wolf pack via `BeliefRecord.ground_truth_ids`.
"""

from __future__ import annotations

import random
from collections import Counter

from ..agents.werewolf_agent import WerewolfAgent
from ..engine.events import (
    BeliefRecord,
    Clue,
    GameResult,
    JevDecision,
    Player,
    Team,
    Vote,
)
from ..engine.game import SocialDeductionGame
from ..jev.client import JevBackend
from ..jev.types import ChoiceAnswer


class Werewolf(SocialDeductionGame):
    name = "werewolf"

    def __init__(
        self,
        backend: JevBackend,
        n_players: int = 6,
        n_werewolves: int = 1,
        include_seer: bool = True,
        max_rounds: int = 8,
        seed: int | None = None,
    ) -> None:
        min_players = n_werewolves + (1 if include_seer else 0) + 1
        if n_players < max(4, min_players):
            raise ValueError("Werewolf needs at least 4 players and room for every role")
        if n_werewolves < 1:
            raise ValueError("Werewolf needs at least one werewolf")
        self.backend = backend
        self.n_players = n_players
        self.n_werewolves = n_werewolves
        self.include_seer = include_seer
        self.max_rounds = max_rounds
        self.rng = random.Random(seed)

    def _build_players(self) -> list[Player]:
        ids = [f"P{i + 1}" for i in range(self.n_players)]
        self.rng.shuffle(ids)
        players: list[Player] = []
        cursor = 0
        for _ in range(self.n_werewolves):
            players.append(Player(id=ids[cursor], team=Team.WEREWOLF, role="werewolf"))
            cursor += 1
        if self.include_seer:
            players.append(Player(id=ids[cursor], team=Team.TOWN, role="seer"))
            cursor += 1
        for pid in ids[cursor:]:
            players.append(Player(id=pid, team=Team.TOWN, role="villager"))
        players.sort(key=lambda p: int(p.id[1:]))
        return players

    def play(self) -> GameResult:
        players = self._build_players()
        wolves = frozenset(p.id for p in players if p.team is Team.WEREWOLF)
        seer_id = next((p.id for p in players if p.role == "seer"), None)
        agents = {p.id: WerewolfAgent(p, self.backend, wolves) for p in players}
        living = {p.id for p in players}

        transcript: list[Clue] = []
        beliefs: list[BeliefRecord] = []
        decisions: list[JevDecision] = []
        all_votes: list[Vote] = []
        eliminated_order: list[str] = []
        night_kills: list[str] = []
        spoken: dict[str, list[str]] = {p.id: [] for p in players}
        seer_knowledge: dict[str, str] = {}

        def log(agent_id: str, kind: str, question: str, ans: ChoiceAnswer, rnd: int) -> None:
            decisions.append(
                JevDecision(
                    round_index=rnd,
                    agent_id=agent_id,
                    kind=kind,
                    question=question,
                    options=dict(ans.probabilities),
                    choice=ans.choice,
                    confidence=ans.confidence,
                )
            )

        def living_wolves() -> set[str]:
            return {w for w in wolves if w in living}

        def living_town() -> set[str]:
            return {pid for pid in living if pid not in wolves}

        def winner() -> Team | None:
            if not living_wolves():
                return Team.TOWN
            if len(living_wolves()) >= len(living_town()):
                return Team.WEREWOLF
            return None

        result = GameResult(winner=Team.WEREWOLF, rounds_played=0, game_type="werewolf")
        rounds_played = 0
        final: Team | None = None

        for rnd in range(self.max_rounds):
            if (final := winner()) is not None:
                break
            rounds_played = rnd + 1

            # ---------- NIGHT ----------
            victims = [pid for pid in sorted(living) if pid not in wolves]
            night_victim = ""
            if victims:
                pack_score: dict[str, float] = {}
                for w in sorted(living_wolves()):
                    ans = agents[w].night_kill(victims, transcript, rnd)
                    log(w, "night_kill", WerewolfAgent.NIGHT_KILL_Q, ans, rnd)
                    for k, p in ans.probabilities.items():
                        pack_score[k] = pack_score.get(k, 0.0) + p
                night_victim = max(sorted(victims), key=lambda k: pack_score.get(k, 0.0))
                living.discard(night_victim)
            night_kills.append(night_victim)

            if (final := winner()) is not None:
                break

            if seer_id and seer_id in living:
                to_inspect = [
                    pid for pid in sorted(living) if pid != seer_id and pid not in seer_knowledge
                ]
                if to_inspect:
                    ans = agents[seer_id].seer_inspect(to_inspect, transcript, rnd)
                    log(seer_id, "seer_inspect", WerewolfAgent.SEER_Q, ans, rnd)
                    seer_knowledge[ans.choice] = (
                        "werewolf" if ans.choice in wolves else "town"
                    )

            # ---------- DAY ----------
            speak_order = sorted(living)
            self.rng.shuffle(speak_order)
            for pid in speak_order:
                others = [o for o in sorted(living) if o != pid]
                ans = agents[pid].day_statement(others, transcript, rnd)
                log(pid, "statement", WerewolfAgent.STATEMENT_Q, ans, rnd)
                spoken[pid].append(ans.choice)
                transcript.append(Clue(rnd, pid, ans.choice))

            # town beliefs
            for observer in sorted(living_town()):
                candidates: dict[str, dict[str, object]] = {}
                for pid in sorted(living):
                    if pid == observer:
                        continue
                    ctx: dict[str, object] = {"statements": spoken[pid]}
                    if observer == seer_id and pid in seer_knowledge:
                        ctx["known"] = seer_knowledge[pid]
                    candidates[pid] = ctx
                assessment = agents[observer].suspect(candidates, transcript, rnd)
                beliefs.append(
                    BeliefRecord(
                        round_index=rnd,
                        observer_id=observer,
                        distribution=assessment.distribution,
                        ground_truth_id="",
                        confidence=assessment.confidence,
                        ground_truth_ids=wolves,
                    )
                )
                top = (
                    max(assessment.distribution, key=lambda k: assessment.distribution[k])
                    if assessment.distribution
                    else ""
                )
                decisions.append(
                    JevDecision(
                        round_index=rnd,
                        agent_id=observer,
                        kind="suspect",
                        question=WerewolfAgent.SUSPECT_Q,
                        options=dict(assessment.distribution),
                        choice=top,
                        confidence=assessment.confidence,
                    )
                )

            # votes
            round_belief = {b.observer_id: b for b in beliefs if b.round_index == rnd}
            tally: Counter[str] = Counter()
            for voter in sorted(living):
                if voter in wolves:
                    non_wolves = [pid for pid in sorted(living) if pid not in wolves]
                    if not non_wolves:
                        continue
                    ans = agents[voter].wolf_vote(non_wolves, transcript, rnd)
                    log(voter, "wolf_vote", WerewolfAgent.WOLF_VOTE_Q, ans, rnd)
                    target = ans.choice
                else:
                    dist = round_belief[voter].distribution
                    target = max(dist, key=lambda k: dist[k]) if dist else voter
                all_votes.append(Vote(rnd, voter, target))
                tally[target] += 1

            if tally:
                lynched = self._resolve_vote(tally, round_belief)
                living.discard(lynched)
                eliminated_order.append(lynched)

            if (final := winner()) is not None:
                break

        result.winner = final if final is not None else (winner() or Team.WEREWOLF)
        result.rounds_played = rounds_played
        result.players = players
        result.eliminated_order = eliminated_order
        result.night_kills = night_kills
        result.beliefs = beliefs
        result.transcript = transcript
        result.votes = all_votes
        result.decisions = decisions
        return result

    def _resolve_vote(
        self, tally: Counter[str], round_belief: dict[str, BeliefRecord]
    ) -> str:
        top = max(tally.values())
        tied = [pid for pid, v in tally.items() if v == top]
        if len(tied) == 1:
            return tied[0]

        def suspicion_mass(pid: str) -> float:
            return sum(b.distribution.get(pid, 0.0) for b in round_belief.values())

        return max(sorted(tied), key=suspicion_mass)
