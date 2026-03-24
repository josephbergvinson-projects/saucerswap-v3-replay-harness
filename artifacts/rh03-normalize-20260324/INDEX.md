# RH-03 Normalize Event Level Units — Artifact Index

Date: 2026-03-24
Branch: feat/ssv3-rh03-normalize-event-level-units
Worktree: /Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness/.worktrees/feat-ssv3-rh03-normalize-event-level-units

## Scope

Implemented deterministic event-level normalization for the materialized SaucerSwap V2 HBAR/USDC replay dataset.

Contract shipped:
- one observed `trade_data_v2` row maps to one replay unit
- canonical ordering is `tradeTimestampSeconds`, `swapEventId`, `tradeRowId`
- no cross-row collapse
- replay-unit compatibility preserved via `tx_id := swapEventId` and `event_index := tradeRowId`

## Source changes

- `src/saucerswap_v3_replay/schema.py`
  - extended `ReplayUnit` with explicit source-anchor and coverage fields while preserving existing positional callers
- `src/saucerswap_v3_replay/normalize/events.py`
  - added event-level parsing, side resolution, deterministic formatting, and `NormalizedEvent`
- `src/saucerswap_v3_replay/normalize/prices.py`
  - added stdlib reference-price loader and at-or-before / later-fallback join logic
- `src/saucerswap_v3_replay/normalize/replay_units.py`
  - replaced collapse semantics with canonical event-level materialization and kept a compatibility shim
- `src/saucerswap_v3_replay/normalize/pipeline.py`
  - added streaming normalization pipeline that writes interim CSVs and a manifest
- `src/saucerswap_v3_replay/cli.py`
  - added `normalize-event-level`
- `Makefile`
  - added `normalize-event-level` target
- `README.md`
  - documented the rerun command and interim outputs
- `tests/test_normalize_events.py`
  - covers side inference, requested-notional semantics, and reference-price behavior
- `tests/test_replay_units.py`
  - covers deterministic ordering and one-trade-row-per-replay-unit pipeline behavior

## Commands run

- `make validate-config` — passed
- `make compile` — passed
- `make test` — passed (`Ran 24 tests`)
- `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli normalize-event-level --root .` — passed

## Materialized outputs

Generated locally under `data/interim/`:
- `data/interim/normalized_events.csv`
- `data/interim/replay_units.csv`
- `data/interim/normalization-manifest.json`

Observed file sizes from the final successful run:
- `normalized_events.csv` — 1,777,871,695 bytes
- `replay_units.csv` — 1,168,929,452 bytes
- `normalization-manifest.json` — 3,099 bytes

## Output summary

Row counts:
- raw trade rows: 7,255,957
- normalized event rows: 7,255,957
- replay unit rows: 7,255,957
- reconciliation: counts match

Coverage / missingness:
- swap metadata covered rows: 103,326
- swap metadata missing rows: 7,152,631
- swap metadata coverage ratio: 0.01424
- fee covered rows: 3,892,143
- fee missing rows: 3,363,814
- fee coverage ratio: 0.536407
- reference price at-or-before rows: 7,255,957
- reference price later fallback rows: 0
- reference price missing rows: 0
- explicit side rows: 7,255,957
- inferred side rows: 0
- buy rows: 3,770,999
- sell rows: 3,484,958

Timestamp ranges:
- trades: 1700264033 to 1774363967
- reference prices: 1700239200 to 1774363860

Determinism anchors:
- first ordering key: `1700264033:00000000000000000036:00000000000000000036`
- last ordering key: `1774363967:00000000000009610455:00000000000009577405`
- ordering fingerprint: `c74934c10b96eaa2feab41bb5babe2dfbd6445ee5a019a147575599a434d0d4d`

## Notes

- Reference prices are normalized to USDC-per-HBAR by inverting the raw pool minute series.
- Requested size is the HBAR-side size from `targetVolume`.
- Requested notional is the USDC-side size from `baseVolume`.
- Fee inputs are treated as daily supplemental coverage only for `poolVersion == 2`.
- Interim outputs are gitignored and remain local artifacts.
