"""Command-line entry point: run Undercover games and print/plot the analysis."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .experiment import sweep
from .jev.client import get_backend


def _int_list(value: str) -> list[int]:
    return [int(x) for x in value.split(",") if x.strip()]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jev-undercover",
        description="Run Undercover with Jev-backed agents and report belief calibration.",
    )
    p.add_argument("--games", type=int, default=20, help="games per configuration")
    p.add_argument(
        "--players",
        type=_int_list,
        default=[5],
        help="player count(s), comma-separated for a sweep (e.g. 4,5,6)",
    )
    p.add_argument(
        "--max-reveal",
        type=_int_list,
        default=[2],
        help="clue reveal ceiling(s) 0..2, comma-separated for a sweep",
    )
    p.add_argument("--seed", type=int, default=0, help="base RNG seed")
    p.add_argument(
        "--backend",
        choices=["auto", "offline", "live"],
        default="auto",
        help="Jev backend (auto uses live iff TYPESAFE_API_KEY is set)",
    )
    p.add_argument("--plot", metavar="PATH", help="save belief-trajectory plot (single config)")
    p.add_argument("--json", metavar="PATH", help="dump results as JSON")
    p.add_argument(
        "--watch",
        action="store_true",
        help="God's-eye view: replay ONE game round-by-round with all hidden info",
    )
    p.add_argument(
        "--web",
        metavar="PATH",
        help="write a self-contained God's-eye web viewer (HTML) with games baked in",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prefer = {"auto": None, "offline": False, "live": True}[args.backend]
    backend = get_backend(prefer_live=prefer)

    if args.watch:
        from .games.undercover import Undercover
        from .replay import narrate

        game = Undercover(
            backend=backend,
            n_players=args.players[0],
            max_reveal=args.max_reveal[0],
            seed=args.seed,
        )
        print(f"backend: {backend.name}\n")
        print(narrate(game.play()))
        return 0

    if args.web:
        from .games.undercover import Undercover
        from .webexport import export_html, game_to_dict

        n_games = max(1, args.games)
        games = [
            game_to_dict(
                Undercover(
                    backend=backend,
                    n_players=args.players[0],
                    max_reveal=args.max_reveal[0],
                    seed=args.seed + i,
                ).play(),
                backend=backend.name,
            )
            for i in range(n_games)
        ]
        export_html(games, args.web)
        print(f"backend: {backend.name}")
        print(f"baked {n_games} game(s) -> {args.web}")
        print(f"open it in a browser:  open {args.web}")
        return 0

    results = sweep(
        backend,
        player_counts=args.players,
        reveal_levels=args.max_reveal,
        games=args.games,
        base_seed=args.seed,
    )

    print(f"backend: {backend.name}\n")
    for r in results:
        print(r.summary())

    if args.plot:
        if len(results) != 1:
            print("\n--plot needs a single config (one --players and one --max-reveal)",
                  file=sys.stderr)
            return 2
        from .analysis.trajectories import plot_trajectory

        plot_trajectory(results[0].trajectory, args.plot)
        print(f"\nsaved plot -> {args.plot}")

    if args.json:
        payload = [
            {
                "config": asdict(r.config),
                "games_played": r.games_played,
                "civilian_win_rate": r.civilian_win_rate,
                "mean_rounds": r.mean_rounds,
                "calibration": asdict(r.calibration),
                "trajectory": [asdict(t) for t in r.trajectory],
            }
            for r in results
        ]
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"\nsaved results -> {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
