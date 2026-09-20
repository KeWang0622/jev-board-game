"""Export games to a self-contained God's-eye web viewer (single HTML file)."""

from __future__ import annotations

import json
from collections import Counter
from importlib import resources
from typing import Any

from .engine.events import GameResult

_MARKER = "/*__GAMES__*/[]"


def game_to_dict(result: GameResult, backend: str = "offline") -> dict[str, Any]:
    rounds: list[dict[str, Any]] = []
    n_rounds = max((c.round_index for c in result.transcript), default=-1) + 1
    for r in range(n_rounds):
        clues = [
            {"speaker": c.speaker_id, "text": c.text}
            for c in result.transcript
            if c.round_index == r
        ]
        beliefs = []
        for b in result.beliefs:
            if b.round_index != r:
                continue
            top = max(b.distribution, key=lambda k: b.distribution[k]) if b.distribution else ""
            beliefs.append(
                {
                    "observer": b.observer_id,
                    "distribution": b.distribution,
                    "confidence": b.confidence,
                    "top": top,
                    "top_prob": b.distribution.get(top, 0.0),
                }
            )
        votes = [
            {"voter": v.voter_id, "target": v.target_id}
            for v in result.votes
            if v.round_index == r
        ]
        tally = Counter(v["target"] for v in votes)
        eliminated = result.eliminated_order[r] if r < len(result.eliminated_order) else None
        rounds.append(
            {
                "index": r,
                "clues": clues,
                "beliefs": beliefs,
                "votes": votes,
                "tally": dict(tally),
                "eliminated": eliminated,
            }
        )

    return {
        "backend": backend,
        "winner": result.winner.value,
        "rounds_played": result.rounds_played,
        "undercover_id": result.undercover_id,
        "players": [
            {"id": p.id, "team": p.team.value, "secret": p.secret} for p in result.players
        ],
        "rounds": rounds,
    }


def render_html(games: list[dict[str, Any]]) -> str:
    template = (
        resources.files("jev_board_game.web").joinpath("viewer.html").read_text(encoding="utf-8")
    )
    payload = json.dumps(games, ensure_ascii=False)
    if _MARKER not in template:
        raise RuntimeError("viewer template is missing the games marker")
    return template.replace(_MARKER, payload)


def export_html(games: list[dict[str, Any]], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_html(games))
