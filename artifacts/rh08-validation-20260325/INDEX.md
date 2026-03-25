# RH-08 Validation Polish — Artifact Index

Date: 2026-03-25
Branch: feat/ssv3-rh08-validation-polish
Worktree: /Users/openclaw/OpenClawWorkspace/projects/saucerswap-v3-replay-harness/.worktrees/feat-ssv3-rh08-validation-polish
Base commit: 763f06aa401d7ec59f8d3c7b122823ffba230504
Status: locally committed and review-ready; acceptance checks passed locally

## Scope

Implemented the RH-08 validation-polish slice on top of the mounted RH-04, RH-05, RH-06, and RH-07 artifacts.

Contract shipped:
- the normal RH-08 path is read-only with respect to mounted baseline, pure-book, hybrid, and reporting-pack artifacts
- realized-V2 sanity checks are sampled deterministically as the first observed row per populated `side x requested_notional bucket` segment from the mounted baseline lane
- golden validation cases are evaluated from explicit toy fixtures under `tests/fixtures/`
- `reports/validation.md` now carries forward RH-07 rollup/global checks, adds study caveats, references the new explicit validation artifacts, and surfaces sampled plus golden evidence together
- RH-08 summary and manifest materializations are deterministic across reruns in the same worktree

## Source changes

- `src/saucerswap_v3_replay/validation/polish.py`
  - adds the RH-08 orchestrator, deterministic realized-V2 sample selection, explicit artifact materialization, and summary/manifest generation
- `src/saucerswap_v3_replay/validation/golden_cases.py`
  - expands the old stub into a real toy-fixture evaluator for explicit pure-book and hybrid golden cases
- `src/saucerswap_v3_replay/reporting/tables.py`
  - adds the expanded validation report renderer used by RH-08
- `src/saucerswap_v3_replay/cli.py`
  - adds the `validation-polish` CLI entry
- `Makefile`
  - adds the `validation-polish` target
- `tests/test_validation_polish.py`
  - adds deterministic sample-pack, golden-case, and end-to-end validation-polish coverage
- `tests/fixtures/toy_book.yaml`
- `tests/fixtures/toy_flow.csv`
- `tests/fixtures/toy_expected_outputs.json`
  - make the first golden pack explicit and non-opaque
- `README.md`
  - documents the RH-08 rerun path
- `reports/validation.md`
  - updated from the accepted RH-08 local run

## Commands run

- `make validate-config`
  - result: passed
- `make compile`
  - result: passed
- `make test`
  - result: passed (`43` tests)
- `PYTHONPATH=src python3 -m saucerswap_v3_replay.cli validation-polish --root .`
  - result: passed against the mounted live artifacts; overall status `pass`

## Materialized outputs

- `reports/generated/rh08-validation-sampled-v2-sanity.json` (`17,132` bytes)
- `reports/generated/rh08-validation-sampled-v2-sanity.md` (materialized locally)
- `reports/generated/rh08-validation-golden-cases.json` (`8,100` bytes)
- `reports/generated/rh08-validation-golden-cases.md` (materialized locally)
- `data/processed/rh08_validation_summary.json` (`6,956` bytes)
- `data/processed/rh08_validation_manifest.json` (`6,715` bytes)
- `reports/validation.md` (`4,538` bytes)

## Validation findings

From the accepted RH-08 local run:

- RH-07 rollup validation rows remained `pass` for:
  - `V2 baseline`
  - `3A pure-book`
  - `3B hybrid`
- deterministic realized-V2 sample coverage:
  - rows scanned from mounted baseline lane: `7,255,957`
  - populated segments selected: `10`
  - empty segments: `2`
  - every sampled segment passed all explicit baseline contract checks (`8/8`)
- sampled realized-V2 segments materialized for:
  - buy `<1k`, `1k-5k`, `5k-10k`, `10k-25k`, `25k+`
  - sell `<1k`, `1k-5k`, `5k-10k`, `10k-25k`, `25k+`
- golden-case evaluation:
  - `pure_book_partial_fill` — `pass` (`14/14`)
  - `hybrid_admissibility_fail` — `pass` (`14/14`)
  - `hybrid_admissibility_pass` — `pass` (`14/14`)
- study caveats preserved:
  - event-level replay benchmark, not an order-level reconstruction
  - mounted upstream artifacts reused read-only
  - no grounded synthetic/blended fee model added for 3A/3B
  - Lambdaplex published panel still disclosed as placeholder

## Notes for review

- CLI entry: `python3 -m saucerswap_v3_replay.cli validation-polish --root .`
- Make target: `make validation-polish`
- human-readable review entry point: `reports/validation.md`
- local explicit artifacts:
  - `reports/generated/rh08-validation-sampled-v2-sanity.json`
  - `reports/generated/rh08-validation-golden-cases.json`
  - `data/processed/rh08_validation_summary.json`
  - `data/processed/rh08_validation_manifest.json`
- no push performed
