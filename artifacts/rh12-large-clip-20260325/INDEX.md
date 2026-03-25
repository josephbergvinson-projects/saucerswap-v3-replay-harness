# RH-12 artifact index — large-clip fidelity

## Scope

Branch-local RH-12 slice focused on improving 3B large-clip completion while preserving the low-slippage / explicit-caveat profile of the accepted event-level study.

## Canonical paths

- canonical repo root: `/Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness`
- active worktree: `/Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness/.worktrees/feat-ssv3-rh12-large-clip-fidelity`
- branch: `feat/ssv3-rh12-large-clip-fidelity`
- normalized base: `main @ 6a0e2f4`

## RH-12 deliverables in this folder

- `DIAGNOSIS_MEMO.md`
  - ranked diagnosis of the current `25k+` weakness
  - rationale for the RH-12 change
  - measured post-rerun effects and remaining caveats
- `before_after_delta_summary.md`
  - concise before/after summary for aggregate, `10k-25k`, and `25k+` 3B outputs
- `before_after_delta_summary.json`
  - machine-readable form of the same delta summary
- `diagnostics_summary.json`
  - streaming diagnostic pass on the accepted mounted inputs
- `diagnostics_stdout.json`
  - stdout capture from the diagnostic pass
- `hybrid_rerun_stdout.json`
  - stdout capture from the isolated `hybrid` rerun
- `reporting_rerun_stdout.json`
  - stdout capture from the isolated `reporting-pack` rerun
- `large_clip_diagnostics.py`
  - streaming diagnostic helper used for RH-12 evidence gathering
- `prepare_rerun_root.py`
  - prepares the isolated rerun root used for RH-12 materialization
- `build_delta_summary.py`
  - builds the before/after delta summary from accepted vs RH-12 reporting outputs
- `rerun-root/`
  - isolated output root containing the RH-12 hybrid lane, reporting pack outputs, copied config/benchmark files, and symlinked read-only upstream inputs

## Commands run

### Diagnostics

- `python3 artifacts/rh12-large-clip-20260325/large_clip_diagnostics.py`
  - status: passed
  - output: `diagnostics_summary.json`

### Isolated output root prep

- `python3 artifacts/rh12-large-clip-20260325/prepare_rerun_root.py`
  - status: passed
  - output root: `artifacts/rh12-large-clip-20260325/rerun-root/`

### RH-12 materialization

- `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli hybrid --root artifacts/rh12-large-clip-20260325/rerun-root`
  - status: passed
  - outputs:
    - `rerun-root/data/processed/lane_3b_hybrid.csv`
    - `rerun-root/data/processed/hybrid_summary.json`
    - `rerun-root/data/processed/hybrid_manifest.json`

- `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli reporting-pack --root artifacts/rh12-large-clip-20260325/rerun-root`
  - status: passed
  - outputs:
    - `rerun-root/data/processed/comparison_aggregate.csv`
    - `rerun-root/data/processed/comparison_by_bucket.csv`
    - `rerun-root/data/processed/comparison_by_side.csv`
    - `rerun-root/data/processed/reporting_pack_summary.json`
    - `rerun-root/data/processed/reporting_pack_manifest.json`
    - `rerun-root/reports/final-comparison.md`
    - `rerun-root/reports/reconciliation.md`
    - `rerun-root/reports/validation.md`

### Acceptance checks

- `make validate-config`
  - status: passed
- `make compile`
  - status: passed
- `make test`
  - status: passed (`50` tests)

## Main measured outcome

Accepted 3B vs RH-12 3B:

- aggregate fill rate: `0.9877077761 -> 0.9894705584`
- aggregate avg slippage: `2.2605150 -> 2.2610919` bps
- `25k+` fill rate: `0.5983774024 -> 0.6510806081`
- `25k+` avg completion ratio: `0.7394175522 -> 0.7980145359`
- `25k+` avg slippage: `34.0430 -> 35.3004` bps
- aggregate remainder: `295.569M -> 253.183M` HBAR
- `25k+` remainder: `290.492M -> 252.372M` HBAR

## Rerun reminder

To refresh the RH-12 isolated root on this branch:

1. `python3 artifacts/rh12-large-clip-20260325/prepare_rerun_root.py`
2. `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli hybrid --root artifacts/rh12-large-clip-20260325/rerun-root`
3. `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli reporting-pack --root artifacts/rh12-large-clip-20260325/rerun-root`
4. `python3 artifacts/rh12-large-clip-20260325/build_delta_summary.py`
