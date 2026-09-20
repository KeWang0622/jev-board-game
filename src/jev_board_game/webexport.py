"""Export games to a self-contained God's-eye web viewer (single HTML file)."""

from __future__ import annotations

import json
from collections import Counter
from importlib import resources
from typing import Any

from .engine.events import GameResult

_MARKER = "/*__GAMES__*/[]"


def _rationale(
    distribution: dict[str, float],
    clues_by_speaker: dict[str, str],
    n_alive: int,
) -> dict[str, Any]:
    """A faithful, template-generated explanation of a Jev belief.

    Jev returns probabilities, not prose, so this is derived *only* from the
    distribution and the clues — it never invents a reason the numbers don't
    support. It reports the accusation, its strength relative to a uniform guess,
    and (when the belief is decisive) the clue that drove it.
    """

    if not distribution:
        return {"guess": "", "strength": "none", "text": "no one else to assess yet"}
    ordered = sorted(distribution.items(), key=lambda kv: kv[1], reverse=True)
    top, p1 = ordered[0]
    p2 = ordered[1][1] if len(ordered) > 1 else 0.0
    uniform = 1.0 / max(1, n_alive - 1)
    margin = p1 - p2

    if p1 >= 2.0 * uniform:
        strength = "strong"
    elif p1 >= 1.3 * uniform:
        strength = "moderate"
    else:
        strength = "weak"

    if strength == "weak" or margin < 0.05:
        text = "everyone sounds alike — unsure, slight lean to " + top
    else:
        clue = clues_by_speaker.get(top)
        text = (
            f'“{clue}” fits the group least' if clue else f"{top}'s clues stand out from the group"
        )
    return {"guess": top, "strength": strength, "text": text}


def game_to_dict(result: GameResult, backend: str = "offline") -> dict[str, Any]:
    rounds: list[dict[str, Any]] = []
    n_rounds = max((c.round_index for c in result.transcript), default=-1) + 1
    for r in range(n_rounds):
        clues = [
            {"speaker": c.speaker_id, "text": c.text}
            for c in result.transcript
            if c.round_index == r
        ]
        clues_by_speaker = {c["speaker"]: c["text"] for c in clues}
        n_alive = len(clues)
        beliefs = []
        for b in result.beliefs:
            if b.round_index != r:
                continue
            top = max(b.distribution, key=lambda k: b.distribution[k]) if b.distribution else ""
            beliefs.append(
                {
                    "observer": b.observer_id,
                    "own_clue": clues_by_speaker.get(b.observer_id, ""),
                    "distribution": b.distribution,
                    "confidence": b.confidence,
                    "top": top,
                    "top_prob": b.distribution.get(top, 0.0),
                    "rationale": _rationale(b.distribution, clues_by_speaker, n_alive),
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
