import json
import re

from jev_board_game.games.undercover import Undercover
from jev_board_game.jev.client import OfflineJevBackend
from jev_board_game.webexport import game_to_dict, render_html


def test_game_to_dict_shape():
    result = Undercover(OfflineJevBackend(), n_players=5, seed=3).play()
    d = game_to_dict(result, backend="offline")
    assert d["winner"] in ("civilian", "undercover")
    assert len(d["players"]) == 5
    assert d["undercover_id"]
    assert d["rounds"]
    r0 = d["rounds"][0]
    assert r0["clues"] and r0["beliefs"] and "tally" in r0
    for b in r0["beliefs"]:
        assert abs(sum(b["distribution"].values()) - 1.0) < 1e-6
        assert b["top"] in b["distribution"] or not b["distribution"]


def test_render_html_injects_valid_json():
    games = [
        game_to_dict(Undercover(OfflineJevBackend(), n_players=5, seed=i).play())
        for i in range(3)
    ]
    html = render_html(games)
    assert "__GAMES__" not in html  # marker consumed
    assert "上帝视角" in html
    # the baked payload must be valid JSON
    m = re.search(r"const GAMES = (\[.*?\]);", html, re.S)
    assert m, "GAMES payload not found"
    parsed = json.loads(m.group(1))
    assert len(parsed) == 3
