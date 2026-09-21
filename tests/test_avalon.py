import pytest

from jev_board_game.engine.events import Team
from jev_board_game.games.avalon import Avalon
from jev_board_game.jev.client import OfflineJevBackend


def test_game_runs_and_has_structure():
    result = Avalon(OfflineJevBackend(), n_players=6, seed=1).play()
    assert result.winner in (Team.GOOD, Team.EVIL)
    assert result.game_type == "avalon"
    assert result.quests
    kinds = {d.kind for d in result.decisions}
    assert {"suspect", "approve"} <= kinds


def test_roles_and_evil_count():
    result = Avalon(OfflineJevBackend(), n_players=7, seed=2).play()
    roles = [p.role for p in result.players]
    assert roles.count("merlin") == 1
    assert roles.count("assassin") == 1
    evil = [p for p in result.players if p.team is Team.EVIL]
    assert len(evil) == 3  # 7 players -> 3 evil


def test_beliefs_target_evil_and_exclude_evil_observers():
    result = Avalon(OfflineJevBackend(), n_players=6, seed=1).play()
    evil = {p.id for p in result.players if p.team is Team.EVIL}
    assert result.beliefs
    for b in result.beliefs:
        assert b.observer_id not in evil  # only good players' beliefs are logged
        assert b.truths() == frozenset(evil)
        assert abs(sum(b.distribution.values()) - 1.0) < 1e-6


def test_assassin_path_exercised():
    # seed 5 reaches 3 good quests and triggers the Assassin's Merlin guess.
    result = Avalon(OfflineJevBackend(), n_players=6, seed=5).play()
    assert any(d.kind == "assassinate" for d in result.decisions)


def test_reproducible_with_seed():
    a = Avalon(OfflineJevBackend(), n_players=6, seed=3).play()
    b = Avalon(OfflineJevBackend(), n_players=6, seed=3).play()
    assert a.winner == b.winner
    assert [q.get("team") for q in a.quests] == [q.get("team") for q in b.quests]


def test_player_count_guard():
    with pytest.raises(ValueError):
        Avalon(OfflineJevBackend(), n_players=4)
    with pytest.raises(ValueError):
        Avalon(OfflineJevBackend(), n_players=11)
