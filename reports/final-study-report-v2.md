# WHBAR/USDC Replay Study — Final Report V2

## Executive summary

This study replays 7,255,957 historical WHBAR/USDC V2 events against two synthetic V3-style execution scenarios and reports execution-quality, explicit fee-transfer, and gross spread-capture results.

The main execution result is unchanged. Both synthetic scenarios materially improve price quality versus V2. The book-only scenario reduces average study slippage from 19.97 bps to 2.26 bps, but leaves too much large-order flow incomplete. The hybrid scenario preserves essentially the same slippage while improving full-fill rate from 98.21% to 98.95% overall and from 42.16% to 65.11% in the $25k+ bucket. Hybrid therefore remains the best overall result in this study.

The explicit fee-transfer layer points in the same direction. Under the default no-xSAUCE schedule, explicit trader fees are about $5.89M for V2, $4.62M for book-only, and $4.67M for hybrid. V2 is the most expensive outcome for traders by a wide margin. Book-only is cheapest on explicit fees. Hybrid sits between the two because it keeps most flow on the lower-fee synthetic book while routing admissible residual size through the V2 backstop.

RH-24 closes an important interpretation gap on maker economics. Rebate-only tables can understate the V3-style maker-side monetization surface, because explicit maker rebate is only one component of book-maker economics. The gross spread-capture proxy on filled resting-book quotes is about $1.82M, or 4.73 bps on book-leg filled notional, for both 3A and the pure-book leg of 3B. That does not make maker PnL solved, but it does show that explicit maker rebate alone is too narrow a lens for comparing V2 LP economics with V3-style maker economics.

The explicit liquidity-side fee transfer still differs sharply across scenarios, but it should be read alongside the spread-capture section, not as a standalone liquidity-incentive ranking. V2 routes about $4.91M of explicit fee accrual to active LPs. Book-only routes about $77.0k of explicit maker rebate. Hybrid routes the same $77.0k maker rebate plus about $42.9k of residual V2 LP accrual, for about $119.9k of explicit liquidity-side fee transfer. The gross spread-capture proxy makes clear that the rebate is only a small explicit transfer component inside the V3-style book leg.

The tier-2 10% xSAUCE case lowers explicit trader fees further for the synthetic scenarios without changing execution quality. Aggregate trader fees fall to about $4.16M for book-only and $4.21M for hybrid. In this retained fee model, maker rebate and residual LP accrual stay flat because the discount comes out of protocol take rather than liquidity-side earnings.

This standalone v2 report now uses the accepted post-RH-24 rerun basis for the fee and spread-capture tables. Earlier v2 drafts had to treat the fee layer as a split-basis extension because the matching row-level lane outputs were not mounted. RH-24 resolved that by rematerializing raw inputs and rerunning the replay pipeline through reporting.

## Decision rule

Choose the design that preserves most of the slippage improvement versus V2 while keeping completion high, especially on large clips.

That yields the following decision matrix:

| Decision lens | Preferred scenario | Why |
| --- | --- | --- |
| Best price only | Book-only and hybrid are effectively tied | Both reduce average study slippage to about 2.26 bps. |
| Best overall price + completion | Hybrid | It keeps the slippage gain while materially reducing incomplete large-order flow. |
| Best guaranteed completion | V2 baseline | It fully completes the replay set, but at much worse slippage. |
| Lowest explicit trader fee | Book-only, especially with tier-2 xSAUCE | It avoids the V2 backstop fee burden entirely and gets the full synthetic-scenario fee discount. |
| Fairest maker-side monetization proxy available in this study | Gross spread capture on filled resting-book quotes | It is still not full maker PnL, but it is materially broader than rebate-only transfer. |

## What this study shows / does not show

### What this study shows

- On the same historical WHBAR/USDC flow, both synthetic V3-style scenarios improve price quality materially versus the V2 baseline.
- The book-only scenario is too capacity-constrained on large clips.
- The hybrid scenario materially closes that completion gap without giving back the slippage advantage.
- The fee layer quantifies explicit trader fees, explicit maker rebates, active-LP accrual, protocol earnings, and xSAUCE tier effects across V2, book-only, and hybrid.
- The gross spread-capture proxy quantifies filled resting-book monetization separately from both explicit maker rebate and V2 LP fee accrual.
- The published Lambdaplex 15.47 bps AMM figure can be reproduced on our own V2 baseline using the AMM pre-trade spot gross parity proxy, which avoids a denominator mismatch when comparing the studies at a high level.

### What this study does not show

- A production-faithful simulation of deployed SaucerSwap V3 or any live generic on-chain order book.
- A fee-aware rerun of the hybrid routing decision itself. The fee layer here is a reporting-layer reconstruction on the accepted execution surface, not a new routing policy search.
- Full market-maker profitability. Even with the new spread-capture proxy, the report still excludes inventory carry, quote management, queue dynamics, persistence, adverse selection, and capital utilization.
- A full cross-study normalization of every Lambdaplex headline beyond the narrow AMM-facing parity note below.

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

### Current source basis

This standalone v2 report uses the accepted post-RH-24 materialization of the replay pipeline.

RH-24 rematerialized raw inputs and reran:

- normalization
- V2 baseline
- 3A pure-book
- 3B hybrid
- reporting pack

That matters because the fee and spread-capture tables in this report now come from exact row-level lane outputs on the accepted current basis rather than from an earlier split-basis reconstruction.

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
- **Gross spread capture (USD / bps)** = a study-reference spread-capture proxy on filled resting-book quotes. For 3A this covers the whole synthetic-book fill; for 3B it covers the pure-book leg only and excludes the V2 backstop leg.

Fee tables in the main body are deterministic reconstructions from materialized row-level lane outputs plus the locked fee contract above. Dollar figures are rounded for readability in this report.

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

A secondary way to summarize the result is implied execution-shortfall cost per $1M of filled notional on the study-owned slippage surface.

| Scenario | Study slippage cost per $1M filled | Improvement vs V2 |
| --- | ---: | ---: |
| V2 baseline | $2,432.37 | — |
| Book-only | $473.07 | $1,959.30 lower |
| Hybrid | $496.71 | $1,935.66 lower |

This cost framing is useful, but secondary. It mixes price quality and completion, so the decision rule still belongs to the combined price-plus-completion lens above.

## Explicit fee transfer layer

This section reports only the explicit protocol-routed fee transfer layer. It is not a full comparison of V2 LP economics and V3 maker economics. In V2, liquidity compensation is primarily explicit swap-fee accrual to LP capital. In an order book, maker economics come primarily from spread capture on filled resting quotes, with rebates as a secondary tuning lever. The maker rebate shown here is therefore only the measured protocol transfer component, not total maker return.

| Surface | V2 baseline | V3-style book lanes |
| --- | --- | --- |
| Primary liquidity monetization | Explicit LP fee accrual | Spread capture on filled resting quotes |
| Explicit protocol transfer measured here | LP fee accrual | Maker rebate only |
| Not measured here | LP ROI, inventory effects, capital efficiency | Inventory PnL, quote quality, adverse selection, queue effects |

### Headline explicit fee transfer (`no_xsauce` default)

| Scenario | Trader fee (USD) | Maker rebate (USD) | Active LP accrual (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V2 baseline | $5,892,865.90 | $0.00 | $4,910,721.58 | $4,910,721.58 | $982,144.32 | 15.00 |
| Book-only | $4,621,382.48 | $77,023.04 | $0.00 | $77,023.04 | $4,544,359.44 | 11.76 |
| Hybrid | $4,672,841.25 | $77,023.04 | $42,882.31 | $119,905.35 | $4,552,935.90 | 11.89 |

Takeaway: V2 is the most expensive outcome for traders by a wide margin. Book-only is the cheapest explicit-fee synthetic path. Hybrid remains much cheaper than V2, but it gives back some fee advantage versus book-only because the residual backstop inherits V2 fees. The liquidity-side columns here should be read as explicit protocol transfers only, not as a complete comparison of V2 LP return and V3 maker return.

### Explicit liquidity-side fee transfer (not full maker economics)

The table below compares only the explicit liquidity-side fee transfer captured in the current fee model. It does not measure total maker economics in the V3-style scenarios. That broader maker-side picture is why the spread-capture proxy is reported separately below.

| Scenario | Maker rebate (USD) | Active LP accrual (USD) | Liquidity-side total (USD) |
| --- | ---: | ---: | ---: |
| V2 baseline | $0.00 | $4,910,721.58 | $4,910,721.58 |
| Book-only | $77,023.04 | $0.00 | $77,023.04 |
| Hybrid | $77,023.04 | $42,882.31 | $119,905.35 |

Interpretation:

- V2 concentrates liquidity compensation in explicit LP fee accrual.
- In the V3-style scenarios, the measured protocol transfer to makers is only the rebate component; it does not include spread capture or other maker-side economics.
- Hybrid preserves the same explicit maker rebate on the book leg and adds residual V2 LP accrual where the backstop fills.
- Lower rebate totals here should not be read as weaker maker incentives than V2 LP accrual; they reflect a different monetization model.

That makes this section useful as a fee-routing comparison, not as a total liquidity-incentive ranking.

### $25k+ explicit fee transfer stress case (`no_xsauce` default)

The fee story is especially informative in the same $25k+ bucket where the book-only scenario breaks down on completion.

| Scenario | Trader fee (USD) | Maker rebate (USD) | Active LP accrual (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V2 baseline | $192,217.23 | $0.00 | $160,181.02 | $160,181.02 | $32,036.20 | 15.00 |
| Book-only | $63,360.00 | $1,056.00 | $0.00 | $1,056.00 | $62,304.00 | 4.94 |
| Hybrid | $111,788.42 | $1,056.00 | $40,357.02 | $41,413.02 | $70,375.40 | 8.72 |

Takeaway: on large clips, book-only is cheapest on explicit fees because it completes far less of the hardest flow. Hybrid pays more than book-only because it actually completes more of that large-order flow through the V2 residual leg. Even so, hybrid remains materially cheaper than V2 on explicit trader fees in this bucket.

## Gross spread capture on filled resting quotes

This section reports gross spread capture only on filled synthetic resting-book quotes.

- For **3A**, that means the full pure-book fill.
- For **3B**, that means the pure-book leg only; the V2 backstop leg is excluded.
- This is **not** full maker PnL, and it should not be conflated with either V2 LP fee accrual or the explicit V3 maker rebate.

### Aggregate gross spread capture

| Scenario | Book-leg filled notional (USD) | Gross spread capture (USD) | Gross spread capture (bps on book-leg filled notional) |
| --- | ---: | ---: | ---: |
| Book-only | $3,851,152,066.77 | $1,821,860.20 | 4.73 |
| Hybrid pure-book leg | $3,851,152,066.77 | $1,821,860.20 | 4.73 |

These aggregate values are identical because the hybrid route reuses the same pure-book fill and only appends a V2 backstop leg when residual remains.

### Bucket pattern

| Requested-notional bucket | Gross spread capture (USD) | Gross spread capture (bps on book-leg filled notional) |
| --- | ---: | ---: |
| <1k | $245,832.51 | 2.00 |
| 1k-5k | $746,748.62 | 3.46 |
| 5k-10k | $276,596.11 | 9.93 |
| 10k-25k | $356,831.64 | 26.50 |
| 25k+ | $195,851.32 | 37.09 |

The gross spread-capture proxy rises sharply with order size. That is exactly the pattern you would expect from a replenishing-book design with wider effective capture on larger, harder-to-fill clips.

### Interpretation

This result changes the fair reading of the maker-side comparison.

If we looked only at explicit protocol transfer, we would see about **$77.0k** of maker rebate in the book-only lane. Once gross spread capture is reported, the maker-side monetization picture is visibly broader: the filled resting-book leg captures about **$1.82M** of study-reference spread. That still does not solve full maker profitability, but it does show that rebate-only tables materially understate the V3-style maker economics surface.

## Tier-2 (10%) xSAUCE fee case

The tier-2 xSAUCE case changes the fee schedule, not the execution path. Fill rate, completion, slippage, remainder, and gross spread capture therefore stay the same. What changes is the allocation of explicit fees: traders pay less, protocol take falls, and the measured liquidity-side transfer remains unchanged. In this retained model, tier-2 xSAUCE lowers trader fees only; it does not change the modeled maker rebate.

### Aggregate tier-2 results

| Scenario | Trader fee (USD) | Maker rebate (USD) | Active LP accrual (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V2 baseline | $5,892,865.90 | $0.00 | $4,910,721.58 | $4,910,721.58 | $982,144.32 | 15.00 |
| Book-only | $4,159,244.23 | $77,023.04 | $0.00 | $77,023.04 | $4,082,221.19 | 10.59 |
| Hybrid | $4,210,703.00 | $77,023.04 | $42,882.31 | $119,905.35 | $4,090,797.65 | 10.72 |

Relative to the default no-xSAUCE schedule:

- Book-only trader fees fall by about **$462.1k**.
- Hybrid trader fees fall by about **$462.1k**.
- Maker rebates and LP accrual are unchanged.
- The discount comes out of protocol earnings, not liquidity-side earnings.

In the $25k+ bucket specifically, trader fees fall from **$63.36k** to **$57.02k** for book-only and from **$111.79k** to about **$105.45k** for hybrid, while the liquidity-side transfer remains unchanged.

## Benchmark normalization note

The only Lambdaplex point worth carrying in this v2 report is the denominator check.

The published Lambdaplex study reports **15.47 bps** average AMM slippage. Using the AMM pre-trade spot gross parity proxy in the replay harness, our own V2 baseline reproduces **15.47 bps** on that AMM-facing denominator. That is enough to show that the headline V2 number can be matched on the benchmark-style surface rather than treated as evidence that our study is using a weaker comparison.

On the study-owned comparison surface that drives the main decision in this report, the synthetic V3 scenarios still land around **2.26 bps**. That is the point that matters if someone tries to infer from the Lambdaplex study that the replayed order-book design here is somehow inferior.

## Main conclusion

The study now supports five clear conclusions:

1. **A V3-style execution surface materially improves price quality versus the current WHBAR/USDC V2 pool.**
2. **Book-only is not enough for large clips.** It leaves too much high-notional flow incomplete.
3. **Hybrid is the best overall internal result.** It preserves the slippage gain while materially improving completion and reducing remainder versus book-only.
4. **The explicit fee-transfer layer strengthens the case against V2 without changing the preferred scenario.** V2 is the worst outcome on explicit trader fees, book-only is the cheapest synthetic path, and hybrid is the best combined price-plus-completion design.
5. **The new gross spread-capture proxy makes the maker-side comparison fairer.** Rebate-only transfer materially understates V3-style book-maker monetization; the filled resting-book leg captures about $1.82M of study-reference spread even though the explicit maker rebate is only about $77k.

## Appendix A — Output paths

Tracked repo outputs:

- `reports/final-study-report.md`
- `reports/final-study-report-v2.md`
- `reports/final-comparison.md`
- `reports/final-comparison-v2.md`
- `reports/rh24-gross-spread-capture.md`
- `reports/validation.md`
- `reports/reconciliation.md`

Historical fee-derivation artifacts retained for provenance:

- `artifacts/rh23-report-v2/fees_no_xsauce.csv`
- `artifacts/rh23-report-v2/fees_tier2_10pct.csv`
- `artifacts/rh23-report-v2/summary.json`

## Appendix B — Historical basis note

Earlier drafts of this standalone v2 report had to treat the fee layer as a split-basis extension because the matching row-level lane outputs for the accepted hybrid basis were not mounted in the workspace.

RH-24 resolved that gap by rematerializing raw inputs and rerunning:

- normalization
- V2 baseline
- 3A pure-book
- 3B hybrid
- reporting pack

The current standalone v2 report therefore uses the accepted post-RH-24 row-level basis for both the fee tables and the gross spread-capture tables.

Historically, the later RH-12 hybrid rerun had already established the substantive direction of the final result: hybrid materially improves large-clip completion versus the earlier hybrid basis without giving back the low-slippage profile. RH-24 does not change that conclusion; it makes the economics surface more complete and better grounded.

## Appendix C — Future studies

This report should be read as a completed **counterfactual replay study**, not as the final word on production-faithful on-chain order-book behavior.

The most useful next studies, if fidelity needs to increase later, are:

1. **Fee-aware hybrid admissibility rerun**
   - Re-test hybrid with fee-inclusive blended execution inside the admissibility rule itself.
   - This would answer whether realistic fees change routing decisions, completion, and large-clip behavior rather than only post-trade reporting.

2. **Full maker-profitability model**
   - Extend beyond gross spread capture into inventory carry, quote persistence, queue priority, adverse selection, and capital utilization.
   - That would turn the current maker-side proxy into a fuller market-maker economics model.

3. **Production-faithful order-book simulation**
   - Replace the replenishing synthetic-book assumption with a closer reconstruction of live on-chain order-book behavior.
   - That would likely require historical order placement, cancellation, replacement, persistence, queue priority, matching semantics, and more exact fee and timing data.

4. **Engineering validation pack**
   - Add golden examples or canonical truth cases from engineering so the simulation can be validated against known matcher outcomes rather than only replay-surface consistency checks.

These are fidelity upgrades, not prerequisites for the current study conclusion.
