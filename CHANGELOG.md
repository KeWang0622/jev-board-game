# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Werewolf** fully implemented: werewolves, a seer, and villagers over a
  night/day cycle — night kill (combined across the wolf pack), seer inspection,
  day statements, town suspicion, and voting, all via Jev `Choice`. Town suspicion
  is scored against the whole wolf pack.
- Engine generalized for multi-role games: `Player.role`, `Team.TOWN`/`WEREWOLF`,
  and `BeliefRecord.ground_truth_ids` (a hidden team, not just one holder);
  calibration/Brier/accuracy score against the set.
- Web and terminal God's-eye viewers now render Werewolf (roles, night phase,
  kills, seer inspections) as well as Undercover; the CLI takes `--game werewolf`
  and `--werewolves N`.

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
