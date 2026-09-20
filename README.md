# Jev Board Game

**Belief as a primitive: instrumenting social-deduction games with a calibrated System-One model.**

Social-deduction games (Undercover, Werewolf, Avalon) are, at their core, games of
*calibrated belief under hidden information*: each player maintains a probability
over who is lying and updates it every turn. A recent wave of work tries to recover
those beliefs from autoregressive LLMs by *probing* them or asking them to *verbalize*
confidence — and repeatedly finds that verbalized confidence is **poorly calibrated**
and must be recalibrated before it can be read as probability (see [Related work](docs/related_work.md)).

This repo takes the opposite route. [Jev](https://typesafe.ai) (TypeSafe's *System One*
model) does not generate text; it returns a **typed, natively-calibrated probability
distribution** as its primitive output. So instead of probing a language model for a
belief and then correcting it, we make the belief the model's direct answer:

> Every agent's suspicion is a Jev `Choice` over the other players. **That probability
> distribution _is_ the belief** — logged every round, and scored against known ground
> truth for calibration (ECE, Brier) and belief-trajectory analysis.

`Jev Board Game` is the testbed and analysis harness for that idea.

---

## Status

| Game | State |
| --- | --- |
| **Undercover** (Who-Is-The-Spy) | ✅ fully implemented (reference game) |
| Werewolf / Mafia | 🚧 scaffolded (shared engine + belief contract) |
| Avalon (The Resistance) | 🚧 scaffolded |

Everything runs **offline with no API key** via a deterministic stand-in backend, so
the demo, experiments, and CI work out of the box. Set `TYPESAFE_API_KEY` to swap in
real Jev judgements.

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # add ",plots" for trajectory PNGs, ",live" for real Jev
```

## Quickstart

```bash
# God's-eye view: WATCH one game play out round-by-round (clues, suspicion, votes)
jev-undercover --watch --players 5 --seed 3

# 20 offline games of 5-player Undercover, with calibration report
jev-undercover --games 20 --players 5

# sweep player count x clue-revealingness (the "how much do clues expose" knob)
jev-undercover --games 20 --players 4,5,6 --max-reveal 0,1,2

# use real Jev (requires TYPESAFE_API_KEY); dump machine-readable results
jev-undercover --backend live --games 50 --players 5 --json runs/live.json
```

Example output (offline backend):

```
backend: offline

[players=5,max_reveal=2] games=20 civ_win_rate=... mean_rounds=... | records=... top1_acc=... mass_on_truth=... brier=... ECE=...
```

> **Note on the offline backend.** It does not understand language; it produces
> stable, well-formed distributions from lexical heuristics (including a generic
> odd-one-out signal) so the pipeline and demo are non-trivial and reproducible. Its
> calibration numbers illustrate the *analysis*, not Jev's real accuracy — for the
> scientific result, run `--backend live`.

## How it maps onto Jev primitives

| Decision | Primitive | Why |
| --- | --- | --- |
| Which clue to say (blend in) | `Choice` over the player's candidate clues | "Select, don't generate" — Jev picks from a bank; code never asks it to write text |
| Who is the spy | `Choice` over the other living players | the returned `probabilities` are the calibrated belief we log |

Two invariants keep the science honest:

1. **Agents never see their own team.** In Undercover no one is told whether their
   word is the majority or minority word, so suspicion is a genuine inference.
2. **Ground truth is analysis-only.** The true spy id is attached to each belief
   record for scoring but is never part of any agent's state.

## Architecture

```
src/jev_board_game/
  jev/          backend-agnostic client: typed Choice/Noul/Score + live & offline backends
  engine/       game contract, players/events, BeliefRecord (the research payload)
  games/        undercover.py (full); werewolf.py, avalon.py (scaffolds)
  agents/       jev_agent.py — clue selection + suspicion via Jev
  analysis/     calibration.py (ECE, Brier, reliability), trajectories.py
  experiment.py run many games / sweep configs and aggregate
  cli.py        `jev-undercover`
```

## Development

```bash
pytest            # test suite (offline, deterministic)
ruff check .      # lint
mypy              # type-check
```

## The paper

The intended contribution and framing live in [`docs/related_work.md`](docs/related_work.md).
Short version: prior social-deduction-agent work measures win rates or probes
autoregressive LLMs for miscalibrated beliefs; here the belief is a calibrated
primitive by construction, and the game is the instrument that tests it.

## License

MIT — see [LICENSE](LICENSE).
