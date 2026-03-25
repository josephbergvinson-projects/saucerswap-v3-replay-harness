# Reviewer memo — `d78c852`

## Scope
RH-09 closes the Lambdaplex benchmark-ingestion gap at the contract/reporting layer on top of the accepted RH-08 study state.

## What changed
- Replaces the flat placeholder benchmark stub with a structured local benchmark contract and loader.
- Makes provenance explicit via tracked source notes and schema fields.
- Updates reporting so benchmark metrics can merge only when locally recorded data is genuinely comparable.
- Hardens tests around placeholder vs comparable benchmark behavior.

## What looks good
- The lane is honest: it improves the benchmark surface without inventing missing benchmark numbers.
- Comparable-vs-placeholder behavior is now deterministic and test-covered.
- Reporting artifacts can now carry benchmark provenance cleanly instead of a vague placeholder note.
- Acceptance avoided mutating mounted upstream artifacts by using an isolated reporting root.

## Main implementation risk
- RH-09 solves the software/provenance contract, not the underlying data availability problem. Reviewers should not mistake a better benchmark interface for actual benchmark evidence.

## Main modeling caveat
- The external benchmark gap remains real: Lambdaplex still cannot be used in headline performance claims until real comparable headline metrics are recorded locally.

## Suggested review focus
- `benchmarks/lambdaplex.py` schema/comparability contract
- `reporting/pack.py` and `reporting/tables.py` merge rules for benchmark rows
- `published-results.json` and `source-notes.md` wording around provenance vs comparable metrics
