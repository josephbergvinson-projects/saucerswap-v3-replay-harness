# Internal Review Memo — RH-04 through RH-09

## Objective
Assess whether the current SaucerSwap V3 replay study is strong enough to support internal directional conclusions, and identify the highest-value remaining gap.

## Current study state

### RH-04 — realized V2 baseline
- Establishes the anchor lane.
- Full completion, but materially higher execution cost.
- Current headline: average slippage is about `19.97` bps.

### RH-05 — 3A pure-book
- Establishes the raw synthetic-book tradeoff.
- Slippage collapses to about `2.26` bps.
- But completion degrades materially, leaving `431.6M` HBAR remainder and `28,789` partial fills.

### RH-06 — 3B hybrid
- Adds the study-owned residual V2 backstop when the admissibility rule passes.
- Preserves the low-slippage profile (`~2.26` bps).
- Improves completion materially versus 3A:
  - remainder falls to `295.6M` HBAR
  - partial fills fall to `3,200`
  - improvement comes from `25,780` admissible residual routes

### RH-07 — reporting pack
- Converts lane outputs into decision-visible comparison surfaces.
- Key read:
  - below `10k` requested notional, 3A/3B are effectively complete while retaining much lower slippage than baseline V2
  - in `10k-25k`, 3B materially improves on 3A
  - in `25k+`, both synthetic lanes still underperform baseline completion:
    - `3A` fill rate: `0.4216`
    - `3B` fill rate: `0.5984`
    - baseline: `1.0`

### RH-08 — validation polish
- Adds explicit audit surfaces behind the reporting story.
- The study now includes deterministic sampled realized-V2 sanity checks and explicit toy golden cases for pure-book and hybrid behavior.
- This materially improves reviewability and trust, even though it does not change the core model assumptions.

### RH-09 — Lambdaplex benchmark contract
- Closes the benchmark-contract and provenance gap in software.
- The benchmark panel is now explicit, schema-validated, and merge-safe.
- But the tracked local benchmark payload is still placeholder-only and non-comparable, so no actual Lambdaplex performance claim can yet be made.

## What the study now supports
- Strong directional claim:
  - the hybrid lane is materially better than pure-book while preserving the low-slippage profile.
- Strong segmented claim:
  - for mostly sub-`10k` requested-notional flow, the study-owned lanes look viable enough to merit internal product/strategy discussion.
- Honest limitation:
  - the study does **not** yet support a claim of large-clip parity with realized V2 execution.
- Evidence-quality claim:
  - the study is now locally reproducible, reviewable, and auditable enough for serious internal review.

## What still limits the study
- Event-level replay, not order-level reconstruction.
- No grounded synthetic/blended fee model for 3A/3B.
- Large-clip completion remains the main weakness of the current synthetic assumptions.
- Lambdaplex published benchmark values are still not recorded locally in comparable form, so external benchmark conclusions remain blocked.

## Decision signal
If the question is whether a study-owned synthetic V3 execution surface can plausibly beat realized V2 on slippage for ordinary flow without collapsing completion, the answer is now directionally yes — especially with the hybrid residual backstop.

If the question is whether the current modeled design credibly replaces baseline behavior for large clips, the answer is still no / not yet proven.

## Recommended next step
The technical pipeline is largely complete. The next highest-value lane is a final closeout/review-pack surface that packages the study into one compact, caveat-forward internal decision artifact and makes the remaining Lambdaplex data blocker impossible to miss.
