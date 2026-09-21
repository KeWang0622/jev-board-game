"""Cross-game calibration benchmark: run Undercover, Werewolf, and Avalon and
report how well each game's Jev beliefs are calibrated against ground truth.

Runs on the offline backend by default; pass --backend live (with TYPESAFE_API_KEY)
for the real Jev result. Optionally dump JSON with --json.

Usage:
    python scripts/benchmark.py --games 50
    python scripts/benchmark.py --backend live --games 50 --json runs/bench.json
"""

from __future__ import annotations

import argparse
import json

from jev_board_game.analysis.calibration import analyze
from jev_board_game.engine.events import GameResult, Team
from jev_board_game.games.avalon import Avalon
from jev_board_game.games.undercover import Undercover
from jev_board_game.games.werewolf import Werewolf
from jev_board_game.jev.client import get_backend


def _run(name: str, factory, games: int, seed0: int) -> dict:
    results: list[GameResult] = [factory(seed0 + i).play() for i in range(games)]
    beliefs = [b for g in results for b in g.beliefs]
    good = sum(
        1 for g in results if g.winner in (Team.CIVILIAN, Team.TOWN, Team.GOOD)
    )
    rep = analyze(beliefs)
    return {
        "game": name,
        "games": games,
        "good_win_rate": good / games if games else 0.0,
        "belief_records": rep.n_records,
        "top1_accuracy": rep.top1_accuracy,
        "mass_on_truth": rep.mean_mass_on_truth,
        "brier": rep.brier,
        "ece": rep.ece,
        "n_decisions": sum(len(g.decisions) for g in results),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["auto", "offline", "live"], default="offline")
    ap.add_argument("--games", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", metavar="PATH")
    args = ap.parse_args()
    prefer = {"auto": None, "offline": False, "live": True}[args.backend]
    backend = get_backend(prefer_live=prefer)

    g, s0 = args.games, args.seed
    rows = [
        _run("undercover", lambda s: Undercover(backend, n_players=5, seed=s), g, s0),
        _run("werewolf", lambda s: Werewolf(backend, n_players=6, seed=s), g, s0),
        _run("avalon", lambda s: Avalon(backend, n_players=6, seed=s), g, s0),
    ]

    print(f"backend: {backend.name}\n")
    hdr = f"{'game':<12}{'good_win':>9}{'top1':>7}{'mass':>7}{'brier':>8}{'ece':>7}{'beliefs':>9}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(
            f"{r['game']:<12}{r['good_win_rate']:>9.3f}{r['top1_accuracy']:>7.3f}"
            f"{r['mass_on_truth']:>7.3f}{r['brier']:>8.4f}{r['ece']:>7.4f}{r['belief_records']:>9}"
        )
    if backend.name == "offline":
        print("\nNote: offline backend is a deterministic stand-in, not a claim about "
              "Jev's accuracy. Run --backend live for the real result.")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"backend": backend.name, "rows": rows}, fh, indent=2)
        print(f"\nsaved -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
