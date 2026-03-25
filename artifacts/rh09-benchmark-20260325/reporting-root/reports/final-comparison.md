# Final Comparison Report

## Study caveats

- This pack is an event-level replay benchmark, not an order-level reconstruction or production-fidelity V3 simulator.
- The reporting path reuses mounted RH-03, RH-04, RH-05, and RH-06 artifacts as read-only inputs and does not rebuild those layers.
- 3A and 3B still carry `fees_paid=0.0` because the current phase has no grounded synthetic or blended fee model.
- The current Lambdaplex published panel is placeholder or incomplete in the local benchmark contract, so no benchmark metrics were merged into the comparison tables.

## Headline lane comparison

| Lane | Rows | Fill rate | Avg completion | Avg slippage (bps) | Remainder (HBAR) | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| V2 baseline | 7255957 | 1 | 1 | 19.966868100735 | 0 | Observed realized V2 execution under the event-level replay contract. |
| 3A pure-book | 7255957 | 0.982051114481 | 0.999813179401 | 2.261847743867 | 431584607.835286259651 | Study-owned replenishing synthetic book; partial fills remain explicit. |
| 3B hybrid | 7255957 | 0.98770777613 | 0.999901267765 | 2.260514999438 | 295569026.42833083868 | Mounted 3A fill plus residual V2 backstop only when the frozen admissibility rule passes. |

## Side split

| Side | Lane | Rows | Fill rate | Avg completion | Avg slippage (bps) |
| --- | --- | --- | --- | --- | --- |
| buy | V2 baseline | 3770999 | 1 | 1 | 20.113965383082 |
| buy | 3A pure-book | 3770999 | 0.983074163236 | 0.999819285866 | 2.249938661012 |
| buy | 3B hybrid | 3770999 | 0.989089882113 | 0.999910662713 | 2.24815820165 |
| sell | V2 baseline | 3484958 | 1 | 1 | 19.807697211506 |
| sell | 3A pure-book | 3484958 | 0.981026559784 | 0.999806571725 | 2.274734309669 |
| sell | 3B hybrid | 3484958 | 0.986323635668 | 0.999891101691 | 2.273886028047 |

## Bucket split

| Bucket | Lane | Rows | Requested notional (USDC) | Fill rate | Avg completion | Avg slippage (bps) |
| --- | --- | --- | --- | --- | --- | --- |
| <1k | V2 baseline | 6034242 | 1229219632.47347 | 1 | 1 | 19.234413439835 |
| <1k | 3A pure-book | 6034242 | 1229219632.47347 | 1 | 1 | 2.000191311834 |
| <1k | 3B hybrid | 6034242 | 1229219632.47347 | 1 | 1 | 2.000191311666 |
| 1k-5k | V2 baseline | 1165115 | 2156022220.233877 | 1 | 1 | 23.520931891209 |
| 1k-5k | 3A pure-book | 1165115 | 2156022220.233877 | 1 | 1 | 3.073675293403 |
| 1k-5k | 3B hybrid | 1165115 | 2156022220.233877 | 1 | 1 | 3.073675293403 |
| 5k-10k | V2 baseline | 44226 | 278436310.669434 | 1 | 1 | 22.417523452719 |
| 5k-10k | 3A pure-book | 44226 | 278436310.669434 | 1 | 1 | 9.591722916248 |
| 5k-10k | 3B hybrid | 44226 | 278436310.669434 | 1 | 1 | 9.591722916248 |
| 10k-25k | V2 baseline | 9734 | 136754285.894524 | 1 | 1 | 27.214279808663 |
| 10k-25k | 3A pure-book | 9734 | 136754285.894524 | 0.985056295039 | 0.990562075735 | 24.525290187137 |
| 10k-25k | 3B hybrid | 9734 | 136754285.894524 | 0.994271699167 | 0.997076310936 | 24.378361137233 |
| 25k+ | V2 baseline | 2640 | 128144817.912701 | 1 | 1 | 57.84032380474 |
| 25k+ | 3A pure-book | 2640 | 128144817.912701 | 0.421620518287 | 0.521328227636 | 37.16426009997 |
| 25k+ | 3B hybrid | 2640 | 128144817.912701 | 0.598377402399 | 0.739417552154 | 34.042999540549 |

## Benchmark panel status

| Benchmark | Status | Comparable | Source notes | Published headline metrics | Provenance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Lambdaplex published panel | placeholder | false | benchmarks/lambdaplex/source-notes.md |  | local_payload_state=placeholder_only \| local_payload_complete=false \| Comparable Lambdaplex headline metrics are not recorded locally in this worktree, so RH-09 can only ship the ingestion contract and explicit blocker handling. \| mapping_notes=Only comparable_headline_metrics are eligible for merge into reporting outputs.; Raw headline_metrics remain provenance-only until explicitly mapped. \| captured_artifacts=benchmarks/lambdaplex/published-results.json, benchmarks/lambdaplex/source-notes.md | Published panel is placeholder or incomplete; no comparable benchmark metrics were merged. Populate this payload only from locally tracked published Lambdaplex outputs. Do not invent benchmark values when rerunning reporting-pack. |

Lambdaplex market: `HBAR/USDC`
Lambdaplex benchmark schema: `rh09_lambdaplex_published_panel_v1`
