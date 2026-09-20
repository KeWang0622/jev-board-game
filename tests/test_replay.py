from jev_board_game.games.undercover import Undercover
from jev_board_game.jev.client import OfflineJevBackend
from jev_board_game.replay import narrate


def test_narrate_contains_god_view_sections():
    result = Undercover(OfflineJevBackend(), n_players=5, seed=3).play()
    text = narrate(result, color=False)
    assert "God's-eye view" in text
    assert "UNDERCOVER" in text
    assert "Round 1" in text
    assert "Suspicion" in text
    assert "Result:" in text
    # the true spy must be labelled in the reveal
    assert result.undercover_id in text


def test_narrate_no_ansi_when_color_disabled():
    result = Undercover(OfflineJevBackend(), n_players=4, seed=1).play()
    text = narrate(result, color=False)
    assert "\x1b[" not in text
