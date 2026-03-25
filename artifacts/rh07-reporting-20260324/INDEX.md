# RH-07 Reporting Pack — Artifact Index

Date: 2026-03-24
Branch: feat/ssv3-rh07-reporting-pack
Worktree: /Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness/.worktrees/feat-ssv3-rh07-reporting-pack
Base commit: 3e2972ffcb4fe337b7d93458989eaa751c58ca0e
Status: local review-ready candidate; acceptance checks passed locally

## Scope

Implemented the first reporting-pack slice on top of the mounted RH-03, RH-04, RH-05, and RH-06 artifacts.

Contract shipped:
- the normal reporting path is read-only with respect to mounted normalization, baseline, pure-book, and hybrid artifacts
- comparison outputs are materialized under `data/processed/` as CSV plus reporting summary/manifest JSON
- human-readable reports are materialized under `reports/`
- V2 baseline, 3A pure-book, and 3B hybrid are compared directly from mounted lane outputs
- Lambdaplex is surfaced only to the extent the current published panel supports; the current placeholder state is disclosed explicitly and no benchmark metrics are invented

## Source changes

- `src/saucerswap_v3_replay/reporting/pack.py`
  - adds the reporting-pack runner, config loading, bucket assignment, streaming lane rollups, validation, and summary/manifest materialization
- `src/saucerswap_v3_replay/reporting/tables.py`
  - adds deterministic CSV row builders and Markdown renderers for comparison, reconciliation, and validation reports
- `src/saucerswap_v3_replay/reporting/__init__.py`
  - exports the reporting-pack entry point
- `src/saucerswap_v3_replay/metrics/summaries.py`
  - adds reusable rollup primitives for aggregate, side, and bucket summaries
- `src/saucerswap_v3_replay/benchmarks/lambdaplex.py`
  - adds published benchmark status handling for placeholder/incomplete panels
- `src/saucerswap_v3_replay/cli.py`
  - adds the `reporting-pack` CLI entry
- `Makefile`
  - adds the `reporting-pack` target
- `tests/test_reporting_pack.py`
  - adds coverage for deterministic output generation, rollups, bucket edges, side splits, and placeholder benchmark handling
- `README.md`
  - documents the reporting-pack rerun path
- `reports/final-comparison.md`
- `reports/reconciliation.md`
- `reports/validation.md`
  - updated from the accepted local reporting-pack run

## Commands run

- `make validate-config`
  - result: passed
- `make compile`
  - result: passed
- `make test`
  - result: passed (`40` tests)
- `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli reporting-pack --root .`
  - result: passed against the mounted live artifacts; validation rows all `pass`

## Materialized outputs

- `data/processed/comparison_aggregate.csv` (`1,792` bytes)
- `data/processed/comparison_by_bucket.csv` (`3,656` bytes)
- `data/processed/comparison_by_side.csv` (`1,883` bytes)
- `data/processed/reporting_pack_summary.json` (`27,928` bytes)
- `data/processed/reporting_pack_manifest.json` (`6,145` bytes)
- `reports/final-comparison.md` (`3,562` bytes)
- `reports/reconciliation.md` (`1,014` bytes)
- `reports/validation.md` (`830` bytes)

## Reporting outputs summary

From `data/processed/reporting_pack_summary.json`:

- aggregate comparison rows emitted for:
  - `v2_realized`
  - `3a_pure_book`
  - `3b_hybrid`
  - `lambdaplex_published`
- side split rows emitted: `6`
- bucket split rows emitted: `15`
- validation status:
  - `V2 baseline` — `pass`
  - `3A pure-book` — `pass`
  - `3B hybrid` — `pass`
- global validation checks:
  - lane order fixed to V2 baseline, 3A pure-book, 3B hybrid
  - side split enabled from `config/reporting.yaml`
  - bucket split enabled from `config/reporting.yaml`
  - bucket basis loaded from `config/buckets.yaml`
  - direct lane rollups matched mounted lane summaries

## Benchmark handling

- `benchmarks/lambdaplex/published-results.json` is still marked `placeholder`
- the reporting pack therefore writes a benchmark status row and notes in the aggregate outputs and reports
- no Lambdaplex headline metrics, bucket splits, or side splits were fabricated

## Notes for review

- CLI entry: `python3 -m saucerswap_v3_replay.cli reporting-pack --root .`
- Make target: `make reporting-pack`
- The reporting pack preserves mounted artifact immutability and reads mounted CSV/JSON inputs in place
- No push performed
