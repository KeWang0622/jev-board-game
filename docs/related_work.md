# Related work & paper framing

> **Verification note.** The arXiv IDs and titles below were gathered via web search
> while scoping this repo. Confirm each one (title, authors, venue, ID) against the
> primary source before citing it in a submission — do not trust this file as the
> system of record.

## The gap this repo targets

Two lines of prior work bracket our contribution.

### 1. LLMs *playing* social-deduction games (measured by outcomes)

These build environments and agents and report win rates / capability gaps:

- **Werewolf Arena: A Case Study in LLM Evaluation via Social Deduction** — Bailis,
  Friedhoff et al. (2024). A unified Werewolf evaluation framework.
- **Language Agents with Reinforcement Learning for Strategic Play in the Werewolf
  Game** — Xu et al., ICML 2024. arXiv:2310.18940.
- **AvalonBench: Evaluating LLMs Playing the Game of Avalon** — Light et al.
  arXiv:2310.05036. Reports large capability gaps (e.g. best model ~22% win as a
  good role). Code: `jonathanmli/Avalon-LLM`.
- **Cooperation on the Fly: Exploring Language Agents for Ad Hoc Teamwork in the
  Avalon Game** — arXiv:2312.17515.
- **Multicultural Spyfall: Assessing LLMs through Dynamic Multilingual Social
  Deduction Game** — Wibowo et al. arXiv:2601.09017.
- **Social Gym and SPaRTan: Benchmarking and Improving LLM Social Reasoning via
  Multi-Agent Game Tournaments** — arXiv:2608.09128. Covers Chameleon, Insider,
  Spyfall, Undercover, Resistance, Werewolf.
- **Beyond Survival: Evaluating LLMs in Social Deduction Games with Human-Aligned
  Strategies** — arXiv:2510.11389. Large human-verified Werewolf dataset.
- **A Survey on Large Language Model-Based Social Agents in Game-Theoretic
  Scenarios** — arXiv:2412.03920.

### 2. LLM *beliefs* in these games (probed, and found miscalibrated)

This very recent (2026) cluster is the closest prior art — and the strongest
motivation for using a natively-calibrated model:

- **MafiaScope: Non-Invasive, Time-Resolved Belief Probing for LLM Agents in Social
  Deduction Games** — arXiv:2607.10645. Time-resolved belief logs with a viewer.
- **Auditing Belief-Conditioned LLM Agents in Hidden-Information Social Deduction
  Games** — arXiv:2607.10814. Auditable belief layer + factorized updates.
- **Do LLMs Trust the Accuser or the Accusation? Measuring Belief Shifts in
  Werewolf** — arXiv:2609.12446. Accusations bias beliefs toward the accused.
- **MARBO: Relational Belief Grounding for LLM Agents in Social Deduction Games** —
  arXiv:2609.06563.

Recurring finding across this cluster: **verbalized / probed confidence is poorly
calibrated** and must be recalibrated before it can be read as probability, and
agents carry systematic egocentric bias (e.g. overestimating how often they are
suspected).

## Our contribution

**Belief as a primitive.** Rather than probe an autoregressive LLM and recalibrate
its verbalized confidence, we obtain each agent's belief directly as the typed
`Choice` probability distribution of a System-One model (Jev) that is *trained for
calibrated decisions*. Concretely:

1. A unified, game-agnostic **belief-logging contract** (`BeliefRecord`) across
   Undercover (implemented), Werewolf, and Avalon (scaffolded).
2. A **calibration harness** (ECE, Brier, reliability curves) and **belief-trajectory
   analysis** over rounds, scored against known ground truth.
3. Controlled **experiment sweeps** (player count, clue-revealingness) as the
   independent variables.

**Testable claims** (to run with `--backend live`):

- **H1 (native calibration).** Jev's per-round suspicion is well-calibrated (low ECE)
  *without* any post-hoc recalibration step, unlike verbalized-confidence baselines.
- **H2 (trajectory).** Mean belief mass on the true spy rises monotonically with
  rounds / clue-revealingness.
- **H3 (transfer).** The same belief-as-primitive recipe carries across all three
  games with no per-game recalibration.

## Suggested venues

Demo/short-paper tracks fit the artifact (cf. MafiaScope → EMNLP System
Demonstrations); the calibration study fits an agents/LLM-evaluation workshop or
main-track short paper. Confirm current deadlines before committing.
