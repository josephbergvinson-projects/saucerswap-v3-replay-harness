# RH-04 Realized V2 Baseline — Artifact Index

Date: 2026-03-24
Branch: feat/ssv3-rh04-v2-realized-baseline
Worktree: /Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness/.worktrees/feat-ssv3-rh04-v2-realized-baseline

## Scope

Implemented the realized V2 baseline lane on top of the RH-03 event-level normalized dataset.

Contract shipped:
- one normalized event-level replay unit maps to one realized V2 baseline record
- `replay_unit_id`, `tradeRowId`, `swapEventId`, `tradeTimestampSeconds`, and `source_ordering_key` are preserved in the lane output
- completion is 1.0 for the realized event-level unit under the amended first-pass contract
- slippage is measured against `reference_price`
- per-replay-unit fees are **not** imputed when the current inputs only expose pool/day fee coverage

## Source changes

- `src/saucerswap_v3_replay/baseline/v2_realized.py`
  - replaced the stub with a runnable baseline pipeline
  - streams RH-03 interim artifacts into `data/processed/`
  - preserves event anchors and baseline record compatibility with `ExecutionRecord`
  - verifies the shared replay-unit projection prefix, then falls back to normalized-event-derived replay units for the trailing projection gap without mutating RH-03 artifacts
  - records fee/slippage caveats and reconciliation metadata in the summary/manifest
- `src/saucerswap_v3_replay/baseline/__init__.py`
  - exports the realized baseline helpers
- `src/saucerswap_v3_replay/cli.py`
  - adds the `v2-baseline` CLI entry
- `Makefile`
  - adds the `v2-baseline` target
- `src/saucerswap_v3_replay/metrics/core.py`
  - makes slippage handling deterministic for zero-execution edge cases (`sell -> inf`, `buy -> -10000 bps`)
- `tests/test_v2_realized.py`
  - expands baseline tests for record construction, mapping verification, replay-unit tail-gap handling, slippage, and summary rollups
- `tests/test_metrics.py`
  - adds zero-execution slippage coverage
- `README.md`
  - documents the realized baseline rerun path

## Commands run

- `PYTHONPATH=src python3 -m unittest tests.test_v2_realized`
  - result: passed
- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'`
  - result: passed (29 tests)
- `python3 -m compileall src`
  - result: passed
- `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli v2-baseline --root .`
  - result: passed; processed outputs written under `data/processed/`
- `make validate-config`
  - result: passed
- `make compile`
  - result: passed
- `make test`
  - result: passed (29 tests)

## Materialized outputs

- `data/processed/lane_v2_baseline.csv`
  - size: 3,071,416,518 bytes
- `data/processed/v2_baseline_summary.json`
- `data/processed/v2_baseline_manifest.json`

## Row-count / reconciliation summary

From `data/processed/v2_baseline_summary.json`:

- normalized-event rows: `5,451,773`
- baseline rows: `5,451,773`
- replay projection verified rows: `5,451,743`
- replay projection missing tail rows: `30`
- buy rows: `2,846,807`
- sell rows: `2,604,966`
- requested size total: `18,878,378,184.57498342 HBAR`
- requested notional total: `3,324,991,018.55032 USDC`
- filled size total: `18,878,378,184.57498342 HBAR`
- filled notional total: `3,324,991,018.55032 USDC`
- count reconciliation: `true`
- requested/fill size reconciliation: `true`
- requested/fill notional reconciliation: `true`

Mapping fingerprint:
- `9221d3669984cebc646e24e57d866c616e4aa27eda05866ae9c01d14c289633b`

## Fee / slippage caveats

- Per-replay-unit historical fees are **not recoverable** from the current fee inputs.
- The current materialized fee input only supports pool/day coverage visibility, so lane records set `fees_paid = 0.0`, mark `fee_precision = not_allocated_per_replay_unit`, and carry `fee_covered` visibility instead of silently imputing swap-level fees.
- Fee day coverage in the materialized run:
  - covered rows: `2,087,959`
  - missing rows: `3,363,814`
  - precise fee rows: `0`
- Finite slippage rows: `5,451,772`
- Non-finite slippage rows: `1`
  - cause: one sell-side replay unit has zero observed execution price with positive `reference_price`
  - handling: the lane preserves the row and writes `realized_slippage_bps = inf`, while summary averages exclude the non-finite row

## RH-03 artifact discrepancy surfaced during RH-04

The existing RH-03 interim artifacts are internally inconsistent at the tail:

- `normalized_events.csv` parsed rows: `5,451,773`
- `replay_units.csv` parsed rows: `5,451,743`
- gap: `30` rows

RH-04 does **not** mutate RH-03 artifacts. Instead, the realized baseline:
- verifies the shared prefix one-to-one against `replay_units.csv`
- derives the final 30 replay-unit records directly from `normalized_events.csv`
- records the projection gap explicitly in the summary/manifest as a caveat

## Retention

- `artifacts/rh04-v2-baseline-20260324/INDEX.md` — retain_long_term
- `data/processed/lane_v2_baseline.csv` — retain_until_manual_archive_window
- `data/processed/v2_baseline_summary.json` — retain_long_term
- `data/processed/v2_baseline_manifest.json` — retain_long_term
