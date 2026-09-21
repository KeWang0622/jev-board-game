"""Command-line entry point: run a game with Jev-backed agents and report analysis."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .engine.events import GameResult, Team
from .engine.game import SocialDeductionGame
from .jev.client import JevBackend, get_backend


def _int_list(value: str) -> list[int]:
    return [int(x) for x in value.split(",") if x.strip()]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jev-undercover",
        description="Run a social-deduction game with Jev agents and report belief calibration.",
    )
    p.add_argument(
        "--game",
        choices=["undercover", "werewolf", "avalon"],
        default="undercover",
        help="which game to run",
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
        help="[undercover] clue reveal ceiling(s) 0..2, comma-separated for a sweep",
    )
    p.add_argument(
        "--werewolves", type=int, default=1, help="[werewolf] number of werewolves"
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


def _build_game(
    args: argparse.Namespace, backend: JevBackend, seed: int
) -> SocialDeductionGame:
    if args.game == "werewolf":
        from .games.werewolf import Werewolf

        return Werewolf(
            backend=backend,
            n_players=args.players[0],
            n_werewolves=args.werewolves,
            seed=seed,
        )
    if args.game == "avalon":
        from .games.avalon import Avalon

        return Avalon(backend=backend, n_players=args.players[0], seed=seed)
    from .games.undercover import Undercover

    return Undercover(
        backend=backend,
        n_players=args.players[0],
        max_reveal=args.max_reveal[0],
        seed=seed,
    )


def _run_stats(args: argparse.Namespace, backend: JevBackend) -> int:
    if args.game == "undercover":
        from .experiment import sweep

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
                print("\n--plot needs a single config", file=sys.stderr)
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

    # werewolf / avalon stats
    from .analysis.calibration import analyze

    games: list[GameResult] = [
        _build_game(args, backend, args.seed + i).play() for i in range(args.games)
    ]
    beliefs = [b for g in games for b in g.beliefs]
    good = sum(1 for g in games if g.winner in (Team.TOWN, Team.GOOD))
    mean_rounds = sum(g.rounds_played for g in games) / len(games) if games else 0.0
    report = analyze(beliefs)
    cfg = (
        f"wolves={args.werewolves}" if args.game == "werewolf" else f"n={args.players[0]}"
    )
    print(f"backend: {backend.name}\n")
    print(
        f"[{args.game} players={args.players[0]},{cfg}] games={len(games)} "
        f"good_win_rate={good / len(games):.3f} mean_rounds={mean_rounds:.2f} | {report.summary()}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prefer = {"auto": None, "offline": False, "live": True}[args.backend]
    backend = get_backend(prefer_live=prefer)

    if args.watch:
        from .replay import narrate

        print(f"backend: {backend.name}\n")
        print(narrate(_build_game(args, backend, args.seed).play()))
        return 0

    if args.web:
        if args.game == "avalon":
            print(
                "The web viewer does not support Avalon yet — use --watch for the "
                "terminal God's-eye view.",
                file=sys.stderr,
            )
            return 2
        from .webexport import export_html, game_to_dict

        n_games = max(1, args.games)
        games = [
            game_to_dict(_build_game(args, backend, args.seed + i).play(), backend=backend.name)
            for i in range(n_games)
        ]
        export_html(games, args.web)
        print(f"backend: {backend.name}")
        print(f"baked {n_games} {args.game} game(s) -> {args.web}")
        print(f"open it in a browser:  open {args.web}")
        return 0

    return _run_stats(args, backend)


if __name__ == "__main__":
    raise SystemExit(main())
