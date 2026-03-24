# SaucerSwap V3 Replay Harness

Offline historical replay harness for the HBAR/USDC study comparing:

- realized SaucerSwap V2 execution
- the published Lambdaplex benchmark panel
- a synthetic V3 pure-book lane
- a synthetic V3 hybrid lane with a study-owned V2 residual backstop rule

## Status

This repository is the standalone source tree for the replay study harness. It is intentionally separate from any SaucerSwap production repository.

## Project layout

- `docs/planning/` — frozen planning inputs and Notion export snapshots
- `docs/methodology/` — explicit study assumptions and definitions
- `config/` — runnable study configuration
- `sql/` — extraction queries/templates for Gigabrain source data
- `benchmarks/` — external benchmark inputs (Lambdaplex)
- `data/raw/` — raw extracted data (gitignored)
- `data/interim/` — normalized intermediate datasets (gitignored)
- `data/processed/` — lane outputs and comparison datasets (gitignored)
- `src/` — Python package for extraction, normalization, simulation, metrics, reporting, validation
- `tests/` — unit tests and toy fixtures
- `runs/` — per-run materializations and logs (gitignored)
- `reports/` — human-readable outputs and figures

## Quick start

```bash
cd /Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m saucerswap_v3_replay.cli validate-config
python -m unittest discover -s tests
```

## Claim boundary

This is a counterfactual historical replay harness, not a product-fidelity simulator for deployed SaucerSwap V3.

## First implementation slices

1. Freeze Phase 0 assumptions in `docs/methodology/phase-0-lock.md` and `config/*.yaml`
2. Extract HBAR/USDC V2 0.15% historical flow from Gigabrain
3. Normalize raw flow into replay units
4. Build V2 baseline and shared metrics engine
5. Add 3A pure-book lane
6. Add 3B hybrid lane with study-owned admissibility rule
7. Produce comparison pack and validation outputs
