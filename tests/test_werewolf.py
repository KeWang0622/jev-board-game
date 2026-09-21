import pytest

from jev_board_game.engine.events import Team
from jev_board_game.games.werewolf import Werewolf
from jev_board_game.jev.client import OfflineJevBackend


def test_game_runs_and_has_expected_structure():
    result = Werewolf(OfflineJevBackend(), n_players=6, n_werewolves=1, seed=4).play()
    assert result.winner in (Team.TOWN, Team.WEREWOLF)
    assert result.game_type == "werewolf"
    assert result.rounds_played >= 1
    assert result.night_kills  # at least one night resolved
    kinds = {d.kind for d in result.decisions}
    assert {"night_kill", "seer_inspect", "statement", "suspect"} <= kinds


def test_beliefs_target_the_wolf_pack_and_exclude_wolves():
    result = Werewolf(OfflineJevBackend(), n_players=7, n_werewolves=2, seed=1).play()
    wolves = {p.id for p in result.players if p.team is Team.WEREWOLF}
    assert result.beliefs
    for b in result.beliefs:
        assert b.observer_id not in wolves  # only town forms beliefs
        assert b.truths() == frozenset(wolves)
        assert abs(sum(b.distribution.values()) - 1.0) < 1e-6
        assert b.observer_id not in b.distribution


def test_roles_assigned_once():
    result = Werewolf(OfflineJevBackend(), n_players=6, n_werewolves=1, seed=2).play()
    roles = [p.role for p in result.players]
    assert roles.count("werewolf") == 1
    assert roles.count("seer") == 1
    assert roles.count("villager") == 4


def test_reproducible_with_seed():
    a = Werewolf(OfflineJevBackend(), n_players=6, seed=9).play()
    b = Werewolf(OfflineJevBackend(), n_players=6, seed=9).play()
    assert a.winner == b.winner
    assert a.eliminated_order == b.eliminated_order
    assert a.night_kills == b.night_kills


def test_player_guards():
    with pytest.raises(ValueError):
        Werewolf(OfflineJevBackend(), n_players=3, n_werewolves=1)
    with pytest.raises(ValueError):
        Werewolf(OfflineJevBackend(), n_players=6, n_werewolves=0)
