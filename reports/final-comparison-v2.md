# Final Comparison Report V2

## Analytical frame

- The tables below focus on fee-aware and provider-side comparisons for the replay study.
- The execution-quality tables and fee tables are kept on one analytical basis.
- A separate hybrid execution sensitivity table appears later rather than being blended into the fee tables.
- That separation avoids mixing two analytical bases in one headline comparison.

## Included comparison layers

- explicit trader-fee, liquidity-side earnings, and protocol-earnings surfaces for V2 / 3A / 3B
- xSAUCE fee sensitivity (`no_xsauce` vs `tier2_10pct`)
- a symmetric provider-economics comparison layer
- a separate hybrid execution sensitivity table rather than a mixed-basis headline table

## Locked fee model

- **V2 WHBAR/USDC**: trader pays `15.0 bps`, active LPs earn `12.5 bps`, protocol earns `2.5 bps`.
- **V3 WHBAR/USDC / no xSAUCE**: trader pays `12.0 bps`, maker earns `0.20 bps`, protocol earns `11.8 bps`.
- **V3 WHBAR/USDC / tier 2 (10%)**: trader pays `10.8 bps`, maker earns `0.20 bps`, protocol earns `10.6 bps`.
- **3B hybrid attribution rule**: pure-book notional uses the V3 schedule; the residual notional above 3A for the same segment is treated as V2 backstop notional and uses the V2 schedule.

## Method note

- The fee rows below are deterministic transformations of available `filled_notional_usdc` values plus the fee contract specified below.
- Some row-level diagnostics are not available on this basis, so the analysis emphasizes aggregate, side, and bucket comparisons rather than replay-unit-level exception counts.
- V2 liquidity-side figures are aggregate active-LP fee accrual, not LP ROI. V3 liquidity-side figures are maker rebate capture, not full market-maker PnL.

## Execution-quality headline snapshot

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
| 3A pure-book | tier2_10pct | 4,159,244.23 | 77,023.04 | 4,082,221.19 | 10.587151 |
| 3B hybrid | no_xsauce | 4,662,788.54 | 111,528.09 | 4,551,260.45 | 11.868899 |
| 3B hybrid | tier2_10pct | 4,200,650.29 | 111,528.09 | 4,089,122.20 | 10.692548 |

## Interpretation

- V2 charges the highest explicit trader fee at a fixed `15 bps`, but routes all of that fee to active LPs plus the protocol.
- 3A lowers explicit trader fees versus V2 while redirecting the liquidity-side transfer from LP accrual to maker rebate capture.
- 3B sits between 3A and V2: its explicit fee layer is lower than V2 because much of the flow remains on the pure book, but higher than 3A because the residual backstop inherits V2 fees.
- The xSAUCE tier-2 case lowers explicit trader fees for 3A/3B while leaving maker rebates unchanged, with the discount flowing out of protocol take.

## Hybrid execution sensitivity

- A separate hybrid recalculation improved 3B execution-quality metrics versus the basis used for the fee tables, especially in larger buckets.
- That sensitivity is shown separately below rather than blended into the fee tables.

# Hybrid execution sensitivity summary

Comparison basis:
- Fee-table execution basis
- Hybrid sensitivity basis
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

## Reading the hybrid sensitivity table

- The fee tables and execution-quality tables above are intentionally kept on one analytical basis.
- The hybrid sensitivity table reflects a separate execution-only recalculation.
- The two are shown side by side for interpretation, not blended into a single mixed-basis table.
