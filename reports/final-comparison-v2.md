# Final Comparison Report V2

## Source basis and scope

- This v2 report adds the fee-inclusive layer requested after the originally published replay study.
- The fee reconstruction in this document is anchored to the last retained structured reporting snapshot: `artifacts/rh09-benchmark-20260325/reporting-root/`.
- The current `reports/final-comparison.md` on `main` reflects a later RH-12 hybrid-only execution rerun, but the matching structured lane CSVs/summaries were not retained, so exact fee reconstruction on that later basis is not possible from the mounted workspace.
- To avoid mixing incompatible bases, the execution-quality tables and fee tables in this v2 document are all tied to the retained RH-09 structured snapshot.
- The later RH-12 hybrid delta is still captured separately below so the report preserves the full study history.

## Changelog vs prior final report

- Added explicit trader-fee, liquidity-side-earnings, and protocol-earnings surfaces for V2 / 3A / 3B.
- Added xSAUCE fee sensitivity (`no_xsauce` vs `tier2_10pct`).
- Added an explicit reconstruction note for the fee layer and a later-RH-12 delta note for 3B.
- Preserved the execution-quality comparison as a separate surface rather than silently replacing it with fee-inclusive metrics.

## Locked fee model used in this report

- **V2 WHBAR/USDC**: trader pays `15.0 bps`, active LPs earn `12.5 bps`, protocol earns `2.5 bps`.
- **V3 WHBAR/USDC / no xSAUCE**: trader pays `12.0 bps`, maker earns `0.20 bps`, protocol earns `11.8 bps`.
- **V3 WHBAR/USDC / tier 2 (10%)**: trader pays `10.8 bps`, maker earns `0.18 bps`, protocol earns `10.62 bps`.
- **3B hybrid attribution rule**: pure-book notional uses the V3 schedule; the residual notional above 3A for the same segment is treated as V2 backstop notional and uses the V2 schedule.

## Validation / reconstruction note

- The retained RH-09 structured snapshot still validates cleanly at the aggregate, side, and bucket level.
- Fee rows in this v2 report are deterministic transformations of retained `filled_notional_usdc` plus the locked RH-20/21 fee contract.
- Because replay-unit lane files are no longer mounted, this report **cannot** surface exact replay-unit-level `v3_min_order_ineligible` counts or the exact RH-22 all-in trader-cost USD rollups that depend on row-level execution-shortfall reconstruction.
- V2 liquidity-side figures are aggregate active-LP fee accrual, not LP ROI. V3 liquidity-side figures are maker rebate capture, not full market-maker PnL.

## Execution-quality headline snapshot (retained structured basis)

| Lane | Rows | Fill rate | Avg completion | Avg study slippage (bps) |
| --- | --- | --- | --- | --- |
| V2 baseline | 7255957 | 1 | 1 | 19.966868 |
| 3A pure-book | 7255957 | 0.982051 | 0.999813 | 2.261848 |
| 3B hybrid | 7255957 | 0.987708 | 0.999901 | 2.260515 |

## Explicit fee economics — headline aggregate (`no_xsauce` default)

| Lane | Trader fee (USD) | Maker rebate (USD) | V2 LP accrual (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) | Trader fee (bps, filled) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V2 baseline | 5,892,865.90 | 0.00 | 4,910,721.58 | 4,910,721.58 | 982,144.32 | 15 | 15 |
| 3A pure-book | 4,621,382.48 | 77,023.04 | 0.00 | 77,023.04 | 4,544,359.44 | 11.763502 | 12 |
| 3B hybrid | 4,662,788.54 | 77,023.04 | 34,505.05 | 111,528.09 | 4,551,260.45 | 11.868899 | 12.02135 |

## Fee side split (`no_xsauce` default)

| Side | Lane | Trader fee (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | --- | --- | --- | --- | --- |
| buy | V2 baseline | 2,948,018.93 | 2,456,682.44 | 491,336.49 | 15 |
| buy | 3A pure-book | 2,309,875.82 | 38,497.93 | 2,271,377.89 | 11.753024 |
| buy | 3B hybrid | 2,331,907.81 | 56,857.92 | 2,275,049.88 | 11.865126 |
| sell | V2 baseline | 2,944,846.97 | 2,454,039.14 | 490,807.83 | 15 |
| sell | 3A pure-book | 2,311,506.66 | 38,525.11 | 2,272,981.55 | 11.77399 |
| sell | 3B hybrid | 2,330,880.73 | 54,670.17 | 2,276,210.56 | 11.872675 |

## Fee bucket split (`no_xsauce` default)

| Bucket | Lane | Trader fee (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | --- | --- | --- | --- | --- |
| <1k | V2 baseline | 1,843,829.45 | 1,536,524.54 | 307,304.91 | 15 |
| <1k | 3A pure-book | 1,474,995.78 | 24,583.26 | 1,450,412.51 | 11.999449 |
| <1k | 3B hybrid | 1,474,995.78 | 24,583.26 | 1,450,412.51 | 11.999449 |
| 1k-5k | V2 baseline | 3,234,033.33 | 2,695,027.78 | 539,005.56 | 15 |
| 1k-5k | 3A pure-book | 2,587,302.08 | 43,121.70 | 2,544,180.38 | 12.00035 |
| 1k-5k | 3B hybrid | 2,587,302.08 | 43,121.70 | 2,544,180.38 | 12.00035 |
| 5k-10k | V2 baseline | 417,654.47 | 348,045.39 | 69,609.08 | 15 |
| 5k-10k | 3A pure-book | 334,114.32 | 5,568.57 | 328,545.75 | 11.999668 |
| 5k-10k | 3B hybrid | 334,114.32 | 5,568.57 | 328,545.75 | 11.999668 |
| 10k-25k | V2 baseline | 205,131.43 | 170,942.86 | 34,188.57 | 15 |
| 10k-25k | 3A pure-book | 161,610.30 | 2,693.51 | 158,916.80 | 11.817568 |
| 10k-25k | 3B hybrid | 163,805.82 | 4,523.10 | 159,282.72 | 11.978112 |
| 25k+ | V2 baseline | 192,217.23 | 160,181.02 | 32,036.20 | 15 |
| 25k+ | 3A pure-book | 63,360.00 | 1,056.00 | 62,304.00 | 4.944406 |
| 25k+ | 3B hybrid | 102,570.54 | 33,731.45 | 68,839.09 | 8.004267 |

## xSAUCE fee sensitivity — headline aggregate

| Lane | Scenario | Trader fee (USD) | Liquidity-side total (USD) | Protocol earnings (USD) | Trader fee (bps, requested) |
| --- | --- | --- | --- | --- | --- |
| V2 baseline | v2_fixed | 5,892,865.90 | 4,910,721.58 | 982,144.32 | 15 |
| 3A pure-book | no_xsauce | 4,621,382.48 | 77,023.04 | 4,544,359.44 | 11.763502 |
| 3A pure-book | tier2_10pct | 4,159,244.23 | 69,320.74 | 4,089,923.49 | 10.587151 |
| 3B hybrid | no_xsauce | 4,662,788.54 | 111,528.09 | 4,551,260.45 | 11.868899 |
| 3B hybrid | tier2_10pct | 4,200,650.29 | 103,825.79 | 4,096,824.50 | 10.692548 |

## Interpretation

- V2 charges the highest explicit trader fee at a fixed `15 bps`, but routes all of that fee to active LPs plus the protocol.
- 3A lowers explicit trader fees versus V2 while redirecting the liquidity-side transfer from LP accrual to maker rebate capture.
- 3B sits between 3A and V2: its explicit fee layer is lower than V2 because much of the flow remains on the pure book, but higher than 3A because the residual backstop inherits V2 fees.
- The xSAUCE tier-2 case lowers explicit trader fees for 3A/3B and also trims maker rebates proportionally, with the remaining fee reduction flowing out of protocol take.

## Later RH-12 hybrid-only rerun note

- The later RH-12 rerun improved 3B execution-quality metrics versus the retained RH-09 structured snapshot, especially in larger buckets.
- Those hybrid-only execution deltas are preserved here for completeness, but fee totals in this v2 report remain tied to the retained RH-09 structured pack because the later filled-notional tables were not retained.

# RH-12 before/after delta summary

Comparison basis:
- Before: `artifacts/rh09-benchmark-20260325/reporting-root/data/processed/`
- After: `artifacts/rh12-large-clip-20260325/rerun-root/data/processed/`
- Lane: `3b_hybrid`

## Aggregate

| metric | before | after | delta |
| --- | ---: | ---: | ---: |
| fill_rate | 0.98770777613 | 0.989470558433 | +0.001762782303 |
| avg_completion_ratio | 0.999901267765 | 0.999925922904 | +2.4655139e-05 |
| avg_slippage_bps | 2.26051499944 | 2.26109193653 | +0.000576937089 |
| avg_abs_slippage_bps | 2.2615340605 | 2.26211099759 | +0.00057693709 |
| remainder_size_hbar | 295569026.428 | 253182566.923 | -42386459.505 |
| full_fill_rows | 7252757 | 7254843 | +2086 |
| partial_fill_rows | 3200 | 1114 | -2086 |
| admissibility_pass_rows | 25780 | 27885 | +2105 |
| admissibility_fail_rows | 3009 | 904 | -2105 |

## 10k-25k

| metric | before | after | delta |
| --- | ---: | ---: | ---: |
| fill_rate | 0.994271699167 | 0.999085179852 | +0.004813480685 |
| avg_completion_ratio | 0.997076310936 | 0.999562502701 | +0.002486191765 |
| avg_slippage_bps | 24.3783611372 | 24.4673984596 | +0.089037322354 |
| avg_abs_slippage_bps | 24.4128664793 | 24.5019038017 | +0.089037322354 |
| remainder_size_hbar | 5077348.01765 | 810861.789227 | -4266486.22842 |
| full_fill_rows | 9194 | 9710 | +516 |
| partial_fill_rows | 540 | 24 | -516 |
| admissibility_pass_rows | 2168 | 2684 | +516 |
| admissibility_fail_rows | 540 | 24 | -516 |

## 25k+

| metric | before | after | delta |
| --- | ---: | ---: | ---: |
| fill_rate | 0.598377402399 | 0.651080608121 | +0.052703205722 |
| avg_completion_ratio | 0.739417552154 | 0.798014535901 | +0.058596983747 |
| avg_slippage_bps | 34.0429995405 | 35.300401593 | +1.25740205242 |
| avg_abs_slippage_bps | 36.7166314612 | 37.9740335137 | +1.25740205242 |
| remainder_size_hbar | 290491678.411 | 252371705.134 | -38119973.2766 |
| full_fill_rows | 1343 | 1749 | +406 |
| partial_fill_rows | 1297 | 891 | -406 |
| admissibility_pass_rows | 1353 | 1760 | +407 |
| admissibility_fail_rows | 1287 | 880 | -407 |

## Current main report reference

- `reports/final-comparison.md` remains preserved as the later execution-quality / parity-proxy report on `main`.
- This v2 document does not overwrite that report basis; it adds the fee layer on the last retained structured snapshot and carries the later RH-12 hybrid delta separately.
- The current main report still contains the latest RH-12 hybrid execution figures (for example 3B aggregate `fill_rate = 0.989470558433` and `avg_slippage_bps = 2.261091936527`), but exact fee totals on that later basis cannot be reconstructed without the missing structured lane outputs.
