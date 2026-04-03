# RH-24 Gross Spread Capture Materialization

RH-24 adds a separate gross spread-capture proxy for filled resting-book quotes:

- `3A pure-book`: all filled synthetic-book size.
- `3B hybrid`: pure-book leg only; exclude the V2 backstop leg.
- Metric basis: study reference price versus resting-book filled size/notional.
- Do not present it as full maker PnL, V2 LP fee accrual, or V3 maker rebate.

Exact study numbers require row-level materialized lane outputs in `data/processed/`:

- `lane_3a_pure_book.csv`
- `lane_3b_hybrid.csv`

If this checkout only has mounted summaries/reports, rerun:

```bash
PYTHONPATH=src python3 -m saucerswap_v3_replay.cli pure-book --root .
PYTHONPATH=src python3 -m saucerswap_v3_replay.cli hybrid --root .
PYTHONPATH=src python3 -m saucerswap_v3_replay.cli reporting-pack --root .
```
