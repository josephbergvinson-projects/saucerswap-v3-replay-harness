# WHBAR/USDC Replay Study — Final Report V2

## Executive summary

This report extends the original final replay study with the additional fee-inclusive scope requested after the first publication.

The core execution conclusion does not change. This study replays 7,255,957 historical WHBAR/USDC V2 events against two synthetic V3-style execution scenarios. Both synthetic scenarios materially improve price quality versus V2. The book-only scenario reduces average study slippage from 19.97 bps to 2.26 bps, but leaves too much large-order flow incomplete. The hybrid scenario preserves essentially the same slippage while improving full-fill rate from 98.21% to 98.95% overall and from 42.16% to 65.11% in the $25k+ bucket. That still makes hybrid the best overall result in this study.

What v2 adds is the explicit fee layer. On the retained fee-reconstructable basis, V2 remains the most expensive scenario for traders on explicit fees. Book-only is cheapest on explicit trader fees. Hybrid sits between the two because it keeps most flow on the lower-fee synthetic book but still routes residual size through the V2 backstop when admissible. Under the default no-xSAUCE schedule, reconstructed aggregate trader fees are about $5.89M for V2, $4.62M for book-only, and $4.66M for hybrid. Under the tier-2 10% xSAUCE discount, the synthetic-scenario fee burden drops further.

That fee extension strengthens the case against the current V2 baseline, but it does not overturn the main decision rule. The preferred design is still the one that preserves most of the slippage improvement while keeping completion high on large clips. On that combined lens, hybrid remains the preferred result.

A final caveat is important. The main execution-quality conclusion still uses the later RH-12 hybrid rerun that improved large-clip completion. The fee reconstruction cannot be done exactly on that later basis because the matching structured lane outputs were not retained. To avoid mixing incompatible bases, the fee layer in this v2 report is reconstructed on the last retained structured snapshot and treated as an explicit extension rather than as a fully rerun all-in report on the later hybrid basis.

## Decision rule

The preferred design is **not** the one with the lowest slippage in isolation. The preferred design is the one that preserves most of the slippage improvement versus V2 while keeping completion high, especially on large clips.

That still yields the same core decision matrix:

| Decision lens | Preferred scenario | Why |
| --- | --- | --- |
| Best price only | Book-only and hybrid are effectively tied | Both reduce average study slippage to about 2.26 bps. |
| Best overall price + completion | Hybrid | It keeps the slippage gain while materially reducing incomplete large-order flow. |
| Best guaranteed completion | V2 baseline | It fully completes the replay set, but at much worse slippage. |
| Lowest explicit trader fee | Book-only, especially with tier-2 xSAUCE | It avoids the V2 backstop fee burden entirely and gets the full synthetic-scenario fee discount. |

## What this study shows / does not show

### What this study shows

- On the same historical WHBAR/USDC flow, both synthetic V3-style scenarios improve price quality materially versus the V2 baseline.
- The book-only scenario is too capacity-constrained on large clips.
- The hybrid scenario materially closes that completion gap without giving back the slippage advantage.
- The fee-inclusive extension does not reverse the execution conclusion: hybrid still beats V2 clearly, and book-only remains the cheapest explicit-fee synthetic scenario.
- xSAUCE fee discounts materially lower explicit trader fees for the synthetic scenarios.
- Lambdaplex is directionally useful as an external benchmark, especially for AMM-facing slippage context, but only under explicit caveats.

### What this study does not show

- A production-faithful simulation of deployed SaucerSwap V3 or any live generic on-chain order book.
- A fully normalized Lambdaplex benchmark across fill rate, completion, remainder, weighting, fees, and methodology.
- A fee-aware rerun of the hybrid routing decision itself. The fee layer in this report is a reporting-layer reconstruction, not a new routing simulation.
- An exact all-in trader-cost surface on the later RH-12 hybrid basis, because the matching structured lane outputs were not retained in the mounted workspace.

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

### V2 extension scope and source basis

This v2 report extends the original final study with an explicit fee-inclusive reporting layer.

Two source-basis facts matter:

- The main execution-quality conclusions in this report still use the later RH-12 hybrid rerun already reflected in the original final report on `main`.
- The fee reconstruction is anchored to the last retained structured reporting snapshot: `artifacts/rh09-benchmark-20260325/reporting-root/`.

That split is necessary because the current `reports/final-comparison.md` on `main` reflects the later RH-12 hybrid-only execution rerun, but the matching structured lane CSVs and summaries were not retained. Exact fee reconstruction on that later basis is therefore not possible from the mounted workspace.

The safe way to extend the report is to keep the latest execution-quality conclusion, add the fee layer on the retained structured basis, and state the basis difference explicitly rather than silently blending incompatible snapshots.

### Locked fee model used in this report

- **V2 WHBAR/USDC**: trader pays `15.0 bps`, active LPs earn `12.5 bps`, protocol earns `2.5 bps`.
- **V3 WHBAR/USDC / no xSAUCE**: trader pays `12.0 bps`, maker earns `0.20 bps`, protocol earns `11.8 bps`.
- **V3 WHBAR/USDC / tier 2 (10%)**: trader pays `10.8 bps`, maker earns `0.20 bps`, protocol earns `10.6 bps`.
- **3B hybrid attribution rule**: pure-book notional uses the V3 schedule; the residual notional above 3A for the same segment is treated as V2 backstop notional and uses the V2 schedule.

### Metric definitions used in the main body

The main body still uses one primary slippage metric:

- **Avg study slippage (bps)** = `avg_slippage_bps`, the study-owned external-reference slippage metric.

Other headline metrics:

- **Full-fill rate** = share of replay units fully completed.
- **Avg completion** = average filled share of requested size across replay units.
- **Remainder** = total unfilled HBAR volume left on the table, computed as aggregate requested HBAR minus filled HBAR across replay events. It is an absolute leftover amount, not a percentage.

Fee tables in the main body are explicit-fee reconstructions from retained `filled_notional_usdc` plus the locked fee contract above. Dollar figures are rounded for readability in this report; the companion comparison file keeps the more detailed precision.

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

That is the core reason the report still prefers hybrid rather than simply picking the lowest-slippage synthetic scenario and stopping there.

## $25k+ stress case

The clearest stress test in the study is the $25k+ requested-notional bucket.

| Scenario | Full-fill rate | Avg completion | Avg study slippage | Remainder |
| --- | ---: | ---: | ---: | ---: |
| V2 baseline | 100.00% | 100.00% | 57.84 bps | 0 HBAR |
| Book-only | 42.16% | 52.13% | 37.16 bps | 418.3M HBAR |
| Hybrid | 65.11% | 79.80% | 35.30 bps | 252.4M HBAR |

Takeaway: book-only breaks down on large clips, while hybrid materially closes the completion gap without giving back the slippage advantage. This remains the strongest stress-case argument for hybrid.

## Secondary cost framing

A secondary way to summarize the result is implied slippage cost per $1M of filled notional on the **study-owned slippage metric**.

| Scenario | Study slippage cost per $1M filled | Improvement vs V2 |
| --- | ---: | ---: |
| V2 baseline | $2,440.77 | — |
| Book-only | $473.38 | $1,967.39 lower |
| Hybrid | $497.13 | $1,943.64 lower |

This cost framing is useful, but secondary. It mixes price quality and completion, so it should not override the decision rule above. That is why hybrid remains the preferred overall scenario even though book-only is slightly better on pure price cost alone.

## Fee-inclusive extension

The new scope in v2 is the explicit fee layer.

This section should be read as an extension of the main execution study, not as a silent replacement of it. The execution tables above preserve the latest internal study conclusion. The fee tables below answer a narrower question: given the retained structured basis and the locked fee contract, how do explicit trader fees, liquidity-side earnings, and protocol earnings compare across V2, book-only, and hybrid?

### Headline explicit fee economics (`no_xsauce` default)

| Scenario | Trader fee (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | ---: | ---: | ---: | ---: |
| V2 baseline | $5,892,865.90 | $4,910,721.58 | $982,144.32 | 15.00 |
| Book-only | $4,621,382.48 | $77,023.04 | $4,544,359.44 | 11.76 |
| Hybrid | $4,662,788.54 | $111,528.09 | $4,551,260.45 | 11.87 |

Takeaway: the explicit fee layer strengthens the negative case on the V2 baseline. V2 is the highest-fee outcome for traders by a wide margin. Book-only is the cheapest explicit-fee synthetic path. Hybrid remains much cheaper than V2, but slightly more expensive than book-only because the admissible residual backstop inherits V2 fees.

### What the fee layer changes / does not change

- It **does** show that the synthetic scenarios are not just better on slippage; they are also materially better than V2 on explicit trader fees.
- It **does** show that hybrid gives back some fee advantage versus book-only because the residual V2 leg is real and economically meaningful.
- It **does not** overturn the preferred scenario, because the original reason for preferring hybrid was never lower fees in isolation. It was preserving the slippage gain while materially improving completion on large clips.
- It **does not** supply a fully rerun all-in trader-cost model on the later RH-12 basis. That remains outside what can be reconstructed from the retained files.

### $25k+ explicit fee stress case (retained RH-09 structured basis)

The fee extension is especially informative in the same $25k+ stress bucket where the book-only scenario breaks down on completion.

| Scenario | Trader fee (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | ---: | ---: | ---: | ---: |
| V2 baseline | $192,217.23 | $160,181.02 | $32,036.20 | 15.00 |
| Book-only | $63,360.00 | $1,056.00 | $62,304.00 | 4.94 |
| Hybrid | $102,570.54 | $33,731.45 | $68,839.09 | 8.00 |

Takeaway: on large clips, the fee story still follows the routing story. Book-only is cheapest on explicit trader fees, but only because it leaves much more high-notional flow incomplete. Hybrid pays more than book-only because it actually completes more of that large-order flow through the V2 residual leg. Even so, hybrid remains materially cheaper than V2 on explicit fees in this stress bucket.

### xSAUCE fee sensitivity

Under the tier-2 10% xSAUCE discount, the synthetic-scenario explicit fee burden falls further while maker rebates stay unchanged and the discount comes out of protocol take.

| Scenario | Fee case | Trader fee (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | --- | ---: | ---: | ---: | ---: |
| V2 baseline | fixed V2 | $5,892,865.90 | $4,910,721.58 | $982,144.32 | 15.00 |
| Book-only | no xSAUCE | $4,621,382.48 | $77,023.04 | $4,544,359.44 | 11.76 |
| Book-only | tier 2 (10%) | $4,159,244.23 | $77,023.04 | $4,082,221.19 | 10.59 |
| Hybrid | no xSAUCE | $4,662,788.54 | $111,528.09 | $4,551,260.45 | 11.87 |
| Hybrid | tier 2 (10%) | $4,200,650.29 | $111,528.09 | $4,089,122.20 | 10.69 |

Takeaway: the xSAUCE discount meaningfully lowers explicit trader fees in the synthetic scenarios, but it does not change the ordering. Book-only remains the lowest-fee synthetic path. Hybrid remains the better overall design once completion is reintroduced into the decision rule.

## External benchmark: Lambdaplex

Lambdaplex should still be treated as an external benchmark, not as a fourth replay scenario equivalent to the three modeled here.

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

There are still two distinct comparison surfaces.

**1. AMM-facing comparison**

For the AMM-facing number, this study uses a separate Lambdaplex-parity proxy metric based on reconstructed AMM pre-trade spot gross slippage. On that denominator, our own V2 baseline lands at **15.47 bps**, which strongly supports the interpretation that Lambdaplex’s published 15.47 bps AMM number is being measured on roughly that basis.

That is why this report continues to treat the Lambdaplex 15.47 figure as comparable to the AMM-facing parity proxy, not to the main study slippage metric.

**2. Book-facing comparison**

For the book-facing number, the closest study-owned comparison is still the main book-only / hybrid slippage result:

- Book-only: **2.26 bps**
- Hybrid: **2.26 bps**
- Lambdaplex published grid-strategy slippage: **2.82 bps**

That remains directionally encouraging, but it is **not** a fully normalized apples-to-apples result. The gap is small enough that it should still be explained mainly by modeling and normalization differences, not by claiming some proven architectural edge. Our synthetic book is replenishing and idealized; Lambdaplex’s published panel still leaves important benchmark semantics undisclosed.

The same caveat applies even more strongly on fees. There is still no grounded way to normalize Lambdaplex into the fee-inclusive extension because its public materials do not disclose enough fee, completion, or benchmark-construction detail.

## Main conclusion

The study now supports four clear conclusions:

1. **A V3-style execution surface materially improves price quality versus the current WHBAR/USDC V2 pool.**
2. **Book-only is not enough for large clips.** It leaves too much high-notional flow incomplete.
3. **Hybrid is still the best overall internal result.** It preserves the slippage gain while materially improving completion and reducing remainder versus book-only.
4. **The fee-inclusive extension strengthens the negative case on V2 without changing the preferred scenario.** V2 remains the worst outcome on explicit trader fees, book-only remains the cheapest synthetic path, and hybrid remains the best combined price-plus-completion design.

## Appendix A — Output paths

Tracked repo outputs:

- `reports/final-study-report.md`
- `reports/final-study-report-v2.md`
- `reports/final-comparison.md`
- `reports/final-comparison-v2.md`
- `reports/validation.md`
- `reports/reconciliation.md`

Companion fee-extension artifacts:

- `artifacts/rh23-report-v2/fees_no_xsauce.csv`
- `artifacts/rh23-report-v2/fees_tier2_10pct.csv`
- `artifacts/rh23-report-v2/summary.json`

Benchmark provenance:

- `benchmarks/lambdaplex/published-results.json`
- `benchmarks/lambdaplex/source-notes.md`

## Appendix B — Later RH-12 hybrid rerun note

The original final report on `main` already incorporated the later RH-12 hybrid-only rerun because it materially improved large-clip completion and reduced remainder.

The key aggregate and large-bucket deltas versus the retained RH-09 structured basis were:

| Surface | Metric | Before | After | Delta |
| --- | --- | ---: | ---: | ---: |
| Aggregate | Full-fill rate | 98.77% | 98.95% | +0.18 pts |
| Aggregate | Avg completion | 99.9901% | 99.9926% | +0.0025 pts |
| Aggregate | Avg study slippage | 2.2605 bps | 2.2611 bps | +0.0006 bps |
| Aggregate | Remainder | 295.6M HBAR | 253.2M HBAR | -42.4M HBAR |
| $25k+ | Full-fill rate | 59.84% | 65.11% | +5.27 pts |
| $25k+ | Avg completion | 73.94% | 79.80% | +5.86 pts |
| $25k+ | Avg study slippage | 34.04 bps | 35.30 bps | +1.26 bps |
| $25k+ | Remainder | 290.5M HBAR | 252.4M HBAR | -38.1M HBAR |

That is why the main execution conclusion in this report continues to use the later hybrid figures, even though the fee reconstruction must stay anchored to the earlier retained structured pack.

## Appendix C — Future studies

This report should still be read as a completed **counterfactual replay study**, not as the final word on production-faithful on-chain order-book behavior.

The most useful next studies, if fidelity needs to increase later, are:

1. **Fee-aware hybrid admissibility rerun**
   - Re-test hybrid with fee-inclusive blended execution inside the admissibility rule itself.
   - This would answer whether realistic fees change routing decisions, completion, and large-clip behavior rather than only post-trade reporting.

2. **Full all-in trader-cost reconstruction**
   - Retain the row-level structured outputs needed to recompute exact all-in trader-cost surfaces on the later hybrid basis.
   - That would let the report combine slippage, explicit fees, and execution shortfall on one exact denominator rather than a split-basis extension.

3. **Production-faithful order-book simulation**
   - Replace the replenishing synthetic-book assumption with a closer reconstruction of live on-chain order-book behavior.
   - That would likely require historical order placement, cancellation, replacement, persistence, queue priority, matching semantics, and more exact fee and timing data.

4. **Engineering validation pack**
   - Add golden examples or canonical truth cases from engineering so the simulation can be validated against known matcher outcomes rather than only replay-surface consistency checks.

These are fidelity upgrades, not prerequisites for the current study conclusion.
