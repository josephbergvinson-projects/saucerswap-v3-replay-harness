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

