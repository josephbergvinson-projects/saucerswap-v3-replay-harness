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
- Lambdaplex published panel status is `placeholder`; no comparable benchmark metrics were merged. Provenance: local_payload_state=placeholder_only | local_payload_complete=false | Comparable Lambdaplex headline metrics are not recorded locally in this worktree, so RH-09 can only ship the ingestion contract and explicit blocker handling. | mapping_notes=Only comparable_headline_metrics are eligible for merge into reporting outputs.; Raw headline_metrics remain provenance-only until explicitly mapped. | captured_artifacts=benchmarks/lambdaplex/published-results.json, benchmarks/lambdaplex/source-notes.md.
