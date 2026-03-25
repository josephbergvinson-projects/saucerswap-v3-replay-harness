# RH-05 through RH-10 — Push / Closeout Path

## Current local stacked branch state

| Lane | Review branch tip | Tip subject | Core implementation commit | Tracker state |
|---|---|---|---|---|
| RH-05 | `feat/ssv3-rh05-3a-pure-book` @ `1babf4d` | `feat: add RH-05 pure-book lane` | `1babf4d` | needs Trello review card closeout sync |
| RH-06 | `feat/ssv3-rh06-3b-hybrid-lane` @ `3e2972f` | `docs: add RH-06 reviewer memo` | `0b302a9` | needs Trello review card closeout sync |
| RH-07 | `feat/ssv3-rh07-reporting-pack` @ `763f06a` | `docs: add RH-07 reviewer memo` | `00761a7` | needs Trello review card closeout sync |
| RH-08 | `feat/ssv3-rh08-validation-polish` @ `abe9394` | `docs: add RH-08 reviewer memo` | `01ace26` | Review |
| RH-09 | `feat/ssv3-rh09-lambdaplex-benchmark-panel` @ `bd4c8f5` | `docs: add RH-09 review memos` | `d78c852` | Review |
| RH-10 | `feat/ssv3-rh10-review-pack-closeout` @ `184c0b4` | `docs: add RH-10 final review pack closeout` | `184c0b4` | Review |

## Recommended push strategy

Use a stacked-history push, not a squash-first shortcut.

Reason:
- the study was built as a true dependency chain
- each lane has its own acceptance evidence and reviewer memo surface
- RH-10 is a closeout layer on top of accepted RH-09 evidence, not a substitute for the lower layers

## Recommended push order

Push the branch tips in dependency order:

1. `feat/ssv3-rh05-3a-pure-book` @ `1babf4d`
2. `feat/ssv3-rh06-3b-hybrid-lane` @ `3e2972f`
3. `feat/ssv3-rh07-reporting-pack` @ `763f06a`
4. `feat/ssv3-rh08-validation-polish` @ `abe9394`
5. `feat/ssv3-rh09-lambdaplex-benchmark-panel` @ `bd4c8f5`
6. `feat/ssv3-rh10-review-pack-closeout` @ `184c0b4`

## Recommended review order

Review in the same order as the push order.

What each lane answers:
- RH-05: does the pure-book lane work and keep partial/unfilled cases explicit?
- RH-06: does the hybrid backstop improve completion without breaking interpretability?
- RH-07: do the comparison/reporting surfaces express the actual study tradeoffs?
- RH-08: is the validation evidence explicit enough to trust the reports?
- RH-09: is the Lambdaplex benchmark contract honest and merge-safe without fabricating values?
- RH-10: does the closeout memo compress the evidence honestly without overstating what the study proves?

## Suggested remote closeout flow

### Phase A — publish the stack
- push all six branch tips in order
- preserve the current stacked shape until review completes
- do **not** collapse the stack before review, because the lane-by-lane evidence is part of the audit trail

### Phase B — review / sign-off
- use the reviewer memos at each tip to accelerate review
- keep RH-10 as the top-level reading surface, but require reviewers to inspect RH-07/RH-08/RH-09 evidence for the key claims

### Phase C — merge / normalization decision
Choose one of these two closeout modes after review:

1. **Preserve-stack mode**
   - keep the historical branch chain intact on remote
   - merge or retain each lane as a review branch
   - best if the repo is intended to preserve lane-by-lane study history

2. **Single-closeout mode**
   - treat RH-10 as the presentation branch
   - preserve the lower lane commits as history/tags
   - best if the repo is intended to expose one final closeout branch to most readers

## Trello closeout path

Current truthful Trello state:
- RH-08 — Review
- RH-09 — Review
- RH-10 — Review

For full-stack closeout, add/sync RH-05, RH-06, and RH-07 review cards before or alongside the push so the board matches the real branch stack.

After remote publication and review sign-off:
- move RH-05 through RH-10 from `Review` to `Done`
- add one final closeout comment per card with:
  - pushed branch tip
  - review outcome
  - whether the lane is preserved as a branch, merged, or superseded by the RH-10 closeout layer

## Remaining blockers before claiming final program closeout

These are study blockers, not branch-prep blockers:
- Lambdaplex comparable headline metrics are still missing locally
- large-clip parity with realized V2 is still not shown
- the study is still event-level, not order-level
- `3A` / `3B` still lack a grounded fee model

## Minimal operator read path before pushing

1. `reports/review-pack-closeout.md`
2. `artifacts/rh10-review-pack-20260325/FINAL_INTERNAL_DECISION_MEMO_RH10.md`
3. `artifacts/rh09-benchmark-20260325/INTERNAL_REVIEW_MEMO_RH04_RH09.md`
4. `artifacts/rh09-benchmark-20260325/reporting-root/reports/final-comparison.md`
5. `artifacts/rh09-benchmark-20260325/reporting-root/reports/validation.md`
6. `benchmarks/lambdaplex/source-notes.md`

## Ready state

The local branch stack is ready for push preparation. No further technical implementation is required before a supervised publication/review pass.
