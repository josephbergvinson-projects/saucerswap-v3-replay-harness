# RH-09 Lambdaplex Benchmark Panel — Artifact Index

Date: 2026-03-25
Branch: feat/ssv3-rh09-lambdaplex-benchmark-panel
Worktree: /Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness/.worktrees/feat-ssv3-rh09-lambdaplex-benchmark-panel
Base commit: abe93945fcf506fce85a180c5cc8b0d201169e05
Status: acceptance checks passed locally; committed locally and review-ready (with unrelated residual drift still present outside the RH-09 commit scope)

## Scope

Implemented the RH-09 Lambdaplex benchmark-ingestion slice on top of the accepted RH-08 state.

Contract shipped:
- the local Lambdaplex benchmark payload now has an explicit RH-09 schema, provenance block, comparable-metric mapping surface, and source-notes path
- the reporting pack can merge comparable Lambdaplex headline metrics when the local payload is truly comparable
- placeholder or incomplete benchmark payloads remain explicit and deterministic; no benchmark metrics are fabricated or silently merged
- reporting summaries, manifests, aggregate CSV output, and final markdown now carry benchmark provenance / source-notes context
- benchmark schema validation and reporting behavior are covered by dedicated tests

## Source changes

- `src/saucerswap_v3_replay/benchmarks/lambdaplex.py`
  - replaces the flat placeholder stub with a structured RH-09 benchmark contract loader and validator
- `src/saucerswap_v3_replay/reporting/tables.py`
  - merges comparable benchmark metrics into the benchmark row when eligible and renders provenance/source-notes context
- `src/saucerswap_v3_replay/reporting/pack.py`
  - threads the structured benchmark summary into reporting outputs, caveats, global checks, and manifest inputs
- `benchmarks/lambdaplex/published-results.json`
  - upgraded to the RH-09 schema while remaining honestly placeholder-only
- `benchmarks/lambdaplex/source-notes.md`
  - now records the local payload state, mapping contract, blocker, and rerun reminder
- `tests/test_lambdaplex_benchmark.py`
  - adds dedicated schema/provenance/comparability coverage
- `tests/test_reporting_pack.py`
  - updates fixtures to the RH-09 schema and adds comparable benchmark rendering coverage
- `tests/test_validation_polish.py`
  - updates benchmark fixtures to the RH-09 contract
- `README.md`
  - points the reporting rerun path at the tracked benchmark contract files

## Commands run

- `make validate-config`
  - result: passed
- `make compile`
  - result: passed
- `make test`
  - result: passed (`48` tests)
- `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli reporting-pack --root artifacts/rh09-benchmark-20260325/reporting-root`
  - result: passed against an isolated local staging root that reuses the mounted RH-04 / RH-05 / RH-06 inputs read-only
  - note: this isolated root was necessary because `data/processed/` in the RH-09 worktree is symlink-mounted to upstream lane outputs, including RH-07 reporting files; running against `--root .` would risk writing through those mounts

## Materialized outputs

From the isolated RH-09 reporting-pack acceptance run:

- `artifacts/rh09-benchmark-20260325/reporting-root/data/processed/comparison_aggregate.csv` (`2,474` bytes)
- `artifacts/rh09-benchmark-20260325/reporting-root/data/processed/comparison_by_bucket.csv` (`3,656` bytes)
- `artifacts/rh09-benchmark-20260325/reporting-root/data/processed/comparison_by_side.csv` (`1,883` bytes)
- `artifacts/rh09-benchmark-20260325/reporting-root/data/processed/reporting_pack_summary.json` (`29,832` bytes)
- `artifacts/rh09-benchmark-20260325/reporting-root/data/processed/reporting_pack_manifest.json` (`9,075` bytes)
- `artifacts/rh09-benchmark-20260325/reporting-root/reports/final-comparison.md` (`4,340` bytes)
- `artifacts/rh09-benchmark-20260325/reporting-root/reports/reconciliation.md` (`1,014` bytes)
- `artifacts/rh09-benchmark-20260325/reporting-root/reports/validation.md` (`1,343` bytes)

## Benchmark availability / provenance status

- local benchmark payload status: `placeholder`
- local benchmark schema: `rh09_lambdaplex_published_panel_v1`
- comparable benchmark metrics ingested from tracked local sources: `no`
- benchmark merge blocker: `Comparable Lambdaplex headline metrics are not recorded locally in this worktree, so RH-09 can only ship the ingestion contract and explicit blocker handling.`
- tracked provenance surfaces:
  - `benchmarks/lambdaplex/published-results.json`
  - `benchmarks/lambdaplex/source-notes.md`
- mapping rule now enforced:
  - raw `headline_metrics` stay provenance-only
  - only `comparable_headline_metrics` can flow into comparison outputs
  - a `comparable` payload must include at least `fill_rate`, `avg_completion_ratio`, `avg_slippage_bps`, `avg_abs_slippage_bps`, and `remainder_size_hbar`

## Reporting delta from RH-08

- RH-08 only disclosed Lambdaplex as placeholder/raw status
- RH-09 adds a structured benchmark contract and deterministic validation of comparable vs non-comparable benchmark payloads
- comparison aggregate output now carries benchmark comparability, source-notes path, and provenance summary columns
- final comparison markdown now surfaces benchmark provenance / source-notes details and can include the Lambdaplex row in the headline comparison table when comparable metrics are locally present
- reporting summary and manifest now embed the structured benchmark object instead of the old flat status stub

## Notes for review

- default tracked benchmark contract:
  - `benchmarks/lambdaplex/published-results.json`
  - `benchmarks/lambdaplex/source-notes.md`
- isolated acceptance root used for the live reporting-pack verification:
  - `artifacts/rh09-benchmark-20260325/reporting-root/`
- pre-existing unrelated worktree drift remained present in `data/raw/gigabrain/extract-manifest.json`; RH-09 did not modify or normalize that file
- no push performed
