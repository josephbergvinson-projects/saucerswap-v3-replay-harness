# WHBAR/USDC Replay Study — Final Report

## Executive summary

This study replays 7,255,957 historical WHBAR/USDC V2 events against two synthetic V3-style execution scenarios.

Both synthetic scenarios materially improve price quality versus V2. The book-only scenario reduces average study slippage from 19.97 bps to 2.26 bps, but leaves too much large-order flow incomplete. The hybrid scenario preserves essentially the same slippage while improving full-fill rate from 98.21% to 98.95% overall and from 42.16% to 65.11% in the $25k+ bucket. That makes hybrid the best overall result in this study.

Lambdaplex is relevant only as an external benchmark. Its published panel is useful for directional context, but it is not fully normalized into the same schema across completion, weighting, fee treatment, or methodology.

## Decision rule

The preferred design is **not** the one with the lowest slippage in isolation. The preferred design is the one that preserves most of the slippage improvement versus V2 while keeping completion high, especially on large clips.

That yields a simple decision matrix:

| Decision lens | Preferred scenario | Why |
| --- | --- | --- |
| Best price only | Book-only and hybrid are effectively tied | Both reduce average study slippage to about 2.26 bps. |
| Best overall price + completion | Hybrid | It keeps the slippage gain while materially reducing incomplete large-order flow. |
| Best guaranteed completion | V2 baseline | It fully completes the replay set, but at much worse slippage. |

## What this study shows / does not show

### What this study shows

- On the same historical WHBAR/USDC flow, both synthetic V3-style scenarios improve price quality materially versus the V2 baseline.
- The book-only scenario is too capacity-constrained on large clips.
- The hybrid scenario materially closes that completion gap without giving back the slippage advantage.
- Lambdaplex is directionally useful as an external benchmark, especially for AMM-facing slippage context, but only under explicit caveats.

### What this study does not show

- A production-faithful simulation of deployed SaucerSwap V3 or any live generic on-chain order book.
- A fully normalized Lambdaplex benchmark across fill rate, completion, remainder, and methodology.
- Fee-aware synthetic-scenario outcomes; the current book-only and hybrid scenarios still carry `fees_paid = 0.0` because this phase has no grounded synthetic or blended fee model.

## Study design

### Historical replay set

- Market: WHBAR/USDC
- Source venue: SaucerSwap V2 0.15% pool
- Replay coverage: 7,255,957 event-level replay units
- Split: 3,770,999 buys and 3,484,958 sells

### Replay scenarios

**V2 baseline**
- Realized SaucerSwap V2 execution under the event-level replay contract.

**Book-only (3A)**
- A six-level replenishing synthetic book centered on the study reference price.
- Spreads: 2 / 4 / 8 / 16 / 32 / 64 bps.
- Weights: 1 / 1 / 2 / 3 / 5 / 8.
- Total synthetic grid liquidity: $20,000.

**Hybrid (3B)**
- The same book-only fill first.
- Residual size routes to historical V2 only when the study-owned admissibility rule passes.
- After the large-clip improvement pass, admissibility is evaluated on the projected blended execution price rather than the residual V2 leg in isolation.

### Metric definitions used in the main body

The main body uses one primary slippage metric:

- **Avg study slippage (bps)** = `avg_slippage_bps`, the study-owned external-reference slippage metric.

Other headline metrics:

- **Full-fill rate** = share of replay units fully completed.
- **Avg completion** = average filled share of requested size across replay units.
- **Remainder** = total unfilled HBAR volume left on the table.

Unless otherwise noted, average metrics in the study tables are simple row-weighted averages over replay units. The cost section later is secondary and uses filled-notional-based implied slippage cost.

## Headline results

### Overall scenario comparison

| Scenario | Full-fill rate | Avg completion | Avg study slippage | Remainder |
| --- | ---: | ---: | ---: | ---: |
| V2 baseline | 100.00% | 100.00% | 19.97 bps | 0 HBAR |
| Book-only | 98.21% | 99.98% | 2.26 bps | 431.6M HBAR |
| Hybrid | 98.95% | 99.99% | 2.26 bps | 253.2M HBAR |

Takeaway: both synthetic scenarios slash slippage versus V2, but hybrid is the better overall scenario because it keeps that price improvement while cutting remainder by 178.4M HBAR versus book-only.

### Why hybrid is the preferred result

Relative to book-only, hybrid improves:

- full-fill rate from **98.21% to 98.95%**
- avg completion from **99.9813% to 99.9926%**
- remainder from **431.6M to 253.2M HBAR**
- partial-fill events from **28,789 to 1,114**

That is the core reason the report prefers hybrid rather than simply picking the lowest-slippage synthetic scenario and stopping there.

## $25k+ stress case

The clearest stress test in the study is the $25k+ requested-notional bucket.

| Scenario | Full-fill rate | Avg completion | Avg study slippage | Remainder |
| --- | ---: | ---: | ---: | ---: |
| V2 baseline | 100.00% | 100.00% | 57.84 bps | 0 HBAR |
| Book-only | 42.16% | 52.13% | 37.16 bps | 418.3M HBAR |
| Hybrid | 65.11% | 79.80% | 35.30 bps | 252.4M HBAR |

Takeaway: book-only breaks down on large clips, while hybrid materially closes the completion gap without giving back the slippage advantage. This is the strongest stress-case argument for hybrid.

## Secondary cost framing

A secondary way to summarize the result is implied slippage cost per $1M of filled notional on the **study-owned slippage metric**.

| Scenario | Study slippage cost per $1M filled | Improvement vs V2 |
| --- | ---: | ---: |
| V2 baseline | $2,440.77 | — |
| Book-only | $473.38 | $1,967.39 lower |
| Hybrid | $497.13 | $1,943.64 lower |

This cost framing is useful, but secondary. It mixes price quality and completion, so it should not override the decision rule above. That is why hybrid remains the preferred overall scenario even though book-only is slightly better on pure price cost alone.

## External benchmark: Lambdaplex

Lambdaplex should be treated as an external benchmark, not as a fourth replay scenario equivalent to the three modeled here.

### What Lambdaplex publicly discloses

The published Lambdaplex panel gives two numbers relevant here:

- **Average AMM slippage:** 15.47 bps
- **Grid-strategy slippage:** 2.82 bps

What it does **not** disclose well enough for full normalization:

- fill rate
- avg completion
- remainder / unfilled size
- weighting basis
- fee treatment
- failure / partial-fill treatment

### How to compare Lambdaplex to this study

There are two distinct comparison surfaces.

**1. AMM-facing comparison**

For the AMM-facing number, this study uses a separate Lambdaplex-parity proxy metric based on reconstructed AMM pre-trade spot gross slippage. On that denominator, our own V2 baseline lands at **15.47 bps**, which strongly supports the interpretation that Lambdaplex’s published 15.47 bps AMM number is being measured on roughly that basis.

That is why the report treats the Lambdaplex 15.47 figure as comparable to the AMM-facing parity proxy, not to the main study slippage metric.

**2. Book-facing comparison**

For the book-facing number, the closest study-owned comparison is the main book-only / hybrid slippage result:

- Book-only: **2.26 bps**
- Hybrid: **2.26 bps**
- Lambdaplex published grid-strategy slippage: **2.82 bps**

That is directionally encouraging, but it is **not** a fully normalized apples-to-apples result. The gap is small enough that it should be explained mainly by modeling and normalization differences, not by claiming some proven architectural edge. Our synthetic book is replenishing and idealized; Lambdaplex’s published panel still leaves important benchmark semantics undisclosed.

## Main conclusion

The study supports three clear conclusions:

1. **A V3-style execution surface materially improves price quality versus the current WHBAR/USDC V2 pool.**
2. **Book-only is not enough for large clips.** It leaves too much high-notional flow incomplete.
3. **Hybrid is the best overall internal result.** It preserves the slippage gain while materially improving completion and reducing remainder versus book-only.

That is the central claim the report should carry to colleagues.

## Appendix A — Benchmark provenance and output paths

Tracked repo outputs:

- `reports/final-study-report.md`
- `reports/final-comparison.md`
- `reports/validation.md`
- `reports/reconciliation.md`

Benchmark provenance:

- `benchmarks/lambdaplex/published-results.json`
- `benchmarks/lambdaplex/source-notes.md`

## Appendix B — Future studies

This report should be read as a completed **counterfactual replay study**, not as the final word on production-faithful on-chain order-book behavior.

The most useful next studies, if fidelity needs to increase later, are:

1. **Fee-aware overlay rerun**
   - Apply explicit V3 book fees and maker economics to book-only and hybrid as a reporting-layer overlay.
   - Recompute net slippage and all-in trader-cost tables without changing the current completion logic.

2. **Fee-aware hybrid admissibility**
   - Re-test hybrid with fee-inclusive blended execution in the admissibility rule.
   - This would answer whether realistic fees alter routing decisions, completion, and large-clip behavior rather than just post-trade cost reporting.

3. **Production-faithful order-book simulation**
   - Replace the replenishing synthetic-book assumption with a closer reconstruction of live on-chain order-book behavior.
   - That would likely require historical order placement, cancellation, replacement, persistence, queue priority, matching semantics, and more exact fee and timing data.
   - It would also require a closer recovery of order-level admissibility and routing behavior than the current study-owned proxy.

4. **Engineering validation pack**
   - Add golden examples or canonical truth cases from engineering so the simulation can be validated against known matcher outcomes rather than only replay-surface consistency checks.

These are fidelity upgrades, not prerequisites for the current study conclusion.