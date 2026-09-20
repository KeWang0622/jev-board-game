"""Backend-agnostic question and answer types for Jev (TypeSafe System One).

These wrap the concepts documented at https://docs.typesafe.ai/primitives so the
rest of the codebase never depends on a specific backend (live SDK vs. offline
mock). A backend consumes a ``state`` plus a mapping of question id -> Question
and returns a mapping of the same ids -> Answer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

State = str | Mapping[str, object] | Sequence[object]
"""Jev state is text only: a string, a JSON-like object, or a list of text values.

See https://docs.typesafe.ai/concepts/state — images/audio/video are not supported.
"""


@dataclass(frozen=True)
class Choice:
    """Pick exactly one option from a defined set.

    ``criteria`` maps option name -> human-readable description (or ``None`` when
    the name is self-explanatory). The answer's ``probabilities`` distribution over
    these options is what we treat as a calibrated *belief*.
    """

    instructions: str
    criteria: dict[str, str | None]


@dataclass(frozen=True)
class Noul:
    """A yes/no judgement returned as the probability that the answer is yes."""

    instructions: str
    criteria: dict[str, str] | None = None


@dataclass(frozen=True)
class Score:
    """A position along an ordered set of described levels (low -> high)."""

    instructions: str
    criteria: list[str]


Question = Choice | Noul | Score


@dataclass(frozen=True)
class ChoiceAnswer:
    choice: str
    probabilities: dict[str, float]
    confidence: float


@dataclass(frozen=True)
class NoulAnswer:
    noul: float  # probability of "yes" in [0, 1]


@dataclass(frozen=True)
class ScoreAnswer:
    score: float
    probabilities: list[float]
    confidence: float


Answer = ChoiceAnswer | NoulAnswer | ScoreAnswer


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class Response:
    answers: dict[str, Answer]
    model: str
    usage: Usage = field(default_factory=Usage)

    def choice(self, question_id: str) -> ChoiceAnswer:
        answer = self.answers[question_id]
        if not isinstance(answer, ChoiceAnswer):
            raise TypeError(f"question {question_id!r} did not return a choice answer")
        return answer

    def noul(self, question_id: str) -> NoulAnswer:
        answer = self.answers[question_id]
        if not isinstance(answer, NoulAnswer):
            raise TypeError(f"question {question_id!r} did not return a noul answer")
        return answer

    def score(self, question_id: str) -> ScoreAnswer:
        answer = self.answers[question_id]
        if not isinstance(answer, ScoreAnswer):
            raise TypeError(f"question {question_id!r} did not return a score answer")
        return answer
