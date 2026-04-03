# Validation Report

## Rollup validation

| Lane | Rows | Requested totals | Filled totals | Completion counts | Fee coverage | Fee rollup | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V2 baseline | true | true | true | true | true | true | pass |
| 3A pure-book | true | true | true | true | true | true | pass |
| 3B hybrid | true | true | true | true | true | true | pass |

## Provider-economics horizon checks

| Lane | Rows | Supported rows | Unavailable rows | Net provider economics (USD) | Notes |
| --- | --- | --- | --- | --- | --- |
| V2 baseline | 7255957 | 7255956 | 1 | 4000274.148095092271 | Active LP fee accrual minus adverse-only next-event divergence/LVR-style loss proxy on filled V2 size. |
| 3A pure-book | 7255957 | 7255956 | 1 | 1476833.466783466283 | Gross spread capture plus maker rebate minus adverse-only next-event maker markout on filled resting-book size. |
| 3B hybrid | 7255957 | 7255956 | 1 | 1476833.466783466516 | Pure-book leg only for spread, rebate, and markout. Excludes the V2 backstop leg and any residual V2 LP fee accrual. |

## Global checks

- Lane order fixed to: V2 baseline, 3A pure-book, 3B hybrid.
- Side split enabled in config/reporting.yaml: true.
- Bucket split enabled in config/reporting.yaml: true.
- Bucket basis from config/buckets.yaml: `requested_notional` with semantics `lower_inclusive_upper_exclusive_except_last`.
- All direct lane rollups matched mounted lane summaries: true.
- Execution-quality tables and fee-inclusive tables are emitted as separate surfaces; fee views do not replace the canonical study slippage surfaces.
- Fee-inclusive headline comparisons are normalized by requested notional; filled-notional fee bps remain supplemental diagnostics in the CSV outputs.
- Provider-economics next-event pairing uses the immediate next lane row as the reference horizon; unavailable terminal rows are counted separately and adverse-only loss proxies clip favorable moves to zero.
- Canonical `avg_slippage_bps` remains the external-reference study metric; `avg_amm_pre_trade_spot_gross_slippage_bps` is surfaced separately as a Lambdaplex-parity proxy.
- Lambdaplex published panel status is `incomplete`; no comparable benchmark metrics were merged. Provenance: local_payload_state=reported_partial_slide_metrics_only | local_payload_complete=false | The locally captured Lambdaplex slide values disclose only partial slippage figures and do not provide the required comparable fields or enough methodological detail to map into comparable_headline_metrics. | mapping_notes=Only comparable_headline_metrics are eligible for merge into reporting outputs.; The slide-reported 15.47 / 2.82 values are stored as raw headline_metrics provenance only.; The harness now also reports a separate `avg_amm_pre_trade_spot_gross_slippage_bps` parity proxy using the RH-13 best-supported reconstructed AMM pre-trade pool-spot gross convention.; That parity proxy is local study output, not a confirmed Lambdaplex methodological disclosure and not a substitute for comparable_headline_metrics.; Required comparable fields still missing locally: fill_rate, avg_completion_ratio, avg_abs_slippage_bps, remainder_size_hbar.; Weighting basis, reference-price convention, fee treatment, and completion/failure treatment are not disclosed well enough to normalize the slide values into the study schema. | captured_artifacts=benchmarks/lambdaplex/published-results.json, benchmarks/lambdaplex/source-notes.md, operator-provided Lambdaplex slide screenshots (2026-03-25).
