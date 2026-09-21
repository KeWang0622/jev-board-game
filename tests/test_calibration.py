import numpy as np

from jev_board_game.analysis.calibration import (
    analyze,
    brier_score,
    expected_calibration_error,
    top1_accuracy,
)
from jev_board_game.engine.events import BeliefRecord


def _record(dist, truth, rnd=0, obs="P1", conf=0.5):
    return BeliefRecord(rnd, obs, dist, truth, conf)


def test_perfect_belief_has_zero_brier_and_full_accuracy():
    recs = [_record({"P2": 1.0, "P3": 0.0}, "P2")]
    assert brier_score(recs) == 0.0
    assert top1_accuracy(recs) == 1.0
    assert recs[0].mass_on_truth() == 1.0


def test_uniform_belief_accuracy_and_mass():
    recs = [_record({"P2": 0.5, "P3": 0.5}, "P2")]
    # argmax ties -> max() picks first max encountered; mass on truth is 0.5
    assert recs[0].mass_on_truth() == 0.5
    assert 0.0 <= top1_accuracy(recs) <= 1.0


def test_ece_bounds_and_monotonic_intuition():
    preds = np.array([0.9, 0.8, 0.1, 0.2])
    labels = np.array([1.0, 1.0, 0.0, 0.0])
    ece, bins = expected_calibration_error(preds, labels, n_bins=10)
    assert 0.0 <= ece <= 1.0
    assert bins


def test_analyze_report_fields():
    recs = [
        _record({"P2": 0.7, "P3": 0.3}, "P2"),
        _record({"P2": 0.4, "P3": 0.6}, "P3", obs="P4"),
    ]
    report = analyze(recs)
    assert report.n_records == 2
    assert report.n_binary == 4
    assert 0.0 <= report.top1_accuracy <= 1.0
    assert 0.0 <= report.ece <= 1.0
    assert "ECE" in report.summary()


def test_multi_member_ground_truth_set():
    # Werewolf-style: two hidden members; mass_on_truth sums over the set.
    rec = BeliefRecord(0, "P1", {"P2": 0.4, "P3": 0.35, "P4": 0.25}, "", 0.3,
                       ground_truth_ids=frozenset({"P2", "P3"}))
    assert abs(rec.mass_on_truth() - 0.75) < 1e-9
    report = analyze([rec])
    assert report.top1_accuracy == 1.0  # top pick P2 is a wolf


def test_empty_input_is_safe():
    report = analyze([])
    assert report.n_records == 0
    assert report.brier == 0.0
    assert report.ece == 0.0
