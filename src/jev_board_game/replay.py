"""God's-eye spectator view: replay one game round-by-round with all hidden info.

This reveals everything (secret words, the true spy, and every agent's suspicion)
so you can *watch* the Jev-backed agents play. It reads only a completed
``GameResult`` — no agent ever saw this extra information during play.
"""

from __future__ import annotations

import sys
from collections import Counter

from .engine.events import Clue, GameResult, Team, Vote

_BLOCKS = "▁▂▃▄▅▆▇█"


class _Style:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        return f"\x1b[{code}m{text}\x1b[0m" if self.enabled else text

    def bold(self, t: str) -> str:
        return self._wrap("1", t)

    def dim(self, t: str) -> str:
        return self._wrap("2", t)

    def green(self, t: str) -> str:
        return self._wrap("32", t)

    def red(self, t: str) -> str:
        return self._wrap("31", t)

    def yellow(self, t: str) -> str:
        return self._wrap("33", t)

    def cyan(self, t: str) -> str:
        return self._wrap("36", t)


def _bar(p: float, width: int = 12) -> str:
    filled = p * width
    full = int(filled)
    out = "█" * full
    frac = filled - full
    if full < width:
        out += _BLOCKS[min(len(_BLOCKS) - 1, int(frac * len(_BLOCKS)))]
        out += " " * (width - full - 1)
    return out[:width]


def narrate(result: GameResult, color: bool | None = None) -> str:
    s = _Style(sys.stdout.isatty() if color is None else color)
    spy = result.undercover_id
    words = {p.id: (p.secret or "?") for p in result.players}
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append(s.bold("  UNDERCOVER · 上帝视角 (God's-eye view)"))
    lines.append("=" * 60)
    lines.append(s.dim("Secret words (hidden from the players):"))
    for p in result.players:
        tag = s.red(" ← UNDERCOVER") if p.id == spy else ""
        lines.append(f"  {s.cyan(p.id)}  {words[p.id]}{tag}")
    lines.append("-" * 60)

    n_rounds = (max((c.round_index for c in result.transcript), default=-1)) + 1
    for r in range(n_rounds):
        lines.append(s.bold(f"Round {r + 1}"))
        lines.append("  Clues:")
        for c in [c for c in result.transcript if c.round_index == r]:
            who = s.red(c.speaker_id) if c.speaker_id == spy else s.cyan(c.speaker_id)
            lines.append(f'    {who}: "{c.text}"')

        round_beliefs = [b for b in result.beliefs if b.round_index == r]
        if round_beliefs:
            lines.append("  Suspicion (each agent's top guess for the spy):")
            for b in sorted(round_beliefs, key=lambda x: x.observer_id):
                if not b.distribution:
                    continue
                top = max(b.distribution, key=lambda k: b.distribution[k])
                prob = b.distribution[top]
                hit = top == spy
                mark = s.green("✓") if hit else s.dim("·")
                target = s.green(top) if hit else top
                lines.append(
                    f"    {s.cyan(b.observer_id)} → {target} {mark} "
                    f"[{_bar(prob)}] {prob:.0%}"
                )

        votes = [v for v in result.votes if v.round_index == r]
        if votes:
            tally: Counter[str] = Counter(v.target_id for v in votes)
            summary = ", ".join(f"{pid}×{n}" for pid, n in tally.most_common())
            eliminated = result.eliminated_order[r] if r < len(result.eliminated_order) else None
            line = f"  Votes: {summary}"
            if eliminated:
                verdict = (
                    s.green("was the UNDERCOVER ✓")
                    if eliminated == spy
                    else s.yellow("was a civilian ✗")
                )
                line += f"  →  {s.bold(eliminated)} eliminated ({verdict})"
            lines.append(line)
        lines.append("")

    winner = "CIVILIANS" if result.winner is Team.CIVILIAN else "UNDERCOVER"
    banner = s.green(winner) if result.winner is Team.CIVILIAN else s.red(winner)
    lines.append("=" * 60)
    lines.append(s.bold(f"Result: {banner} win in {result.rounds_played} round(s)"))
    lines.append("=" * 60)
    return "\n".join(lines)


def _fmt_clue(c: Clue) -> str:  # pragma: no cover - convenience only
    return f"[r{c.round_index}] {c.speaker_id}: {c.text}"


def _fmt_vote(v: Vote) -> str:  # pragma: no cover - convenience only
    return f"[r{v.round_index}] {v.voter_id} -> {v.target_id}"
