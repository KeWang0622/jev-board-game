"""Build docs/index.html: a self-contained God's-eye viewer with sample games from
all three games baked in, for GitHub Pages.

Usage: python scripts/build_pages.py [--backend offline|live]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from jev_board_game.games.avalon import Avalon
from jev_board_game.games.undercover import Undercover
from jev_board_game.games.werewolf import Werewolf
from jev_board_game.jev.client import get_backend
from jev_board_game.webexport import game_to_dict, render_html


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["auto", "offline", "live"], default="offline")
    ap.add_argument("--out", default="docs/index.html")
    args = ap.parse_args()
    prefer = {"auto": None, "offline": False, "live": True}[args.backend]
    backend = get_backend(prefer_live=prefer)

    games = []
    for seed in (1, 3, 7):
        games.append(game_to_dict(Undercover(backend, n_players=5, seed=seed).play(), backend.name))
    for seed in (2, 4, 11):
        games.append(game_to_dict(Werewolf(backend, n_players=6, seed=seed).play(), backend.name))
    for seed in (5, 12):
        games.append(game_to_dict(Avalon(backend, n_players=6, seed=seed).play(), backend.name))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(games), encoding="utf-8")
    print(f"backend: {backend.name} · baked {len(games)} games -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
