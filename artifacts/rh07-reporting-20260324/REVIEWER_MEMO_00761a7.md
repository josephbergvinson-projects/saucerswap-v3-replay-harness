# Reviewer memo — `00761a7`

## Scope
RH-07 turns the reporting surface from a stub into the first real comparison/validation pack on top of mounted RH-04, RH-05, and RH-06 lane artifacts.

## What changed
- Replaces minimal reporting stubs with deterministic aggregate, side, and requested-notional bucket rollups.
- Materializes comparison CSVs plus human-readable comparison, reconciliation, and validation reports.
- Adds explicit Lambdaplex benchmark-status handling so placeholder benchmark data is surfaced instead of silently merged.
- Adds reporting-pack CLI/Make wiring, reusable rollup primitives, and dedicated reporting-pack tests.

## What looks good
- The pack keeps mounted upstream artifacts read-only and makes the comparison surfaces reproducible.
- Validation is explicit: lane rollups are checked back against the mounted lane summaries.
- The reports now make the key tradeoff visible: 3A/3B preserve much lower slippage than V2 baseline, but completion degrades in larger requested-notional buckets.
- Placeholder benchmark data is handled honestly.

## Main implementation risk
- The pack still depends on mounted upstream artifacts and large CSV reads, so rerun cost and artifact-integrity assumptions remain operationally important.

## Main modeling caveat
- RH-07 improves interpretation, not model fidelity. The study is still bounded by the event-level replay contract, the synthetic-lane assumptions in RH-05/RH-06, and the absence of a grounded synthetic/blended fee model.

## Suggested review focus
- `reporting/pack.py` rollup logic and validation joins
- `reporting/tables.py` output contracts and caveat rendering
- bucket segmentation behavior in `config/buckets.yaml`
- the report language around placeholder Lambdaplex data and synthetic-lane caveats
