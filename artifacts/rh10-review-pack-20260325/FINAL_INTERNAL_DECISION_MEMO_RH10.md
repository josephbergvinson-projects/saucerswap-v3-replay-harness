# Final Internal Decision Memo — RH-10

## Objective

Package the accepted first-pass SaucerSwap V3 replay study into one compact internal decision surface that makes the positive signal, the hard caveats, and the unresolved external benchmark blocker obvious.

## TL;DR

The study now supports an internal directional conclusion: the hybrid lane (`3B`) is materially better than pure-book (`3A`) on completion while preserving the same low-slippage profile. That is enough to justify internal product / strategy discussion for ordinary-flow behavior.

The study does **not** support two stronger claims:
- large-clip parity with realized V2 execution
- Lambdaplex benchmark parity or outperformance

Those remain blocked by the current model limitations and the absence of locally recorded comparable Lambdaplex headline metrics.

## Decision table

| Question | Decision | Evidence |
| --- | --- | --- |
| Does `3B hybrid` beat `3A pure-book` directionally? | Yes. | Overall fill rate improves from `0.9821` to `0.9877`; remainder falls from `431.6M` to `295.6M` HBAR; partial fills fall from `28,789` to `3,200`; average slippage stays about `2.26` bps. |
| Does the hybrid improvement come from giving back the slippage advantage? | No. | `3A` average slippage is `2.2618` bps and `3B` is `2.2605` bps; the low-slippage profile is preserved rather than traded away. |
| Is ordinary-flow behavior strong enough for internal discussion? | Yes, directionally. | In `<1k`, `1k-5k`, and `5k-10k`, both study-owned lanes show `fill_rate=1.0`; slippage remains well below realized V2 in all three buckets. |
| Is large-clip parity with realized V2 shown? | No. | In `25k+`, fill rate is `0.4216` for `3A`, `0.5984` for `3B`, and `1.0` for realized V2. `3B` improves materially on `3A` but still falls short of parity. |
| Is Lambdaplex parity / outperformance shown? | No. Blocked. | The tracked local benchmark contract is `placeholder`, `comparable=false`, and carries the explicit blocker that comparable headline metrics are not recorded locally. |
| Is the study reviewable enough for internal use? | Yes. | RH-07 reporting, RH-08 validation polish, and RH-09 benchmark provenance handling are all materialized locally and pass their accepted consistency/validation surfaces. |

## Numbers that matter

### Overall lane comparison

| Lane | Fill rate | Avg completion | Avg slippage (bps) | Remainder (HBAR) | Partial fills |
| --- | --- | --- | --- | --- | --- |
| V2 baseline | `1.0` | `1.0` | `19.9669` | `0` | `0` |
| 3A pure-book | `0.9821` | `0.9998` | `2.2618` | `431,584,607.8` | `28,789` |
| 3B hybrid | `0.9877` | `0.9999` | `2.2605` | `295,569,026.4` | `3,200` |

### Bucket read

| Bucket | V2 fill rate | 3A fill rate | 3B fill rate | Practical read |
| --- | --- | --- | --- | --- |
| `<1k` | `1.0` | `1.0` | `1.0` | No completion gap appears in this bucket; synthetic lanes retain much lower slippage than V2. |
| `1k-5k` | `1.0` | `1.0` | `1.0` | Same directional read as `<1k`. |
| `5k-10k` | `1.0` | `1.0` | `1.0` | Same directional read as `<1k`. |
| `10k-25k` | `1.0` | `0.9851` | `0.9943` | `3B` improves on `3A`, but a completion gap versus V2 starts to show. |
| `25k+` | `1.0` | `0.4216` | `0.5984` | This is still the main weakness of the current synthetic assumptions. |

## What the study now supports

- A strong directional claim that the hybrid residual-backstop design is materially better than pure-book under the current first-pass replay contract.
- A strong claim that the low-slippage benefit of the study-owned lanes is real in the accepted outputs.
- A segmented internal-use claim that mostly sub-`10k` requested-notional flow is the current strongest region for further product / strategy discussion.
- A process claim that the study is locally reproducible, auditable, and reviewable enough for an internal decision memo rather than only an exploratory notebook.

## What the study still does not support

- Any claim that the current modeled design is a replacement for realized V2 execution at large clip sizes.
- Any claim that the study-owned lanes match or beat Lambdaplex on a comparable headline basis.
- Any claim that the current replay harness is an order-level or production-fidelity simulation.
- Any fee-aware economic conclusion for `3A` or `3B`, because the current phase still carries `fees_paid=0.0` for those lanes.

## Remaining blockers and caveats

1. **External benchmark blocker**
   - The Lambdaplex benchmark contract/software path is now explicit and safe.
   - The missing piece is still the data: comparable published headline metrics are not yet recorded locally.
   - Until that changes, benchmark parity or outperformance claims should be treated as out of scope.

2. **Large-clip completion blocker**
   - `3B` improves materially on `3A`, but `25k+` fill rate is still `0.5984` versus `1.0` for realized V2.
   - The current first-pass study therefore does not establish large-clip replacement viability.

3. **Model-fidelity caveat**
   - This is still an event-level replay benchmark rather than an order-level reconstruction.
   - Reviewers should treat the results as directional under the locked contract, not as production-execution forecasts.

4. **Fee-model caveat**
   - `3A` and `3B` still lack a grounded synthetic / blended fee model.
   - Slippage conclusions are visible; fee-adjusted economics are not.

## Recommended internal decision

Use this study as a **directional internal input**, not a parity certificate.

Concretely:
- proceed with internal discussion on the hybrid design and ordinary-flow behavior
- do **not** present the current study as proving large-clip parity with realized V2
- do **not** present the current study as proving Lambdaplex parity / outperformance
- treat the next high-value gates as: comparable Lambdaplex data capture, large-clip model improvement, and any future fee-aware pass

## Evidence sources

Accepted benchmark-aware reporting root from RH-09:
- `artifacts/rh09-benchmark-20260325/reporting-root/data/processed/reporting_pack_summary.json`
- `artifacts/rh09-benchmark-20260325/reporting-root/reports/final-comparison.md`
- `artifacts/rh09-benchmark-20260325/reporting-root/reports/reconciliation.md`
- `artifacts/rh09-benchmark-20260325/reporting-root/reports/validation.md`

Accepted validation support from RH-08:
- `data/processed/rh08_validation_summary.json`

Benchmark provenance contract:
- `benchmarks/lambdaplex/published-results.json`
- `benchmarks/lambdaplex/source-notes.md`

## Interpretation boundary

All metrics above are compressed from the accepted outputs cited here. RH-10 adds decision framing and closeout packaging only. It does not reopen provenance hunting, regenerate mounted artifacts, or invent missing benchmark values.
