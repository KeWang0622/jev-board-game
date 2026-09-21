# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-09-20

Initial release: three social-deduction games instrumented with a calibrated
System-One model (Jev), a God's-eye web + terminal viewer, and a calibration harness.

### Added
- **Belief-as-a-primitive engine.** Game-agnostic contract with per-round
  `BeliefRecord` logging, a `JevDecision` record capturing every Jev judgement
  (kind, question, full option distribution, choice, confidence), roles
  (`Player.role`), teams (`Team` civilian/undercover/town/werewolf/good/evil), and a
  multi-member hidden team via `BeliefRecord.ground_truth_ids`.
- **Three games** on the shared contract:
  - **Undercover** (Who-Is-The-Spy): Jev clue selection + suspicion, with a
    `max_reveal` knob.
  - **Werewolf**: werewolves, a seer, and villagers over a night/day cycle — night
    kill (combined across the pack), seer inspection, day statements, suspicion,
    voting.
  - **Avalon** (The Resistance): five quests with team proposals, approve/reject
    votes (Jev `Noul`), quest success/fail with evil sabotage (Jev `Noul`), and the
    Assassin's Merlin guess (Jev `Choice`).
- **Backend-agnostic Jev client:** a live backend (`typesafe-sdk`) and a
  deterministic offline backend so everything runs with no API key.
- **Analysis harness:** expected calibration error, Brier score, top-1 accuracy,
  reliability bins, belief-trajectory aggregation, and a cross-game benchmark
  (`scripts/benchmark.py`).
- **God's-eye viewers:** a terminal `--watch` (上帝视角) and a self-contained web
  viewer (`--web`) that render all three games — a per-agent readout (what each Jev
  said, who it accuses, a faithful derived reason, belief bars), a full Jev decision
  log, and game-specific structure (night phase, quest tracker, team proposals).
  Deep-linkable via `?game=&step=`. A combined multi-game page ships on GitHub Pages
  (`scripts/build_pages.py`).
- **CLI** `jev-undercover` with `--game {undercover,werewolf,avalon}`, sweeps, JSON
  export, and trajectory plots.
- **Tooling:** `pytest` suite (offline, deterministic), `ruff` lint, `mypy --strict`,
  PEP 561 `py.typed`, a GitHub Actions CI matrix (Python 3.10–3.13) that also builds
  and checks the wheel, Dependabot, pre-commit, and full community-health files.
- **Docs:** README with the paper framing and screenshots, and
  `docs/related_work.md` with citations to prior LLM social-deduction and
  belief-probing work.

### Notes
- The offline backend is a deterministic stand-in, not a claim about Jev's accuracy;
  for scientific results run `--backend live`. Offline Avalon favors evil (blind
  good loses).
