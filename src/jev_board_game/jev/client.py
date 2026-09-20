"""Jev backends: a live TypeSafe SDK backend and a deterministic offline backend.

The offline backend lets the whole project run — games, experiments, tests, CI —
with no API key and no network, while producing *plausible*, deterministic belief
dynamics. Swap in the live backend to get real Jev judgements.

All backends share one interface::

    backend.ask(state, {question_id: Question, ...}) -> Response
"""

from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol, runtime_checkable

from .types import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Question,
    Response,
    Score,
    ScoreAnswer,
    State,
    Usage,
)


@runtime_checkable
class JevBackend(Protocol):
    name: str

    def ask(self, state: State, questions: dict[str, Question]) -> Response: ...


def _stable_unit(*parts: str) -> float:
    """Deterministic pseudo-random float in [0, 1) from string parts.

    Used by the offline backend so results are reproducible across runs and
    machines (unlike Python's salted ``hash``).
    """

    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big")
    return value / float(1 << 64)


def _softmax(logits: list[float]) -> list[float]:
    if not logits:
        return []
    hi = max(logits)
    exps = [math.exp(x - hi) for x in logits]
    total = sum(exps)
    return [e / total for e in exps]


def _distribution_confidence(probs: list[float]) -> float:
    """Peakedness of a distribution in [0, 1] (0 = flat/uniform, 1 = one-hot).

    Defined as ``1 - H(p) / H(uniform)`` so it matches the documented intuition:
    a flat shape is low confidence, a single peak is high confidence.
    """

    n = len(probs)
    if n <= 1:
        return 1.0
    entropy = -sum(p * math.log(p) for p in probs if p > 0.0)
    return max(0.0, min(1.0, 1.0 - entropy / math.log(n)))


def _state_text(state: object) -> str:
    if isinstance(state, str):
        return state
    if isinstance(state, dict):
        return "\n".join(f"{k}: {_state_text(v)}" for k, v in state.items())
    if isinstance(state, list | tuple):
        return "\n".join(_state_text(x) for x in state)
    return str(state)


class OfflineJevBackend:
    """Deterministic stand-in for Jev.

    It does not understand language; it produces stable, well-formed distributions
    driven by lightweight lexical-overlap heuristics between the state text and each
    option name/description. This is enough to exercise the full pipeline and to
    make the offline demo show non-trivial, reproducible belief trajectories. It is
    NOT a claim about Jev's accuracy — swap in ``LiveJevBackend`` for that.
    """

    name = "offline"

    def __init__(self, temperature: float = 0.6, seed: str = "jev-board-game") -> None:
        self.temperature = temperature
        self.seed = seed

    def ask(self, state: State, questions: dict[str, Question]) -> Response:
        text = _state_text(state).lower()
        tokens = set(_tokenize(text))
        answers: dict[str, object] = {}
        for qid, q in questions.items():
            if isinstance(q, Choice):
                answers[qid] = self._answer_choice(qid, text, tokens, q)
            elif isinstance(q, Noul):
                answers[qid] = self._answer_noul(qid, tokens, q)
            elif isinstance(q, Score):
                answers[qid] = self._answer_score(qid, tokens, q)
            else:  # pragma: no cover - exhaustive by construction
                raise TypeError(f"unknown question type: {type(q)!r}")
        return Response(answers=answers, model="offline", usage=Usage())  # type: ignore[arg-type]

    def _affinity(self, qid: str, key: str, desc: str | None, tokens: set[str]) -> float:
        target = _tokenize(f"{key} {desc or ''}")
        overlap = sum(1 for t in target if t in tokens)
        base = overlap / (1.0 + len(target))
        jitter = _stable_unit(self.seed, qid, key) * 0.5
        return (base + jitter) / max(self.temperature, 1e-6)

    def _answer_choice(
        self, qid: str, text: str, tokens: set[str], q: Choice
    ) -> ChoiceAnswer:
        options = list(q.criteria.items())
        # Base term: how well each option matches the shared state.
        base = [self._affinity(qid, key, desc, tokens) for key, desc in options]
        # Generic outlier term: options whose description stands out from the
        # others are boosted. This is game-agnostic but happens to be exactly the
        # odd-one-out signal social deduction needs, so the offline demo produces
        # non-trivial (not random) suspicion. It is NOT a claim about Jev.
        outlier = _outlier_scores([desc or key for key, desc in options])
        logits = [b + 1.5 * o for b, o in zip(base, outlier, strict=True)]
        probs = _softmax(logits)
        dist = {key: p for (key, _), p in zip(options, probs, strict=True)}
        best = max(dist, key=lambda k: dist[k])
        return ChoiceAnswer(
            choice=best,
            probabilities=dist,
            confidence=_distribution_confidence(list(dist.values())),
        )

    def _answer_noul(self, qid: str, tokens: set[str], q: Noul) -> NoulAnswer:
        cues = _tokenize(q.instructions)
        overlap = sum(1 for t in cues if t in tokens)
        base = overlap / (1.0 + len(cues))
        jitter = _stable_unit(self.seed, qid, "noul") - 0.5
        logit = 4.0 * (base - 0.25) + jitter
        return NoulAnswer(noul=1.0 / (1.0 + math.exp(-logit)))

    def _answer_score(self, qid: str, tokens: set[str], q: Score) -> ScoreAnswer:
        levels = q.criteria
        logits = [
            self._affinity(qid, f"level{i}", level, tokens)
            for i, level in enumerate(levels)
        ]
        probs = _softmax(logits)
        expected = sum(i * p for i, p in enumerate(probs))
        return ScoreAnswer(
            score=expected,
            probabilities=probs,
            confidence=_distribution_confidence(probs),
        )


class LiveJevBackend:
    """Live backend backed by the official ``typesafe-sdk``.

    Import and construction are lazy so the package works without the optional
    dependency installed. Requires ``TYPESAFE_API_KEY`` in the environment.
    """

    name = "live"

    def __init__(self, model: str | None = None) -> None:
        try:
            import typesafe_sdk  # noqa: F401
        except ImportError as exc:  # pragma: no cover - exercised only when missing
            raise RuntimeError(
                "The live Jev backend needs the optional dependency. "
                "Install it with: pip install 'jev-board-game[live]'"
            ) from exc
        if not os.environ.get("TYPESAFE_API_KEY"):
            raise RuntimeError(
                "TYPESAFE_API_KEY is not set. Copy .env.example to .env and fill it in, "
                "or use the offline backend."
            )
        self.model = model or os.environ.get("JEV_MODEL", "jev-latest")

    def ask(self, state: State, questions: dict[str, Question]) -> Response:
        from typesafe_sdk import Choice as SdkChoice
        from typesafe_sdk import Noul as SdkNoul
        from typesafe_sdk import Score as SdkScore
        from typesafe_sdk import TypeSafeClient

        sdk_questions: dict[str, object] = {}
        for qid, q in questions.items():
            if isinstance(q, Choice):
                sdk_questions[qid] = SdkChoice(instructions=q.instructions, criteria=q.criteria)
            elif isinstance(q, Noul):
                sdk_questions[qid] = SdkNoul(instructions=q.instructions, criteria=q.criteria)
            elif isinstance(q, Score):
                sdk_questions[qid] = SdkScore(instructions=q.instructions, criteria=q.criteria)
            else:  # pragma: no cover
                raise TypeError(f"unknown question type: {type(q)!r}")

        with TypeSafeClient() as client:
            raw = client.system_one(state=state, model=self.model, questions=sdk_questions)

        answers: dict[str, object] = {}
        for qid, q in questions.items():
            if isinstance(q, Choice):
                a = raw.choices[qid]
                answers[qid] = ChoiceAnswer(
                    choice=a.choice,
                    probabilities=dict(a.probabilities),
                    confidence=a.confidence,
                )
            elif isinstance(q, Noul):
                answers[qid] = NoulAnswer(noul=raw.nouls[qid].noul)
            elif isinstance(q, Score):
                a = raw.scores[qid]
                answers[qid] = ScoreAnswer(
                    score=a.score,
                    probabilities=list(a.probabilities),
                    confidence=a.confidence,
                )

        usage = getattr(raw, "usage", None)
        return Response(
            answers=answers,  # type: ignore[arg-type]
            model=getattr(raw, "model", self.model),
            usage=Usage(
                input_tokens=getattr(usage, "input_tokens", 0),
                output_tokens=getattr(usage, "output_tokens", 0),
            ),
        )


def _tokenize(text: str) -> list[str]:
    return [t for t in "".join(c if c.isalnum() else " " for c in text.lower()).split() if t]


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _outlier_scores(descriptions: list[str]) -> list[float]:
    """Per-item outlier score in [0, 1]: 1 - mean Jaccard similarity to the others.

    An item whose tokens overlap little with the rest scores high (it stands out).
    Returns zeros when there is nothing to compare against.
    """

    token_sets = [set(_tokenize(d)) for d in descriptions]
    n = len(token_sets)
    if n <= 1:
        return [0.0] * n
    scores: list[float] = []
    for i, ti in enumerate(token_sets):
        sims = [_jaccard(ti, tj) for j, tj in enumerate(token_sets) if j != i]
        scores.append(1.0 - (sum(sims) / len(sims)))
    return scores


def get_backend(prefer_live: bool | None = None, **kwargs: object) -> JevBackend:
    """Return a backend, defaulting to live iff a key is present.

    Set ``prefer_live=True`` to require live (raises if unavailable), or ``False``
    to force offline.
    """

    if prefer_live is False:
        return OfflineJevBackend(**kwargs)  # type: ignore[arg-type]
    has_key = bool(os.environ.get("TYPESAFE_API_KEY"))
    if prefer_live is True or has_key:
        try:
            return LiveJevBackend()
        except RuntimeError:
            if prefer_live is True:
                raise
    return OfflineJevBackend(**kwargs)  # type: ignore[arg-type]
