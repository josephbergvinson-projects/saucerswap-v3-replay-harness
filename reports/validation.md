# Validation Report

## Rollup validation

| Lane | Rows | Requested totals | Filled totals | Completion counts | Fee coverage | Status |
| --- | --- | --- | --- | --- | --- | --- |
| V2 baseline | true | true | true | true | true | pass |
| 3A pure-book | true | true | true | true | true | pass |
| 3B hybrid | true | true | true | true | true | pass |

## Global checks

- Lane order fixed to: V2 baseline, 3A pure-book, 3B hybrid.
- Side split enabled in config/reporting.yaml: true.
- Bucket split enabled in config/reporting.yaml: true.
- Bucket basis from config/buckets.yaml: `requested_notional` with semantics `lower_inclusive_upper_exclusive_except_last`.
- All direct lane rollups matched mounted lane summaries: true.
- Lambdaplex published panel status is `placeholder`; no comparable benchmark metrics were merged.
