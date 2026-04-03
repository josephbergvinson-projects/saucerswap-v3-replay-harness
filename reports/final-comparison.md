# Final Comparison Report

## Study caveats

- This pack is an event-level replay benchmark, not an order-level reconstruction or production-fidelity V3 simulator.
- The reporting path reuses mounted RH-03, RH-04, RH-05, and RH-06 artifacts as read-only inputs and does not rebuild those layers.
- Fee outputs use the locked RH-20 contract: V2 applies the fixed WHBAR/USDC trader/LP/protocol split, 3A applies the locked V3 scenarios on pure-book filled notional, and 3B blends V3 pure-book fees with V2 residual-backstop fees when applicable.
- Gross spread capture is reported separately as a resting-book proxy versus the study reference price on filled synthetic-book size. It is not full maker PnL, not explicit V2 LP fee accrual, and not V3 maker rebate.
- All-in trader cost is reported as execution shortfall on filled size plus explicit trader fees, with headline normalization on requested notional for completion-aware comparisons.
- V2 liquidity-side fee output is aggregate active-LP fee accrual, not LP ROI; V3 liquidity-side fee output is maker rebate capture, not full maker PnL.
- Canonical `avg_slippage_bps` remains the study-owned external-reference metric. `avg_amm_pre_trade_spot_gross_slippage_bps` is a separate Lambdaplex-parity proxy based on the RH-13 best-supported reconstructed AMM pre-trade pool spot plus a symmetric reference denominator.
- The current Lambdaplex published panel is placeholder or incomplete in the local benchmark contract, so no benchmark metrics were merged into the comparison tables.

## Headline lane comparison

| Lane | Rows | Fill rate | Avg completion | Avg study slippage (bps) | Avg parity proxy slippage (bps) | Remainder (HBAR) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V2 baseline | 7255957 | 1 | 1 | 19.966868100735 | 15.472290058782 | 0 | Observed realized V2 execution under the event-level replay contract. |
| 3A pure-book | 7255957 | 0.982051114481 | 0.999813179401 | 2.261847743867 | -2.186952348264 | 431584607.835286259651 | Study-owned replenishing synthetic book; partial fills remain explicit. |
| 3B hybrid | 7255957 | 0.989470558433 | 0.999925922904 | 2.261091936527 | -2.18773891321 | 253182566.923353403807 | Mounted 3A fill plus residual V2 backstop only when the frozen admissibility rule passes. |

## Fee-inclusive economics

| Lane | Trader fee (USD) | Liquidity-side earnings (USD) | Protocol earnings (USD) | Execution shortfall (USD) | All-in trader cost (USD) | Trader fee (bps, requested) | All-in cost (bps, requested) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V2 baseline | 5892865.900778388605 | 4910721.583980700001 | 982144.316796322237 | 9555763.063907330856 | 15448628.96468571946 | 15.000000000006 | 39.323724376584 | Fixed V2 fee split: active-LP accrual plus protocol cut. Default reported V3 scenario: v2_fixed. |
| 3A pure-book | 4621382.480131900869 | 77023.041335476708 | 4544359.438796410337 | 1821860.196653133724 | 6443242.676785035059 | 11.76350155751 | 16.400956984113 | Liquidity-side earnings are maker rebates only. Default reported V3 scenario: no_xsauce. V3 min-order ineligible rows surfaced separately: 9729. |
| 3B hybrid | 4672841.251625726931 | 119905.350914102295 | 4552935.90071191173 | 1929948.861754297744 | 6602790.11338002421 | 11.894487326643 | 16.807077128237 | Blended route: V3 pure-book fees plus V2 residual-backstop fees when routed. Default reported V3 scenario: no_xsauce. V3 min-order ineligible rows surfaced separately: 9729. |

## Gross spread capture proxy

Filled resting-book leg only for 3A and the pure-book leg of 3B. This is a study-reference spread-capture proxy, not full maker PnL, not explicit LP fee accrual, and not V3 maker rebate.

| Lane | Rows | Book-leg fill rows | Book-leg filled notional (USD) | Gross spread capture (USD) | Gross spread capture (bps, book leg) | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 3A pure-book | 7255957 | 7255957 | 3851152066.77428817749 | 1821860.196653133724 | 4.730688804452 | Filled resting-book quotes only. Proxy is versus the study reference price, not full maker PnL or V3 rebate. |
| 3B hybrid | 7255957 | 7255957 | 3851152066.77428817749 | 1821860.196653133724 | 4.730688804452 | Pure-book leg only. Excludes the V2 backstop leg, explicit V2 LP fee accrual, and V3 maker rebate. |

Exact figures require materialized `data/processed/lane_3a_pure_book.csv` and `data/processed/lane_3b_hybrid.csv`. If those row-level outputs are absent in the mounted checkout, rerun `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli pure-book --root .`, `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli hybrid --root .`, and `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli reporting-pack --root .`.

## Side split

| Side | Lane | Rows | Fill rate | Avg completion | Avg study slippage (bps) | Avg parity proxy slippage (bps) |
| --- | --- | --- | --- | --- | --- | --- |
| buy | V2 baseline | 3770999 | 1 | 1 | 20.113965383082 | 15.464504914751 |
| buy | 3A pure-book | 3770999 | 0.983074163236 | 0.999819285866 | 2.249938661012 | -2.338069382124 |
| buy | 3B hybrid | 3770999 | 0.991056135566 | 0.999936377292 | 2.248739661386 | -2.339336100196 |
| sell | V2 baseline | 3484958 | 1 | 1 | 19.807697211506 | 15.480714197713 |
| sell | 3A pure-book | 3484958 | 0.981026559784 | 0.999806571725 | 2.274734309669 | -2.023431817006 |
| sell | 3B hybrid | 3484958 | 0.987882647311 | 0.999914610432 | 2.274458071277 | -2.023698818458 |

## Fee side split

| Side | Lane | Trader fee (USD) | Liquidity-side earnings (USD) | Protocol earnings (USD) | All-in cost (bps, requested) |
| --- | --- | --- | --- | --- | --- |
| buy | V2 baseline | 2948018.932033283636 | 2456682.443361248821 | 491336.488672551233 | 38.640606261765 |
| buy | 3A pure-book | 2309875.816310321912 | 38497.930271843332 | 2271377.8860384617 | 16.382993999969 |
| buy | 3B hybrid | 2337666.305457924027 | 61656.67122814816 | 2276009.634229701478 | 16.795680016745 |
| sell | V2 baseline | 2944846.968742064666 | 2454039.140618281439 | 490807.828123782412 | 40.007578293832 |
| sell | 3A pure-book | 2311506.663819153327 | 38525.1110637116 | 2272981.552755231969 | 16.418939316604 |
| sell | 3B hybrid | 2335174.946166247595 | 58248.679686032061 | 2276926.266479551792 | 16.818486515823 |

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

## Fee bucket split

| Bucket | Lane | Trader fee (USD) | Liquidity-side earnings (USD) | Protocol earnings (USD) | All-in cost (bps, requested) |
| --- | --- | --- | --- | --- | --- |
| <1k | V2 baseline | 1843829.448710236233 | 1536524.54059203621 | 307304.908118327439 | 35.367613233724 |
| <1k | 3A pure-book | 1474995.77532736701 | 24583.262922141206 | 1450412.512405366404 | 13.999355658987 |
| <1k | 3B hybrid | 1474995.775327367475 | 24583.262922140908 | 1450412.512405366404 | 13.999355658987 |
| 1k-5k | V2 baseline | 3234033.330350778066 | 2695027.775292416103 | 539005.555058522848 | 38.633671707385 |
| 1k-5k | 3A pure-book | 2587302.081005099695 | 43121.701350119642 | 2544180.379655981436 | 15.463897687953 |
| 1k-5k | 3B hybrid | 2587302.081005099695 | 43121.701350119649 | 2544180.379655981436 | 15.463897687953 |
| 5k-10k | V2 baseline | 417654.466004288872 | 348045.388336791017 | 69609.077667362828 | 37.135824016562 |
| 5k-10k | 3A pure-book | 334114.322766133875 | 5568.572046102227 | 328545.750720037264 | 21.93357719158 |
| 5k-10k | 3B hybrid | 334114.322766133875 | 5568.572046102227 | 328545.750720037264 | 21.93357719158 |
| 10k-25k | V2 baseline | 205131.428841784713 | 170942.857368153636 | 34188.571473630873 | 42.697848003029 |
| 10k-25k | 3A pure-book | 161610.301030387345 | 2693.505017173186 | 158916.796013218904 | 37.910471250018 |
| 10k-25k | 3B hybrid | 164640.651456483756 | 5218.797038920273 | 159421.854417564202 | 38.587783321107 |
| 25k+ | V2 baseline | 192217.226869051519 | 160181.022390876693 | 32036.20447817527 | 90.035594869025 |
| 25k+ | 3A pure-book | 63360 | 1055.999999999966 | 62303.999999997352 | 20.227998515253 |
| 25k+ | 3B hybrid | 111788.421068254072 | 41413.017556878433 | 70375.403511375509 | 31.95573797303 |

## xSAUCE fee scenario sensitivity

| Lane | Scenario | Trader fee (USD) | Liquidity-side earnings (USD) | Protocol earnings (USD) | All-in cost (bps, requested) | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| V2 baseline | v2_fixed | 5892865.900778388605 | 4910721.583980700001 | 982144.316796322237 | 39.323724376584 | Fixed V2 fee split: active-LP accrual plus protocol cut. Default reported V3 scenario: v2_fixed. |
| 3A pure-book | no_xsauce | 4621382.480131900869 | 77023.041335476708 | 4544359.438796410337 | 16.400956984113 | Liquidity-side earnings are maker rebates only. Default reported V3 scenario: no_xsauce. V3 min-order ineligible rows surfaced separately: 9729. |
| 3A pure-book | tier2_10pct | 4159244.232117983513 | 77023.041335476708 | 4082221.190781499725 | 15.22460682836 | Liquidity-side earnings are maker rebates only. Default reported V3 scenario: no_xsauce. V3 min-order ineligible rows surfaced separately: 9729. |
| 3B hybrid | no_xsauce | 4672841.251625726931 | 119905.350914102295 | 4552935.90071191173 | 16.807077128237 | Blended route: V3 pure-book fees plus V2 residual-backstop fees when routed. Default reported V3 scenario: no_xsauce. V3 min-order ineligible rows surfaced separately: 9729. |
| 3B hybrid | tier2_10pct | 4210703.003612215631 | 119905.350914102295 | 4090797.652697045822 | 15.630726972485 | Blended route: V3 pure-book fees plus V2 residual-backstop fees when routed. Default reported V3 scenario: no_xsauce. V3 min-order ineligible rows surfaced separately: 9729. |

## Benchmark panel status

| Benchmark | Status | Comparable | Source notes | Published headline metrics | Provenance | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Lambdaplex published panel | incomplete | false | benchmarks/lambdaplex/source-notes.md | {"reported_average_amm_slippage_bps": 15.47, "reported_claim_scope": "slide-reported published benchmark figures captured for provenance only", "reported_grid_strategy_slippage_bps": 2.82} | local_payload_state=reported_partial_slide_metrics_only \| local_payload_complete=false \| The locally captured Lambdaplex slide values disclose only partial slippage figures and do not provide the required comparable fields or enough methodological detail to map into comparable_headline_metrics. \| mapping_notes=Only comparable_headline_metrics are eligible for merge into reporting outputs.; The slide-reported 15.47 / 2.82 values are stored as raw headline_metrics provenance only.; The harness now also reports a separate `avg_amm_pre_trade_spot_gross_slippage_bps` parity proxy using the RH-13 best-supported reconstructed AMM pre-trade pool-spot gross convention.; That parity proxy is local study output, not a confirmed Lambdaplex methodological disclosure and not a substitute for comparable_headline_metrics.; Required comparable fields still missing locally: fill_rate, avg_completion_ratio, avg_abs_slippage_bps, remainder_size_hbar.; Weighting basis, reference-price convention, fee treatment, and completion/failure treatment are not disclosed well enough to normalize the slide values into the study schema. \| captured_artifacts=benchmarks/lambdaplex/published-results.json, benchmarks/lambdaplex/source-notes.md, operator-provided Lambdaplex slide screenshots (2026-03-25) | Published panel is placeholder or incomplete; no comparable benchmark metrics were merged. Populate comparable_headline_metrics only from locally tracked published Lambdaplex outputs with explicit mapping support. Do not treat the slide-reported 15.47 / 2.82 bps figures as apples-to-apples comparable with the study rollups yet. Use the local `avg_amm_pre_trade_spot_gross_slippage_bps` field only as a best-supported Lambdaplex-parity proxy, not as confirmation of Lambdaplex's undisclosed methodology. Do not invent benchmark values when rerunning reporting-pack. |

Lambdaplex market: `HBAR/USDC`
Lambdaplex benchmark schema: `rh09_lambdaplex_published_panel_v1`
