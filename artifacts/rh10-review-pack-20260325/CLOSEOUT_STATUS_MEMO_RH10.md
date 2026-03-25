# Closeout Status Memo — RH-10

## What RH-10 closes

RH-10 closes the first-pass study as an internal review-pack lane.

It does **not** add a new modeling pass. It packages the accepted RH-04 through RH-09 outputs into a compact, caveat-forward closeout surface so a reviewer can answer three questions quickly:
- what is complete
- what is still blocked
- what decision signal is actually supported

## Status by topic

| Topic | Status | Notes |
| --- | --- | --- |
| RH-04 realized V2 baseline | complete | Accepted and already mounted into the current study state. |
| RH-05 pure-book lane | complete | Accepted and already mounted into the current study state. |
| RH-06 hybrid lane | complete | Accepted and already mounted into the current study state. |
| RH-07 reporting pack | complete | Accepted comparison / reconciliation / validation surfaces exist. |
| RH-08 validation polish | complete | Sampled realized-V2 sanity checks and golden cases are materialized and passing. |
| RH-09 benchmark contract / provenance handling | complete | Software contract is explicit, merge-safe, and honest about placeholder benchmark status. |
| RH-10 final review pack / closeout | complete for local internal review | This memo set and index compress the accepted study into one reading path. |
| Lambdaplex benchmark parity/outperformance claim | blocked | Comparable local benchmark headline values are still not recorded locally. |
| Large-clip parity with realized V2 | not shown | `25k+` completion remains materially below realized V2. |
| Fee-aware economics for 3A / 3B | not complete | Current study-owned lanes still carry `fees_paid=0.0`. |
| Order-level / production-fidelity simulation claim | not in scope | The first-pass study remains event-level only. |

## What is complete enough to rely on now

- The study can support an internal directional statement that `3B hybrid` is better than `3A pure-book` on completion while keeping the low-slippage profile.
- The accepted reporting and validation surfaces are sufficient for internal audit/review.
- The Lambdaplex benchmark ingestion/provenance path is explicit enough that the current blocker is now clearly a missing-data problem, not a hidden software ambiguity.

## What remains blocked

### 1. Comparable Lambdaplex benchmark values

Blocked by missing local benchmark data, not by missing software support.

Current explicit benchmark state:
- `status=placeholder`
- `comparable=false`
- blocking reason: comparable Lambdaplex headline metrics are not recorded locally in this worktree

Implication:
- do not claim benchmark parity
- do not claim benchmark outperformance
- do not backfill or infer missing benchmark values

### 2. Large-clip replacement claim

The study still does not show parity with realized V2 for large clips.

Current accepted `25k+` fill rates:
- V2 baseline: `1.0`
- 3A pure-book: `0.4216`
- 3B hybrid: `0.5984`

Implication:
- `3B` is directionally better than `3A`
- `3B` is still not good enough to claim replacement parity under the current locked contract

### 3. Fee-model completeness

`3A` and `3B` still have `fees_paid=0.0` in the current pass.

Implication:
- current study supports slippage/completion interpretation
- current study does not support fee-adjusted economics or net-cost conclusions for the study-owned lanes

## Review path

Recommended reading order:

1. `reports/review-pack-closeout.md`
2. `artifacts/rh10-review-pack-20260325/FINAL_INTERNAL_DECISION_MEMO_RH10.md`
3. `artifacts/rh10-review-pack-20260325/CLOSEOUT_STATUS_MEMO_RH10.md`
4. `artifacts/rh10-review-pack-20260325/INDEX.md`
5. `artifacts/rh09-benchmark-20260325/reporting-root/reports/final-comparison.md`
6. `artifacts/rh09-benchmark-20260325/reporting-root/reports/validation.md`
7. `benchmarks/lambdaplex/source-notes.md`

## Rerun / reproducibility notes

- RH-10 itself is a docs/artifact compression lane; it does not regenerate upstream modeling outputs.
- The accepted benchmark-aware reporting outputs to trust for this closeout are the isolated RH-09 reporting-root artifacts under `artifacts/rh09-benchmark-20260325/reporting-root/`.
- Mounted `data/processed/` inputs were treated as read-only.
- No mounted upstream artifact paths were mutated by RH-10.

If comparable Lambdaplex headline metrics are later recorded locally under the tracked benchmark contract, the next rerun point is:

```bash
cd /Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness
make reporting-pack
```

## Closeout statement

The first-pass SaucerSwap V3 replay study is now **locally review-ready for internal decision use**.

That means:
- the directional decision signal is visible
- the evidence pack is compact enough for review
- the audit surfaces exist
- the remaining blockers are explicit

It does **not** mean:
- benchmark parity is shown
- large-clip parity is shown
- the study is ready to be represented as production-fidelity execution evidence
