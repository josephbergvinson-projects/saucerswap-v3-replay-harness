# RH-05 Pure-Book Implementation Index — 2026-03-24

## Objective
Implement the RH-05 3A pure-book lane on `feat/ssv3-rh05-3a-pure-book` using the mounted RH-03 normalized replay inputs and RH-04 realized V2 baseline artifacts, leaving the branch local-review-ready without pushing.

## Worktree
- Repo root: `/Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness`
- Active worktree: `/Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness/.worktrees/feat-ssv3-rh05-3a-pure-book`
- Branch: `feat/ssv3-rh05-3a-pure-book`

## Source changes
- `Makefile`
- `README.md`
- `src/saucerswap_v3_replay/cli.py`
- `src/saucerswap_v3_replay/sim/book_profile.py`
- `src/saucerswap_v3_replay/sim/hybrid.py`
- `src/saucerswap_v3_replay/sim/pure_book.py`
- `tests/test_pure_book.py`

## Commands run
- `make validate-config` — passed
- `make compile` — passed
- `make test` — passed (`Ran 32 tests`)
- `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli pure-book --root .` — passed, materialized 3A outputs under `data/processed/`
- `wc -l data/interim/normalized_events.csv data/interim/replay_units.csv data/processed/lane_3a_pure_book.csv` — confirmed one header + 7,255,957 data rows in each file

## Materialized outputs
- `data/processed/lane_3a_pure_book.csv`
- `data/processed/pure_book_summary.json`
- `data/processed/pure_book_manifest.json`

## Output sizes
- `lane_3a_pure_book.csv` — 4.0G (`4348296322` bytes)
- `pure_book_summary.json` — 5.7K
- `pure_book_manifest.json` — 5.1K

## Row-count and reconciliation summary
- normalized event rows: `7,255,957`
- pure-book rows: `7,255,957`
- replay projection verified rows: `7,255,957`
- replay projection missing tail rows: `0`
- buy rows: `3,770,999`
- sell rows: `3,484,958`
- counts match: `true`
- filled plus remainder matches requested size: `true`
- overfill rows: `0`
- replay projection complete: `true`

## Completion summary
- full-fill rows: `7,227,168`
- partial-fill rows: `28,789`
- zero-fill rows: `0`
- average completion ratio: `0.999813179401`
- remainder size total: `431,584,607.835286259651` HBAR

## Slippage summary
- average execution slippage: `2.261847743867` bps
- minimum slippage: `1.999999999998` bps
- maximum slippage: `37.29516421537` bps
- finite slippage rows: `7,255,957`
- positive slippage rows: `7,255,957`

## Methodology notes
- One replay unit maps to exactly one pure-book execution record.
- The synthetic book is replenishing and resets per replay unit.
- The ladder is loaded from `config/lambdaplex_book.yaml` with total synthetic depth `20,000` USD split across six levels at `2/4/8/16/32/64` bps.
- The lane walks the synthetic book against RH-03 `requested_size`; RH-03 `requested_notional` is preserved for downstream comparison context.
- Completion is explicit: the lane does not force completion to `1.0` when configured synthetic depth cannot fully fill a replay unit.
- 3A has no separate synthetic fee model in the current Phase 0 config. Lane records keep `fees_paid=0.0`, preserve RH-03 `fee_covered`, and disclose the limitation in the summary/manifest instead of inventing per-replay-unit fee precision.
- A small floating-point overfill tail observed on the first materialization pass was clamped out at source with a tolerance guard; the final accepted run reports `overfill_rows=0`.

## Status
Acceptance checks passed locally. Branch remained local-only and was not pushed.
