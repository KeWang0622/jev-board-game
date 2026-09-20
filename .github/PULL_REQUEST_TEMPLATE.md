<!-- Thanks for contributing! Keep the design philosophy in CONTRIBUTING.md:
belief is a primitive (not a parsed LLM string), select-don't-generate, and never
present offline numbers as scientific results. -->

## What & why
Briefly, what does this change and why?

## Checklist
- [ ] `ruff check .`, `mypy`, and `pytest` all pass.
- [ ] New behavior has tests (prefer the deterministic offline backend).
- [ ] Agents still only see what a real player would (no ground-truth leakage).
- [ ] Belief still comes from a Jev distribution, not a parsed confidence string.
- [ ] Updated `CHANGELOG.md` under `## [Unreleased]` if user-facing.
