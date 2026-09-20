from jev_board_game.engine.events import Team
from jev_board_game.games.undercover import Undercover, load_word_pairs
from jev_board_game.jev.client import OfflineJevBackend


def test_word_pairs_load():
    pairs = load_word_pairs()
    assert pairs
    for pair in pairs:
        assert pair["civilian"] != pair["undercover"]
        assert set(pair["clues"]) == {pair["civilian"], pair["undercover"]}


def test_game_runs_and_reports_beliefs():
    game = Undercover(OfflineJevBackend(), n_players=5, seed=1)
    result = game.play()
    assert result.winner in (Team.CIVILIAN, Team.UNDERCOVER)
    assert result.rounds_played >= 1
    assert result.beliefs, "every round must log beliefs"
    for b in result.beliefs:
        assert abs(sum(b.distribution.values()) - 1.0) < 1e-6
        assert b.ground_truth_id not in b.distribution or b.observer_id != b.ground_truth_id


def test_all_jev_decisions_are_recorded():
    result = Undercover(OfflineJevBackend(), n_players=5, seed=1).play()
    assert result.decisions, "every Jev judgement must be logged"
    kinds = {d.kind for d in result.decisions}
    assert kinds == {"clue", "suspect"}
    for d in result.decisions:
        assert d.choice in d.options
        assert abs(sum(d.options.values()) - 1.0) < 1e-6
        assert d.question


def test_belief_never_includes_the_observer():
    game = Undercover(OfflineJevBackend(), n_players=6, seed=7)
    result = game.play()
    for b in result.beliefs:
        assert b.observer_id not in b.distribution


def test_reproducible_with_seed():
    a = Undercover(OfflineJevBackend(), n_players=5, seed=42).play()
    b = Undercover(OfflineJevBackend(), n_players=5, seed=42).play()
    assert a.winner == b.winner
    assert a.eliminated_order == b.eliminated_order


def test_min_players_guard():
    import pytest

    with pytest.raises(ValueError):
        Undercover(OfflineJevBackend(), n_players=2)
