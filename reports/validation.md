# Validation Report

## Study caveats

- This pack is an event-level replay benchmark, not an order-level reconstruction or production-fidelity V3 simulator.
- The reporting path reuses mounted RH-03, RH-04, RH-05, and RH-06 artifacts as read-only inputs and does not rebuild those layers.
- 3A and 3B still carry `fees_paid=0.0` because the current phase has no grounded synthetic or blended fee model.
- The current Lambdaplex published panel is placeholder or incomplete, so no benchmark metrics were merged into the comparison tables.

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

## Sampled realized-V2 sanity pack

First observed row per populated `side x requested_notional bucket` segment from mounted `data/processed/lane_v2_baseline.csv`.

| Segment | Rows in segment | Replay unit | Requested notional (USDC) | Source ordering key | Checks | Status |
| --- | --- | --- | --- | --- | --- | --- |
| buy / <1k | 3166292 | swap:38:trade:38 | 1.900229 | 1700264041:00000000000000000038:00000000000000000038 | 8/8 | pass |
| buy / 1k-5k | 574800 | swap:36:trade:36 | 1000 | 1700264033:00000000000000000036:00000000000000000036 | 8/8 | pass |
| buy / 5k-10k | 23681 | swap:892:trade:889 | 5209.824159 | 1700299745:00000000000000000892:00000000000000000889 | 8/8 | pass |
| buy / 10k-25k | 4851 | swap:1714:trade:1709 | 15000 | 1700374193:00000000000000001714:00000000000000001709 | 8/8 | pass |
| buy / 25k+ | 1375 | swap:2500:trade:2488 | 37883.851237000003 | 1700441895:00000000000000002500:00000000000000002488 | 8/8 | pass |
| sell / <1k | 2867950 | swap:114:trade:114 | 200.081682 | 1700264767:00000000000000000114:00000000000000000114 | 8/8 | pass |
| sell / 1k-5k | 590315 | swap:313:trade:313 | 1963.422392 | 1700270044:00000000000000000313:00000000000000000313 | 8/8 | pass |
| sell / 5k-10k | 20545 | swap:275:trade:275 | 7056.549202 | 1700268979:00000000000000000275:00000000000000000275 | 8/8 | pass |
| sell / 10k-25k | 4883 | swap:2503:trade:2490 | 12460.643164999999 | 1700441913:00000000000000002503:00000000000000002490 | 8/8 | pass |
| sell / 25k+ | 1265 | swap:6475:trade:6459 | 31147.919911000001 | 1700698673:00000000000000006475:00000000000000006459 | 8/8 | pass |

## Toy golden cases

Fixture inputs: `tests/fixtures/toy_book.yaml`, `tests/fixtures/toy_flow.csv`, `tests/fixtures/toy_expected_outputs.json`.

| Case | Lane | Replay unit | Completion ratio | Remainder size | Admissibility | Checks | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pure_book_partial_fill | 3a_pure_book | u1 | 0.799760079971 | 50.059980007197 |  | 14/14 | pass |
| hybrid_admissibility_fail | 3b_hybrid | u2 | 0.800240080029 | 49.939979992797 | false | 14/14 | pass |
| hybrid_admissibility_pass | 3b_hybrid | u3 | 1 | 0 | true | 14/14 | pass |

## Generated artifacts

| Artifact | Path | Status | Fingerprint |
| --- | --- | --- | --- |
| Sampled realized-V2 JSON | reports/generated/rh08-validation-sampled-v2-sanity.json | materialized | 4750efbd150208277e387f8eecc723cd026f6b450e3b14baea1680605a84d169 |
| Sampled realized-V2 Markdown | reports/generated/rh08-validation-sampled-v2-sanity.md | materialized | d724e7d1d4b17112572b5c375f23bfc97ad4ecf98a4f170fcc7502b190eefd9c |
| Golden cases JSON | reports/generated/rh08-validation-golden-cases.json | materialized | 4facc230da66d9dfd3ef4d5e4360f49a3c8637f0889aaed9d8d92d673b460522 |
| Golden cases Markdown | reports/generated/rh08-validation-golden-cases.md | materialized | 54b24afa41a4d02e27b0aff3d181f1b12b8f986796582caeed2cf660b7c0a88d |
| Validation summary JSON | data/processed/rh08_validation_summary.json | materialized | 809af643378e0f4081949e4a0acddf834dda4555ecd97d2afb83e82c808e0ec3 |
| Validation manifest JSON | data/processed/rh08_validation_manifest.json | materialized | omitted:self-reference |
