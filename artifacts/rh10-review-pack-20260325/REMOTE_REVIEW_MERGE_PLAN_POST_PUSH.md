# Remote Review / Merge Plan — RH-05 through RH-10

## Scope
This plan assumes the full RH-05 through RH-10 branch stack has been pushed to `origin` and is ready for remote review.

## Remote review order
Review in dependency order:

1. `feat/ssv3-rh05-3a-pure-book`
2. `feat/ssv3-rh06-3b-hybrid-lane`
3. `feat/ssv3-rh07-reporting-pack`
4. `feat/ssv3-rh08-validation-polish`
5. `feat/ssv3-rh09-lambdaplex-benchmark-panel`
6. `feat/ssv3-rh10-review-pack-closeout`

## What each review should answer
- RH-05: does the pure-book lane work, and are partial/unfilled outcomes explicit and deterministic?
- RH-06: does the hybrid residual-backstop improve completion without undermining interpretability?
- RH-07: do reporting outputs make the real study tradeoffs visible at aggregate, side, and bucket level?
- RH-08: is the validation evidence explicit enough to support internal trust in the study outputs?
- RH-09: is the Lambdaplex benchmark contract honest, provenance-aware, and safe against fabricated merges?
- RH-10: does the closeout pack compress the accepted evidence honestly without overstating what the study proves?

## Recommended reviewer read path
1. `reports/review-pack-closeout.md`
2. `artifacts/rh10-review-pack-20260325/FINAL_INTERNAL_DECISION_MEMO_RH10.md`
3. `artifacts/rh09-benchmark-20260325/INTERNAL_REVIEW_MEMO_RH04_RH09.md`
4. `artifacts/rh09-benchmark-20260325/reporting-root/reports/final-comparison.md`
5. `artifacts/rh09-benchmark-20260325/reporting-root/reports/validation.md`
6. `benchmarks/lambdaplex/source-notes.md`

## Merge / normalization options

### Option A — preserve stack
Use if you want the repo to preserve the lane-by-lane study build history.
- Keep RH-05 through RH-10 as review-visible branches.
- Merge or retain each lane in order.
- Keep RH-10 as the compact top-level reading surface, not the only surviving history.

### Option B — single-closeout presentation
Use if you want one obvious top branch for most readers.
- Treat RH-10 as the presentation branch.
- Preserve RH-05 through RH-09 branch tips or tags for audit/history.
- Normalize future readers onto RH-10 while keeping the lower lanes available for forensic review.

## Merge gate before calling the study fully closed out
Do not treat push/merge as scientific closure. The remaining study-level blockers remain:
- Lambdaplex comparable headline metrics are still missing locally.
- Large-clip parity with realized V2 is not shown.
- The study is still event-level, not order-level.
- `3A` / `3B` still lack a grounded fee model.

## Recommended decision rule
- If the goal is internal directional product/strategy review: RH-10 is ready.
- If the goal is external or parity-strength claims: stop at internal review and explicitly carry the remaining blockers forward.
