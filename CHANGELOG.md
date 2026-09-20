# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-09-20

Initial release.

### Added
- **Belief-as-a-primitive engine.** Game-agnostic contract with per-round
  `BeliefRecord` logging and a `JevDecision` record capturing every Jev judgement
  (kind, question, full option distribution, choice, confidence).
- **Undercover** (Who-Is-The-Spy), fully implemented: Jev-backed clue selection and
  suspicion, with a `max_reveal` knob for how revealing the clue pool is. Werewolf
  and Avalon are scaffolded on the shared contract.
- **Backend-agnostic Jev client:** a live backend (`typesafe-sdk`) and a
  deterministic offline backend so the project runs with no API key.
- **Analysis harness:** expected calibration error, Brier score, top-1 accuracy,
  reliability bins, and belief-trajectory aggregation.
- **Experiment runner + CLI** (`jev-undercover`): run and sweep configurations
  (player count × clue-revealingness), JSON export, and belief-trajectory plots.
- **God's-eye viewers:** terminal `--watch` (上帝视角) and a self-contained web
  viewer `--web` with a per-agent readout (clue, accusation, faithful derived
  reason, belief bars) and a full Jev decision log.
- **Tooling:** `pytest` suite (offline, deterministic), `ruff` lint, `mypy --strict`
  type checking, PEP 561 `py.typed` marker, and a GitHub Actions CI matrix
  (Python 3.10–3.13).
- **Docs:** README with the paper framing, `docs/related_work.md` with citations to
  prior LLM social-deduction and belief-probing work.
