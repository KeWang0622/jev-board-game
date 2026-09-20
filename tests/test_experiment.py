from jev_board_game.experiment import ExperimentConfig, run_experiment, sweep
from jev_board_game.jev.client import OfflineJevBackend


def test_run_experiment_aggregates():
    backend = OfflineJevBackend()
    result = run_experiment(backend, ExperimentConfig(n_players=5, max_reveal=2, games=5))
    assert result.games_played == 5
    assert 0.0 <= result.civilian_win_rate <= 1.0
    assert result.mean_rounds >= 1.0
    assert result.calibration.n_records > 0
    assert result.trajectory


def test_sweep_covers_grid():
    backend = OfflineJevBackend()
    results = sweep(backend, player_counts=[4, 5], reveal_levels=[0, 2], games=3)
    assert len(results) == 4
    labels = {r.config.label() for r in results}
    assert "players=4,max_reveal=0" in labels
    assert "players=5,max_reveal=2" in labels
