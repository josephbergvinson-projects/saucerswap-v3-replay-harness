# Final Comparison Report

## Study caveats

- This pack is an event-level replay benchmark, not an order-level reconstruction or production-fidelity V3 simulator.
- The reporting path reuses mounted RH-03, RH-04, RH-05, and RH-06 artifacts as read-only inputs and does not rebuild those layers.
- 3A and 3B still carry `fees_paid=0.0` because the current phase has no grounded synthetic or blended fee model.
- Canonical `avg_slippage_bps` remains the study-owned external-reference metric. `avg_amm_pre_trade_spot_gross_slippage_bps` is a separate Lambdaplex-parity proxy based on the RH-13 best-supported reconstructed AMM pre-trade pool spot plus a symmetric reference denominator.
- The current Lambdaplex published panel is placeholder or incomplete in the local benchmark contract, so no benchmark metrics were merged into the comparison tables.

## Headline lane comparison

| Lane | Rows | Fill rate | Avg completion | Avg study slippage (bps) | Avg parity proxy slippage (bps) | Remainder (HBAR) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V2 baseline | 7255957 | 1 | 1 | 19.966868100735 | 15.472290058782 | 0 | Observed realized V2 execution under the event-level replay contract. |
| 3A pure-book | 7255957 | 0.982051114481 | 0.999813179401 | 2.261847743867 | -2.186952348264 | 431584607.835286259651 | Study-owned replenishing synthetic book; partial fills remain explicit. |
| 3B hybrid | 7255957 | 0.989470558433 | 0.999925922904 | 2.261091936527 | -2.18773891321 | 253182566.923353403807 | Mounted 3A fill plus residual V2 backstop only when the frozen admissibility rule passes. |

## Side split

| Side | Lane | Rows | Fill rate | Avg completion | Avg study slippage (bps) | Avg parity proxy slippage (bps) |
| --- | --- | --- | --- | --- | --- | --- |
| buy | V2 baseline | 3770999 | 1 | 1 | 20.113965383082 | 15.464504914751 |
| buy | 3A pure-book | 3770999 | 0.983074163236 | 0.999819285866 | 2.249938661012 | -2.338069382124 |
| buy | 3B hybrid | 3770999 | 0.991056135566 | 0.999936377292 | 2.248739661386 | -2.339336100196 |
| sell | V2 baseline | 3484958 | 1 | 1 | 19.807697211506 | 15.480714197713 |
| sell | 3A pure-book | 3484958 | 0.981026559784 | 0.999806571725 | 2.274734309669 | -2.023431817006 |
| sell | 3B hybrid | 3484958 | 0.987882647311 | 0.999914610432 | 2.274458071277 | -2.023698818458 |

## Bucket split

| Bucket | Lane | Rows | Requested notional (USDC) | Fill rate | Avg completion | Avg study slippage (bps) | Avg parity proxy slippage (bps) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <1k | V2 baseline | 6034242 | 1229219632.47347 | 1 | 1 | 19.234413439835 | 15.184247820931 |
| <1k | 3A pure-book | 6034242 | 1229219632.47347 | 1 | 1 | 2.000191311834 | -2.009495178662 |
| <1k | 3B hybrid | 6034242 | 1229219632.47347 | 1 | 1 | 2.000191311666 | -2.009495178811 |
| 1k-5k | V2 baseline | 1165115 | 2156022220.233877 | 1 | 1 | 23.520931891209 | 16.525407976454 |
| 1k-5k | 3A pure-book | 1165115 | 2156022220.233877 | 1 | 1 | 3.073675293403 | -3.853673561201 |
| 1k-5k | 3B hybrid | 1165115 | 2156022220.233877 | 1 | 1 | 3.073675293403 | -3.853673561187 |
| 5k-10k | V2 baseline | 44226 | 278436310.669434 | 1 | 1 | 22.417523452719 | 20.090822903854 |
| 5k-10k | 3A pure-book | 44226 | 278436310.669434 | 1 | 1 | 9.591722916248 | 7.373248320037 |
| 5k-10k | 3B hybrid | 44226 | 278436310.669434 | 1 | 1 | 9.591722916248 | 7.373248319901 |
| 10k-25k | V2 baseline | 9734 | 136754285.894524 | 1 | 1 | 27.214279808663 | 32.417937489044 |
| 10k-25k | 3A pure-book | 9734 | 136754285.894524 | 0.985056295039 | 0.990562075735 | 24.525290187137 | 29.926721090273 |
| 10k-25k | 3B hybrid | 9734 | 136754285.894524 | 0.999085179852 | 0.999562502701 | 24.467398459587 | 29.867082861841 |
| 25k+ | V2 baseline | 2640 | 128144817.912701 | 1 | 1 | 57.84032380474 | 69.224154100523 |
| 25k+ | 3A pure-book | 2640 | 128144817.912701 | 0.421620518287 | 0.521328227636 | 37.16426009997 | 49.213974921147 |
| 25k+ | 3B hybrid | 2640 | 128144817.912701 | 0.651080608121 | 0.798014535901 | 35.300401592967 | 47.272019609657 |

## Benchmark panel status

| Benchmark | Status | Comparable | Source notes | Published headline metrics | Provenance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Lambdaplex published panel | incomplete | false | benchmarks/lambdaplex/source-notes.md | {"reported_average_amm_slippage_bps": 15.47, "reported_claim_scope": "slide-reported published benchmark figures captured for provenance only", "reported_grid_strategy_slippage_bps": 2.82} | local_payload_state=reported_partial_slide_metrics_only \| local_payload_complete=false \| The locally captured Lambdaplex slide values disclose only partial slippage figures and do not provide the required comparable fields or enough methodological detail to map into comparable_headline_metrics. \| mapping_notes=Only comparable_headline_metrics are eligible for merge into reporting outputs.; The slide-reported 15.47 / 2.82 values are stored as raw headline_metrics provenance only.; The harness now also reports a separate `avg_amm_pre_trade_spot_gross_slippage_bps` parity proxy using the RH-13 best-supported reconstructed AMM pre-trade pool-spot gross convention.; That parity proxy is local study output, not a confirmed Lambdaplex methodological disclosure and not a substitute for comparable_headline_metrics.; Required comparable fields still missing locally: fill_rate, avg_completion_ratio, avg_abs_slippage_bps, remainder_size_hbar.; Weighting basis, reference-price convention, fee treatment, and completion/failure treatment are not disclosed well enough to normalize the slide values into the study schema. \| captured_artifacts=benchmarks/lambdaplex/published-results.json, benchmarks/lambdaplex/source-notes.md, operator-provided Lambdaplex slide screenshots (2026-03-25) | Published panel is placeholder or incomplete; no comparable benchmark metrics were merged. Populate comparable_headline_metrics only from locally tracked published Lambdaplex outputs with explicit mapping support. Do not treat the slide-reported 15.47 / 2.82 bps figures as apples-to-apples comparable with the study rollups yet. Use the local `avg_amm_pre_trade_spot_gross_slippage_bps` field only as a best-supported Lambdaplex-parity proxy, not as confirmation of Lambdaplex's undisclosed methodology. Do not invent benchmark values when rerunning reporting-pack. |

Lambdaplex market: `HBAR/USDC`
Lambdaplex benchmark schema: `rh09_lambdaplex_published_panel_v1`
