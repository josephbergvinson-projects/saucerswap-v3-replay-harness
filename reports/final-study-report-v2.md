# WHBAR/USDC Replay Study — Final Report V2

## Executive summary

This study replays 7,255,957 historical WHBAR/USDC V2 events against two synthetic V3-style execution scenarios and reports both execution-quality and fee-inclusive results.

The main execution result is clear. Both synthetic scenarios materially improve price quality versus V2. The book-only scenario reduces average study slippage from 19.97 bps to 2.26 bps, but leaves too much large-order flow incomplete. The hybrid scenario preserves essentially the same slippage while improving full-fill rate from 98.21% to 98.95% overall and from 42.16% to 65.11% in the $25k+ bucket. Hybrid is therefore the best overall result in this study.

The fee layer points in the same direction. Under the default no-xSAUCE schedule, explicit trader fees are about $5.89M for V2, $4.62M for book-only, and $4.66M for hybrid. V2 is the most expensive outcome for traders by a wide margin. Book-only is cheapest on explicit fees. Hybrid sits between the two because it keeps most flow on the lower-fee synthetic book while routing admissible residual size through the V2 backstop.

Liquidity-side earnings also differ sharply across scenarios. V2 routes about $4.91M to active LPs. Book-only routes about $77.0k to makers. Hybrid routes the same $77.0k maker rebate plus about $34.5k of V2 LP accrual on the residual backstop, for about $111.5k total liquidity-side earnings. That split matters because hybrid improves completion relative to book-only without erasing the distinction between book maker economics and the legacy V2 LP fee path.

The tier-2 10% xSAUCE case lowers explicit trader fees further for the synthetic scenarios without changing execution quality. Aggregate trader fees fall to about $4.16M for book-only and $4.20M for hybrid. Liquidity-side earnings stay flat because the discount comes out of protocol take rather than maker rebates or LP accrual.

One source-basis caveat matters for interpretation. The execution tables in this report preserve the later RH-12 hybrid rerun that improved large-clip completion. The fee reconstruction uses the last retained structured reporting snapshot, because the matching structured lane outputs for the later hybrid rerun were not retained in the mounted workspace. The result is still decision-useful: the latest execution conclusion remains intact, and the fee layer is grounded in retained structured outputs rather than guessed or backfilled from memory.

## Decision rule

Choose the design that preserves most of the slippage improvement versus V2 while keeping completion high, especially on large clips.

That yields the following decision matrix:

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
- The fee layer quantifies trader fees, maker rebates, active-LP accrual, protocol earnings, and xSAUCE tier effects across V2, book-only, and hybrid.
- The published Lambdaplex 15.47 bps AMM figure can be reproduced on our own V2 baseline using the AMM pre-trade spot gross parity proxy, which avoids a denominator mismatch when comparing the studies at a high level.

### What this study does not show

- A production-faithful simulation of deployed SaucerSwap V3 or any live generic on-chain order book.
- A fee-aware rerun of the hybrid routing decision itself. The fee layer here is a reporting reconstruction, not a new routing simulation.
- An exact all-in trader-cost surface on the later RH-12 hybrid basis, because the matching structured lane outputs were not retained in the mounted workspace.
- A full cross-study normalization of every Lambdaplex headline beyond the narrow AMM-facing parity note above.

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

### Source basis and retained outputs

Two retained-output facts matter for this v2 report:

- The execution-quality tables preserve the later RH-12 hybrid rerun already reflected in the published replay conclusions on `main`.
- The fee reconstruction is anchored to the last retained structured reporting snapshot: `artifacts/rh09-benchmark-20260325/reporting-root/`.

That split is necessary because the later RH-12 hybrid rerun improved the execution result materially in large buckets, but the matching structured lane CSVs and summaries needed for exact fee reconstruction were not retained. The fee layer in this report therefore uses the retained structured basis rather than silently mixing incompatible snapshots.

### Locked fee model used in this report

- **V2 WHBAR/USDC**: trader pays `15.0 bps`, active LPs earn `12.5 bps`, protocol earns `2.5 bps`.
- **V3 WHBAR/USDC / no xSAUCE**: trader pays `12.0 bps`, maker earns `0.20 bps`, protocol earns `11.8 bps`.
- **V3 WHBAR/USDC / tier 2 (10%)**: trader pays `10.8 bps`, maker earns `0.20 bps`, protocol earns `10.6 bps`.
- **3B hybrid attribution rule**: pure-book notional uses the V3 schedule; the residual notional above 3A for the same segment is treated as V2 backstop notional and uses the V2 schedule.

### Metric definitions used in the main body

The main body uses one primary slippage metric:

- **Avg study slippage (bps)** = `avg_slippage_bps`, the study-owned external-reference slippage metric.

Other headline metrics:

- **Full-fill rate** = share of replay units fully completed.
- **Avg completion** = average filled share of requested size across replay units.
- **Remainder** = total unfilled HBAR volume left on the table, computed as aggregate requested HBAR minus filled HBAR across replay events. It is an absolute leftover amount, not a percentage.

Fee tables in the main body are deterministic reconstructions from retained `filled_notional_usdc` plus the locked fee contract above. Dollar figures are rounded for readability in this report.

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

That is the main reason this report prefers hybrid rather than simply choosing the lowest-slippage synthetic path and stopping there.

## $25k+ stress case

The clearest stress test in the study is the $25k+ requested-notional bucket.

| Scenario | Full-fill rate | Avg completion | Avg study slippage | Remainder |
| --- | ---: | ---: | ---: | ---: |
| V2 baseline | 100.00% | 100.00% | 57.84 bps | 0 HBAR |
| Book-only | 42.16% | 52.13% | 37.16 bps | 418.3M HBAR |
| Hybrid | 65.11% | 79.80% | 35.30 bps | 252.4M HBAR |

Takeaway: book-only breaks down on large clips, while hybrid materially closes the completion gap without giving back the slippage advantage. This remains the strongest stress-case argument for hybrid.

## Secondary cost framing

A secondary way to summarize the result is implied slippage cost per $1M of filled notional on the study-owned slippage metric.

| Scenario | Study slippage cost per $1M filled | Improvement vs V2 |
| --- | ---: | ---: |
| V2 baseline | $2,440.77 | — |
| Book-only | $473.38 | $1,967.39 lower |
| Hybrid | $497.13 | $1,943.64 lower |

This cost framing is useful, but secondary. It mixes price quality and completion, so the decision rule still belongs to the combined price-plus-completion lens above.

## Explicit fee economics

### Headline explicit fee economics (`no_xsauce` default)

| Scenario | Trader fee (USD) | Maker rebate (USD) | Active LP accrual (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V2 baseline | $5,892,865.90 | $0.00 | $4,910,721.58 | $4,910,721.58 | $982,144.32 | 15.00 |
| Book-only | $4,621,382.48 | $77,023.04 | $0.00 | $77,023.04 | $4,544,359.44 | 11.76 |
| Hybrid | $4,662,788.54 | $77,023.04 | $34,505.05 | $111,528.09 | $4,551,260.45 | 11.87 |

Takeaway: V2 is the most expensive outcome for traders by a wide margin. Book-only is the cheapest explicit-fee synthetic path. Hybrid remains much cheaper than V2, but it gives back some fee advantage versus book-only because the residual backstop inherits V2 fees.

### Liquidity-side earnings

The liquidity-side result is not just a footnote. The scenarios transfer fees to different recipients in very different proportions.

| Scenario | Maker rebate (USD) | Active LP accrual (USD) | Liquidity-side total (USD) |
| --- | ---: | ---: | ---: |
| V2 baseline | $0.00 | $4,910,721.58 | $4,910,721.58 |
| Book-only | $77,023.04 | $0.00 | $77,023.04 |
| Hybrid | $77,023.04 | $34,505.05 | $111,528.09 |

Interpretation:

- V2 routes essentially the whole liquidity-side fee transfer to active LPs.
- Book-only replaces LP accrual with a much smaller maker rebate stream.
- Hybrid preserves the book maker rebate and adds a residual V2 LP accrual stream where the backstop actually fills.

That makes hybrid economically more informative than book-only on the liquidity side. It does not reproduce the V2 LP fee stream, but it does show where LP earnings persist once the residual V2 leg is allowed back into the execution path.

### $25k+ explicit fee stress case (`no_xsauce` default)

The fee story is especially informative in the same $25k+ bucket where the book-only scenario breaks down on completion.

| Scenario | Trader fee (USD) | Maker rebate (USD) | Active LP accrual (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V2 baseline | $192,217.23 | $0.00 | $160,181.02 | $160,181.02 | $32,036.20 | 15.00 |
| Book-only | $63,360.00 | $1,056.00 | $0.00 | $1,056.00 | $62,304.00 | 4.94 |
| Hybrid | $102,570.54 | $1,056.00 | $32,675.45 | $33,731.45 | $68,839.09 | 8.00 |

Takeaway: on large clips, book-only is cheapest on explicit fees because it completes far less of the hardest flow. Hybrid pays more than book-only because it actually completes more of that large-order flow through the V2 residual leg. Even so, hybrid remains materially cheaper than V2 on explicit trader fees in this bucket.

## Tier-2 (10%) xSAUCE fee case

The tier-2 xSAUCE case changes the fee schedule, not the execution path. Fill rate, completion, slippage, and remainder therefore stay the same. What changes is the allocation of explicit fees: traders pay less, protocol take falls, and liquidity-side earnings remain unchanged.

### Aggregate tier-2 results

| Scenario | Trader fee (USD) | Maker rebate (USD) | Active LP accrual (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V2 baseline | $5,892,865.90 | $0.00 | $4,910,721.58 | $4,910,721.58 | $982,144.32 | 15.00 |
| Book-only | $4,159,244.23 | $77,023.04 | $0.00 | $77,023.04 | $4,082,221.19 | 10.59 |
| Hybrid | $4,200,650.29 | $77,023.04 | $34,505.05 | $111,528.09 | $4,089,122.20 | 10.69 |

Relative to the default no-xSAUCE schedule:

- Book-only trader fees fall by about **$462.1k**.
- Hybrid trader fees fall by about **$462.1k**.
- Maker rebates and LP accrual are unchanged.
- The discount comes out of protocol earnings, not liquidity-side earnings.

### $25k+ tier-2 stress case

| Scenario | Trader fee (USD) | Maker rebate (USD) | Active LP accrual (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V2 baseline | $192,217.23 | $0.00 | $160,181.02 | $160,181.02 | $32,036.20 | 15.00 |
| Book-only | $57,024.00 | $1,056.00 | $0.00 | $1,056.00 | $55,968.00 | 4.45 |
| Hybrid | $96,234.54 | $1,056.00 | $32,675.45 | $33,731.45 | $62,503.09 | 7.51 |

Takeaway: the tier-2 fee discount materially lowers trader fees in the hardest bucket without changing execution quality. Hybrid still sits between book-only and V2, and the liquidity-side figures remain exactly the same as in the default fee case.

## Benchmark normalization note

The only Lambdaplex point worth carrying in this v2 report is the denominator check.

The published Lambdaplex study reports **15.47 bps** average AMM slippage. Using the AMM pre-trade spot gross parity proxy in the replay harness, our own V2 baseline reproduces **15.47 bps** on that AMM-facing denominator. That is enough to show that the headline V2 number can be matched on the benchmark-style surface rather than treated as evidence that our study is using a weaker comparison.

On the study-owned comparison surface that drives the main decision in this report, the synthetic V3 scenarios still land around **2.26 bps**. That is the point that matters if someone tries to infer from the Lambdaplex study that the replayed order-book design here is somehow inferior.

## Main conclusion

The study now supports four clear conclusions:

1. **A V3-style execution surface materially improves price quality versus the current WHBAR/USDC V2 pool.**
2. **Book-only is not enough for large clips.** It leaves too much high-notional flow incomplete.
3. **Hybrid is the best overall internal result.** It preserves the slippage gain while materially improving completion and reducing remainder versus book-only.
4. **The fee layer strengthens the case against V2 without changing the preferred scenario.** V2 is the worst outcome on explicit trader fees, book-only is the cheapest synthetic path, hybrid is the best combined price-plus-completion design, and the tier-2 xSAUCE case lowers synthetic-scenario trader fees further without changing execution quality.

## Appendix A — Output paths

Tracked repo outputs:

- `reports/final-study-report.md`
- `reports/final-study-report-v2.md`
- `reports/final-comparison.md`
- `reports/final-comparison-v2.md`
- `reports/validation.md`
- `reports/reconciliation.md`

Companion fee artifacts:

- `artifacts/rh23-report-v2/fees_no_xsauce.csv`
- `artifacts/rh23-report-v2/fees_tier2_10pct.csv`
- `artifacts/rh23-report-v2/summary.json`

## Appendix B — Later RH-12 hybrid rerun note

The later RH-12 hybrid rerun improved the hybrid result materially in the large buckets and is therefore preserved in the main execution conclusions of this report.

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

This is why the main execution conclusion in the report uses the later hybrid figures even though the fee reconstruction stays anchored to the earlier retained structured pack.

## Appendix C — Future studies

This report should be read as a completed **counterfactual replay study**, not as the final word on production-faithful on-chain order-book behavior.

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
