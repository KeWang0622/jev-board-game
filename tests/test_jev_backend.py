from jev_board_game.jev.client import OfflineJevBackend
from jev_board_game.jev.types import Choice, ChoiceAnswer, Noul, NoulAnswer, Score, ScoreAnswer


def test_choice_answer_is_wellformed():
    backend = OfflineJevBackend()
    q = Choice(instructions="pick", criteria={"a": "apple", "b": "banana", "c": "cherry"})
    resp = backend.ask("i like apple", {"q": q})
    ans = resp.choice("q")
    assert isinstance(ans, ChoiceAnswer)
    assert set(ans.probabilities) == {"a", "b", "c"}
    assert abs(sum(ans.probabilities.values()) - 1.0) < 1e-9
    assert ans.choice in ans.probabilities
    assert 0.0 <= ans.confidence <= 1.0


def test_noul_and_score_shapes():
    backend = OfflineJevBackend()
    resp = backend.ask(
        "urgent please help now",
        {
            "n": Noul(instructions="is this urgent"),
            "s": Score(instructions="severity", criteria=["low", "medium", "high"]),
        },
    )
    assert isinstance(resp.noul("n"), NoulAnswer)
    assert 0.0 <= resp.noul("n").noul <= 1.0
    s = resp.score("s")
    assert isinstance(s, ScoreAnswer)
    assert abs(sum(s.probabilities) - 1.0) < 1e-9
    assert 0.0 <= s.score <= 2.0


def test_offline_is_deterministic():
    b1, b2 = OfflineJevBackend(), OfflineJevBackend()
    q = {"q": Choice(instructions="x", criteria={"a": "cat", "b": "dog", "c": "fish"})}
    a1 = b1.ask("a pet story", q).choice("q").probabilities
    a2 = b2.ask("a pet story", q).choice("q").probabilities
    assert a1 == a2


def test_offline_detects_the_outlier():
    # Two options describe the same concept; the third stands out. The outlier
    # signal should make the odd one out the most probable pick.
    backend = OfflineJevBackend()
    q = Choice(
        instructions="which stands out",
        criteria={
            "P1": "it is a warm drink you sip in the morning",
            "P2": "it is a warm drink you sip in the morning",
            "P3": "it runs on rails and carries many passengers",
        },
    )
    ans = backend.ask("group of clues about drinks", {"q": q}).choice("q")
    assert ans.choice == "P3"
