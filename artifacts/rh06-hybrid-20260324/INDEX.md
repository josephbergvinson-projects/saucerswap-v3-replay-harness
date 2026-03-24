# RH-06 3B Hybrid Lane — Artifact Index

Date: 2026-03-24
Branch: feat/ssv3-rh06-3b-hybrid-lane
Worktree: /Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness/.worktrees/feat-ssv3-rh06-3b-hybrid-lane
Base commit: 1babf4df77b8db24c5cf7321fba7b5226aac74d6
Status: local review-ready candidate; committed locally, not pushed
Local commit: committed locally after acceptance (see branch history)

## Scope

Implemented the RH-06 3B hybrid lane as an event-level, one-replay-unit-to-one-record blend of:
- mounted RH-05 3A pure-book fill, plus
- mounted RH-04 realized V2 backstop routing for only the residual size, and only when the frozen study-owned admissibility rule passes.

The normal rerun path reuses mounted RH-03 / RH-04 / RH-05 artifacts and does not rebuild normalization, baseline, or pure-book outputs.

## Source changes

- `src/saucerswap_v3_replay/sim/hybrid.py`
- `src/saucerswap_v3_replay/backstop/v2_residual.py`
- `src/saucerswap_v3_replay/rules/admissibility.py`
- `src/saucerswap_v3_replay/cli.py`
- `Makefile`
- `README.md`
- `tests/test_hybrid.py`
- `tests/test_admissibility.py`

## Commands run

- `PYTHONPATH=src python3 -m compileall src tests` — passed
- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'` — passed (`36` tests)
- `make validate-config` — passed
- `make compile` — passed
- `make test` — passed
- `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli hybrid` — passed in `5:52.96`, materialized RH-06 outputs locally

## Output files

- `data/processed/lane_3b_hybrid.csv` (`4,572,908,059` bytes)
- `data/processed/hybrid_summary.json` (`7,253` bytes)
- `data/processed/hybrid_manifest.json` (`6,431` bytes)

## Row-count and reconciliation summary

- Pure-book input rows: `7,255,957`
- V2 baseline input rows: `7,255,957`
- Hybrid rows: `7,255,957`
- Buy rows: `3,770,999`
- Sell rows: `3,484,958`
- Full-fill rows: `7,252,757`
- Partial-fill rows: `3,200`
- Zero-fill rows: `0`
- Average completion ratio: `0.999901267765`
- Filled + remainder matches requested size: `true`
- No overfill rows: `true`
- Mapping fingerprint: `30c5127f47110d8c730e65e85f7695140f833497f28398bc900c211d2925ed93`

## Route breakdown and admissibility summary

- Rows with residual: `28,789`
- Rows without residual: `7,227,168`
- Backstop quote recovered rows: `28,789`
- Backstop quote missing rows: `0`
- Admissibility pass rows: `25,780`
- Admissibility fail rows: `3,009`
- Admissibility pass rate on residual rows: `0.895480912849`
- Routed rows: `25,780`
- Pure-book-only rows: `7,230,177`
- Unrouted residual rows: `3,009`
- Available-size-limited rows: `0`
- Pure-book routed size: `23,613,619,055.756320953369` HBAR
- V2 backstop routed size: `136,015,581.406956315041` HBAR
- Hybrid full-fill rows attributable to backstop routing: `25,398`

## Completion / slippage / fee methodology notes

- Residual means the remainder of the event-level replay unit after the mounted 3A pure-book fill; it is not a recovered multi-event user-order residual.
- The mounted RH-04 realized V2 lane is used as the study-owned recoverable V2 proxy quote surface.
- The frozen admissibility rule is the symmetric `50 bps` realized slippage cap versus the replay-unit reference price, gated by recoverable quote presence.
- If the residual does not pass the rule, the lane leaves the remainder unfilled and preserves that explicitly via `completion_ratio` and `remainder_size`; it does not force completion to `1.0`.
- Hybrid execution slippage is computed against the final blended average execution price.
- 3B does **not** define a separate synthetic or blended fee model in this pass. `fees_paid` remains `0.0`, while `fee_covered` visibility from RH-03 is preserved instead of inventing per-replay-unit fee precision.

## Notes for review

- The 3B CLI entry is `python3 -m saucerswap_v3_replay.cli hybrid`.
- The Make target is `make hybrid`.
- Output contract preserves `replay_unit_id`, `tradeRowId`, `swapEventId`, `tradeTimestampSeconds`, and `source_ordering_key` per hybrid row.
- No push performed.
