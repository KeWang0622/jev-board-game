"""Export games to a self-contained God's-eye web viewer (single HTML file).

Serializes both Undercover and Werewolf into one round-structured JSON the viewer
renders. ``hidden_team`` lists the adversary ids (the undercover holder, or the
werewolf pack); ``rationale`` on each belief is a faithful, template-generated
explanation of a Jev distribution (never a generated one).
"""

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
    hidden_team: set[str],
    seer_known: dict[str, str],
    n_alive: int,
) -> dict[str, Any]:
    """Faithful, template-generated explanation of a Jev belief (no invented prose)."""

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

    if top in seer_known:
        text = (
            "confirmed by your inspection to be a werewolf"
            if seer_known[top] == "werewolf"
            else "you cleared them, but they still top the read"
        )
    elif strength == "weak" or margin < 0.05:
        text = "hard to read — unsure, slight lean to " + top
    else:
        clue = clues_by_speaker.get(top)
        text = f'“{clue}” stands out' if clue else f"{top} stands out from the group"
    return {"guess": top, "strength": strength, "text": text}


def _round_dict(result: GameResult, r: int, hidden_team: set[str]) -> dict[str, Any]:
    clues = [
        {"speaker": c.speaker_id, "text": c.text}
        for c in result.transcript
        if c.round_index == r
    ]
    clues_by_speaker = {c["speaker"]: c["text"] for c in clues}
    n_alive = len(clues) if clues else len(result.players)

    # Seer knowledge visible to the seer up to and including this round (werewolf).
    seer_known: dict[str, str] = {}
    for d in result.decisions:
        if d.kind == "seer_inspect" and d.round_index <= r:
            seer_known[d.choice] = "werewolf" if d.choice in hidden_team else "town"

    beliefs = []
    for b in result.beliefs:
        if b.round_index != r:
            continue
        top = max(b.distribution, key=lambda k: b.distribution[k]) if b.distribution else ""
        # Only the seer's own belief should surface inspection-based rationale.
        known_for_observer = seer_known if _is_seer(result, b.observer_id) else {}
        beliefs.append(
            {
                "observer": b.observer_id,
                "own_clue": clues_by_speaker.get(b.observer_id, ""),
                "distribution": b.distribution,
                "confidence": b.confidence,
                "top": top,
                "top_prob": b.distribution.get(top, 0.0),
                "rationale": _rationale(
                    b.distribution, clues_by_speaker, hidden_team, known_for_observer, n_alive
                ),
            }
        )

    votes = [
        {"voter": v.voter_id, "target": v.target_id}
        for v in result.votes
        if v.round_index == r
    ]
    tally = Counter(v["target"] for v in votes)
    eliminated = result.eliminated_order[r] if r < len(result.eliminated_order) else None
    decisions = [
        {
            "agent": d.agent_id,
            "kind": d.kind,
            "question": d.question,
            "options": d.options,
            "choice": d.choice,
            "confidence": d.confidence,
        }
        for d in result.decisions
        if d.round_index == r
    ]

    round_dict: dict[str, Any] = {
        "index": r,
        "clues": clues,
        "beliefs": beliefs,
        "votes": votes,
        "tally": dict(tally),
        "eliminated": eliminated,
        "decisions": decisions,
    }
    if result.game_type == "werewolf":
        round_dict["night_victim"] = (
            result.night_kills[r] if r < len(result.night_kills) else ""
        )
        inspect = next(
            (d for d in result.decisions if d.round_index == r and d.kind == "seer_inspect"),
            None,
        )
        if inspect:
            round_dict["seer_inspect"] = {
                "seer": inspect.agent_id,
                "target": inspect.choice,
                "result": "werewolf" if inspect.choice in hidden_team else "town",
            }
    return round_dict


def _is_seer(result: GameResult, pid: str) -> bool:
    return any(p.id == pid and p.role == "seer" for p in result.players)


def game_to_dict(result: GameResult, backend: str = "offline") -> dict[str, Any]:
    hidden_team = set(result.hidden_team())
    n_rounds = max((c.round_index for c in result.transcript), default=-1) + 1
    n_rounds = max(n_rounds, len(result.night_kills))
    rounds = [_round_dict(result, r, hidden_team) for r in range(n_rounds)]

    return {
        "game_type": result.game_type,
        "backend": backend,
        "winner": result.winner.value,
        "rounds_played": result.rounds_played,
        "n_decisions": len(result.decisions),
        "undercover_id": result.undercover_id,
        "hidden_team": sorted(hidden_team),
        "players": [
            {"id": p.id, "team": p.team.value, "role": p.role, "secret": p.secret}
            for p in result.players
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
