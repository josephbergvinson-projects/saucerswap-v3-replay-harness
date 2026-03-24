# SaucerSwap V3 Replay Harness

Offline historical replay harness for the HBAR/USDC study comparing:

- realized SaucerSwap V2 execution
- the published Lambdaplex benchmark panel
- a synthetic V3 pure-book lane
- a synthetic V3 hybrid lane with a study-owned V2 residual backstop rule

## Status

This repository is the standalone source tree for the replay study harness. It is intentionally separate from any SaucerSwap production repository.

## Canonical build plan

- Primary execution document: `docs/planning/execution-plan.md`
- Frozen planning source: `docs/planning/replay-study-plan-locked.md`
- Replay contract amendment: `docs/methodology/replay-contract.md`
- Phase 0 methodology lock: `docs/methodology/phase-0-lock.md`

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

The current first-pass contract is an **event-level replay benchmark** rather than a true order-level reconstruction. See `docs/methodology/replay-contract.md`.

## Build sequence summary

This is the short version of the canonical build plan in `docs/planning/execution-plan.md`.

1. Freeze Phase 0 assumptions in `docs/methodology/phase-0-lock.md` and `config/*.yaml`
2. Extract HBAR/USDC V2 0.15% historical flow from Gigabrain
3. Normalize raw flow into event-level replay units
4. Build V2 baseline and shared metrics engine
5. Add 3A pure-book lane
6. Add 3B hybrid lane with study-owned admissibility rule
7. Produce comparison pack and validation outputs

## Reproducible local Metabase export

On this host, the current first-pass extraction route is:

```bash
cd /Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness
make export-metabase
```

Notes:
- this route uses the signed-in local Chrome Metabase session on the host
- macOS may prompt once for access to `Chrome Safe Storage`
- outputs land under `data/raw/gigabrain/`
- chunk metadata and checksummed export summaries land under `runs/rh02b-metabase-export-20260324/`

## Event-level normalization rerun

Once the raw CSVs are present under `data/raw/gigabrain/`, build the replay-ready interim layer with:

```bash
cd /Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness
PYTHONPATH=src python3 -m saucerswap_v3_replay.cli normalize-event-level --root .
```

This materializes:
- `data/interim/normalized_events.csv`
- `data/interim/replay_units.csv`
- `data/interim/normalization-manifest.json`

Rerun safety:
- normalization now writes staged artifacts under `data/interim/` and only replaces the published CSVs plus `normalization-manifest.json` after a full successful run and manifest build
- interrupted or failed reruns therefore leave the previously published final artifacts intact
