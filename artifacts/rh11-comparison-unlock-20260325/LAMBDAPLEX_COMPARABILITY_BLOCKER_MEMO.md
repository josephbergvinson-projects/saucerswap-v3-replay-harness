# RH-11 comparison unlock blocker memo — Lambdaplex

## Decision

Do **not** promote `benchmarks/lambdaplex/published-results.json` from `incomplete` to `comparable`.

On the current main-equivalent state in this worktree, the locally available evidence is still insufficient to populate `comparable_headline_metrics` honestly.

## Local evidence sweep performed

Searched the repo and nearby workspace-local files for Lambdaplex benchmark evidence, including:

- `benchmarks/lambdaplex/published-results.json`
- `benchmarks/lambdaplex/source-notes.md`
- `artifacts/rh11-benchmark-reconciliation-20260325/LAMBDAPLEX_15_47_2_82_SCHEMA_RECONCILIATION.md`
- `artifacts/rh09-benchmark-20260325/reporting-root/reports/final-comparison.md`
- `artifacts/rh12-large-clip-20260325/reporting_rerun_stdout.json`
- planning docs under `docs/planning/`
- workspace-local text/json/html/md hits for `Lambdaplex`
- workspace-local image/pdf candidates under the repo and nearby workspace

## What exists locally

- The tracked benchmark contract and source notes.
- The already-captured provenance-only slide values:
  - `reported_average_amm_slippage_bps = 15.47`
  - `reported_grid_strategy_slippage_bps = 2.82`
- Prior RH-11 reconciliation notes that already conclude the two slide values are not schema-comparable.
- Reporting outputs that confirm no comparable Lambdaplex row was merged into the comparison tables.
- Planning docs that describe Lambdaplex only as a published benchmark panel, not as a locally reconstructed methodology pack.

## What does **not** exist locally

- No workspace-local Lambdaplex methodology export that discloses the benchmark normalization rules.
- No workspace-local published benchmark row/table that gives or lets us derive all required comparable fields.
- No workspace-local image/PDF artifact for the Lambdaplex benchmark beyond the generic planning PDFs already in the repo.
- No local proof that the slide's `grid strategy` label is semantically identical to our `3A pure-book`, `3B hybrid`, or another merge-safe lane definition.

## Exact missing evidence still required

At minimum, a grounded published source available locally that discloses or lets us derive:

1. `fill_rate`
2. `avg_completion_ratio`
3. `avg_slippage_bps`
4. `avg_abs_slippage_bps`
5. `remainder_size_hbar`

And the methodological basis needed to normalize those fields safely:

- weighting basis for the reported averages
- reference-price convention
- fee inclusion / exclusion treatment
- failure / partial-fill / remainder treatment
- exact semantic mapping for the published `grid strategy` label

## Current downstream reporting state

Current local reporting already reflects the block:

- `artifacts/rh09-benchmark-20260325/reporting-root/reports/final-comparison.md`
  - states that the local Lambdaplex panel is placeholder/incomplete and no benchmark metrics were merged
- `artifacts/rh12-large-clip-20260325/reporting_rerun_stdout.json`
  - preserves the same `incomplete` benchmark status and blocker summary

## Conclusion

No honest unlock is possible from the locally available published evidence currently present in this workspace.

Safe claim:

> Lambdaplex's published panel is still tracked locally only as provenance-level slide values (`15.47` / `2.82` bps). It remains non-comparable because the required headline fields and normalization methodology are still not available locally.
