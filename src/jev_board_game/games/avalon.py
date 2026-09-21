"""Avalon (The Resistance): the third fully implemented game.

Roles: an Assassin plus minions form the evil team; Merlin plus loyal servants form
the good team. Merlin and all evil players know who the evil players are.

Five quests. Each quest: the leader proposes a team, everyone votes to approve or
reject it (Jev `Noul`); five rejections in a row hand the win to evil. On an
approved quest, each evil member decides whether to fail it (Jev `Noul`). Three
successful quests take good to the brink — then the Assassin guesses Merlin
(Jev `Choice`); a correct guess steals the win for evil.

Every good player's belief over who is evil (Jev `Choice`) is logged each quest and
scored against the evil team via `BeliefRecord.ground_truth_ids`.
"""

from __future__ import annotations

import random
from typing import Any

from ..agents.avalon_agent import AvalonAgent
from ..engine.events import BeliefRecord, GameResult, JevDecision, Player, Team, Vote
from ..engine.game import SocialDeductionGame
from ..jev.client import JevBackend

_EVIL_COUNT = {5: 2, 6: 2, 7: 3, 8: 3, 9: 3, 10: 4}
_TEAM_SIZES = {
    5: [2, 3, 2, 3, 3],
    6: [2, 3, 4, 3, 4],
    7: [2, 3, 3, 4, 4],
    8: [3, 4, 4, 5, 5],
    9: [3, 4, 4, 5, 5],
    10: [3, 4, 4, 5, 5],
}
_APPROVE_THRESHOLD = 0.5
_SABOTAGE_THRESHOLD = 0.5


class Avalon(SocialDeductionGame):
    name = "avalon"

    def __init__(
        self,
        backend: JevBackend,
        n_players: int = 6,
        max_rounds: int = 5,  # ignored; Avalon is always up to 5 quests
        seed: int | None = None,
    ) -> None:
        if n_players not in _EVIL_COUNT:
            raise ValueError("Avalon supports 5–10 players")
        self.backend = backend
        self.n_players = n_players
        self.rng = random.Random(seed)

    def _build_players(self) -> list[Player]:
        ids = [f"P{i + 1}" for i in range(self.n_players)]
        self.rng.shuffle(ids)
        n_evil = _EVIL_COUNT[self.n_players]
        players: list[Player] = []
        players.append(Player(id=ids[0], team=Team.EVIL, role="assassin"))
        for pid in ids[1:n_evil]:
            players.append(Player(id=pid, team=Team.EVIL, role="minion"))
        players.append(Player(id=ids[n_evil], team=Team.GOOD, role="merlin"))
        for pid in ids[n_evil + 1 :]:
            players.append(Player(id=pid, team=Team.GOOD, role="servant"))
        players.sort(key=lambda p: int(p.id[1:]))
        return players

    def _required_fails(self, quest_index: int) -> int:
        return 2 if quest_index == 3 and self.n_players >= 7 else 1

    def play(self) -> GameResult:  # noqa: C901 - a full game loop
        players = self._build_players()
        evil = frozenset(p.id for p in players if p.team is Team.EVIL)
        merlin = next(p.id for p in players if p.role == "merlin")
        assassin = next(p.id for p in players if p.role == "assassin")
        # Merlin and every evil player know the evil set.
        agents = {
            p.id: AvalonAgent(
                p,
                self.backend,
                evil if (p.team is Team.EVIL or p.role == "merlin") else frozenset(),
            )
            for p in players
        }
        order = [p.id for p in players]

        beliefs: list[BeliefRecord] = []
        decisions: list[JevDecision] = []
        votes: list[Vote] = []
        quests: list[dict[str, Any]] = []
        history: list[str] = []
        on_teams: dict[str, int] = dict.fromkeys(order, 0)
        failed_teams: dict[str, int] = dict.fromkeys(order, 0)

        team_sizes = _TEAM_SIZES[self.n_players]
        successes = fails = 0
        leader_idx = 0
        winner = Team.EVIL

        for quest_i in range(5):
            size = team_sizes[quest_i]
            # --- belief phase: every good player reads the table ---
            self._log_beliefs(agents, players, evil, merlin, on_teams, failed_teams,
                              history, quest_i, beliefs, decisions)

            approved_team: list[str] | None = None
            approvals: dict[str, bool] = {}
            leader = order[leader_idx % len(order)]
            for _attempt in range(5):
                leader = order[leader_idx % len(order)]
                leader_idx += 1
                team = self._propose(agents[leader], leader, players, evil, on_teams,
                                     failed_teams, history, size)
                # --- approval vote ---
                yes = 0
                attempt_votes: dict[str, bool] = {}
                for pid in order:
                    read = self._team_read(agents[pid], team, players, evil, on_teams,
                                          failed_teams, history)
                    p_ok = agents[pid].approve(team, read, history)
                    ok = p_ok >= _APPROVE_THRESHOLD
                    attempt_votes[pid] = ok
                    votes.append(Vote(quest_i, pid, "approve" if ok else "reject"))
                    decisions.append(JevDecision(quest_i, pid, "approve",
                        AvalonAgent.APPROVE_Q, {"approve": p_ok, "reject": 1 - p_ok},
                        "approve" if ok else "reject", abs(p_ok - 0.5) * 2))
                    yes += int(ok)
                if yes * 2 > len(order):
                    approved_team = team
                    approvals = attempt_votes
                    history.append(f"Q{quest_i + 1}: team {team} approved ({yes}/{len(order)})")
                    break
                history.append(f"Q{quest_i + 1}: team {team} rejected ({yes}/{len(order)})")

            if approved_team is None:
                # five rejects: evil wins immediately (hammer)
                quests.append({"index": quest_i, "team": [], "approved": False,
                              "success": False, "fails": 0, "hammer": True})
                winner = Team.EVIL
                return self._finish(players, evil, merlin, beliefs, decisions, votes,
                                   quests, winner, quest_i + 1)

            # --- quest execution ---
            for pid in approved_team:
                on_teams[pid] += 1
            n_fail = 0
            for pid in approved_team:
                if pid in evil:
                    p_fail = agents[pid].sabotage(quest_i, history)
                    decisions.append(JevDecision(quest_i, pid, "sabotage",
                        AvalonAgent.SABOTAGE_Q, {"fail": p_fail, "success": 1 - p_fail},
                        "fail" if p_fail >= _SABOTAGE_THRESHOLD else "success",
                        abs(p_fail - 0.5) * 2))
                    if p_fail >= _SABOTAGE_THRESHOLD:
                        n_fail += 1
            success = n_fail < self._required_fails(quest_i)
            if not success:
                for pid in approved_team:
                    failed_teams[pid] += 1
            quests.append({"index": quest_i, "leader": leader, "team": approved_team,
                          "approved": True, "success": success, "fails": n_fail,
                          "required_fails": self._required_fails(quest_i),
                          "approvals": approvals})
            history.append(
                f"Q{quest_i + 1}: {'SUCCESS' if success else 'FAIL'} "
                f"({n_fail} fail card(s)) team={approved_team}"
            )
            successes += int(success)
            fails += int(not success)

            if fails >= 3:
                winner = Team.EVIL
                return self._finish(players, evil, merlin, beliefs, decisions, votes,
                                   quests, winner, quest_i + 1)
            if successes >= 3:
                winner = self._assassinate(agents[assassin], assassin, players, evil,
                                          merlin, history, decisions, quest_i)
                return self._finish(players, evil, merlin, beliefs, decisions, votes,
                                   quests, winner, quest_i + 1)

        winner = Team.GOOD if successes > fails else Team.EVIL
        return self._finish(players, evil, merlin, beliefs, decisions, votes, quests,
                           winner, 5)

    # ---- helpers ----
    def _candidates(self, observer: str, players: list[Player], evil: frozenset[str],
                   merlin: str, on_teams: dict[str, int],
                   failed_teams: dict[str, int]) -> dict[str, dict[str, object]]:
        knows_evil = observer in evil or observer == merlin
        cands: dict[str, dict[str, object]] = {}
        for p in players:
            if p.id == observer:
                continue
            ctx: dict[str, object] = {
                "on_teams": on_teams[p.id],
                "failed_teams": failed_teams[p.id],
            }
            if knows_evil and p.id in evil:
                ctx["known"] = "evil"
            cands[p.id] = ctx
        return cands

    def _log_beliefs(
        self,
        agents: dict[str, AvalonAgent],
        players: list[Player],
        evil: frozenset[str],
        merlin: str,
        on_teams: dict[str, int],
        failed_teams: dict[str, int],
        history: list[str],
        quest_i: int,
        beliefs: list[BeliefRecord],
        decisions: list[JevDecision],
    ) -> None:
        for p in players:
            if p.team is not Team.GOOD:
                continue  # only good players' beliefs are calibration-scored
            cands = self._candidates(p.id, players, evil, merlin, on_teams, failed_teams)
            a = agents[p.id].suspect(cands, history)
            beliefs.append(BeliefRecord(quest_i, p.id, a.distribution, "", a.confidence,
                                        ground_truth_ids=evil))
            top = max(a.distribution, key=lambda k: a.distribution[k]) if a.distribution else ""
            decisions.append(JevDecision(quest_i, p.id, "suspect", AvalonAgent.SUSPECT_Q,
                                        dict(a.distribution), top, a.confidence))

    def _propose(
        self,
        leader_agent: AvalonAgent,
        leader: str,
        players: list[Player],
        evil: frozenset[str],
        on_teams: dict[str, int],
        failed_teams: dict[str, int],
        history: list[str],
        size: int,
    ) -> list[str]:
        cands = self._candidates(leader, players, evil, merlin="", on_teams=on_teams,
                                failed_teams=failed_teams)
        belief = leader_agent.suspect(cands, history).distribution
        others = [p.id for p in players if p.id != leader]
        others.sort(key=lambda pid: belief.get(pid, 0.0))  # least suspected first
        team = [leader] + others[: size - 1]
        # An evil leader tries to sneak a fellow evil onto the team.
        if leader in evil:
            pack = [e for e in evil if e != leader]
            if pack and not any(t in evil for t in team[1:]):
                team[-1] = self.rng.choice(pack)
        return team

    def _team_read(
        self,
        agent: AvalonAgent,
        team: list[str],
        players: list[Player],
        evil: frozenset[str],
        on_teams: dict[str, int],
        failed_teams: dict[str, int],
        history: list[str],
    ) -> str:
        cands = self._candidates(agent.id, players, evil, merlin="", on_teams=on_teams,
                                failed_teams=failed_teams)
        belief = agent.suspect(cands, history).distribution
        risk = sum(belief.get(t, 0.0) for t in team if t != agent.id)
        return f"summed suspicion on this team ≈ {risk:.2f}"

    def _assassinate(
        self,
        assassin_agent: AvalonAgent,
        assassin: str,
        players: list[Player],
        evil: frozenset[str],
        merlin: str,
        history: list[str],
        decisions: list[JevDecision],
        quest_i: int,
    ) -> Team:
        good = [p.id for p in players if p.team is Team.GOOD]
        ans = assassin_agent.assassinate(good, history)
        decisions.append(JevDecision(quest_i, assassin, "assassinate",
            AvalonAgent.ASSASSIN_Q, dict(ans.probabilities), ans.choice, ans.confidence))
        history.append(f"Assassin guesses Merlin = {ans.choice}")
        return Team.EVIL if ans.choice == merlin else Team.GOOD

    def _finish(
        self,
        players: list[Player],
        evil: frozenset[str],
        merlin: str,
        beliefs: list[BeliefRecord],
        decisions: list[JevDecision],
        votes: list[Vote],
        quests: list[dict[str, Any]],
        winner: Team,
        rounds_played: int,
    ) -> GameResult:
        return GameResult(
            winner=winner,
            rounds_played=rounds_played,
            beliefs=beliefs,
            votes=votes,
            players=players,
            decisions=decisions,
            game_type="avalon",
            quests=quests,
        )
