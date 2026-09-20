# Contributing to Jev Board Game

Thanks for helping improve this testbed for studying calibrated belief in
social-deduction games. New games, analysis metrics, agents, and viewer
improvements are all welcome.

## Design philosophy (please preserve it)

- **Belief is a primitive, not a probe.** Each agent's suspicion comes straight
  from a Jev `Choice` probability distribution. Do not replace it with a parsed
  LLM confidence string; the whole point is that the belief is natively typed and
  calibrated.
- **Select, don't generate.** Agents pick from candidate options with Jev; they do
  not ask a model to write free text. Keep new game logic on that pattern.
- **Never fake results.** The offline backend is a deterministic stand-in so the
  project runs without an API key — it is explicitly *not* a claim about Jev's
  accuracy. Do not present offline numbers as scientific findings; calibration
  claims must come from `--backend live`.
- **Agents only see what a real player would.** Ground truth (the true role) is for
  analysis only and must never enter an agent's state.

## Development setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Quality gates (run before every PR)

```bash
ruff check .        # lint
mypy                # type-check (strict)
pytest              # tests (offline, deterministic)
```

All three must pass. New behavior needs tests; the offline backend keeps them fast
and deterministic, so prefer testing against it.

## Adding a game

Implement `SocialDeductionGame` (`src/jev_board_game/engine/game.py`) and emit a
`GameResult` that populates the shared `BeliefRecord` and `JevDecision` logs, so the
calibration harness, terminal `--watch`, and web `--web` viewers work unchanged.
`games/undercover.py` is the reference implementation; `werewolf.py` and `avalon.py`
are scaffolds describing the intended design.

## How to propose a change

1. Fork and create a branch.
2. Make the change with tests; keep `ruff`, `mypy`, and `pytest` green.
3. Add a bullet to `CHANGELOG.md` under `## [Unreleased]` if it is user-facing.
4. Open a pull request describing what changed and why.

Larger proposals (a new game, a new analysis axis) are welcome as an issue first so
we can align on scope.
