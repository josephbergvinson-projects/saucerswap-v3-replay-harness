# Execution Plan

This document is the canonical project-level build plan for the SaucerSwap V3 replay harness.

The locked Notion export in `docs/planning/replay-study-plan-locked.md` is the frozen planning source. If there is any ambiguity between planning language and implementation sequence, this file governs build order, deliverables, and acceptance checks.

## 1) Objective

Build a reproducible offline Python harness for the HBAR/USDC replay study that produces four comparison surfaces:

- realized SaucerSwap V2 baseline
- published Lambdaplex benchmark panel
- synthetic V3 pure-book lane (3A)
- synthetic V3 hybrid lane (3B) with a study-owned V2 residual backstop rule

## 2) Claim boundary

- This is a counterfactual historical replay harness, not a product-fidelity simulator of deployed SaucerSwap V3.
- 3A and 3B are study-owned comparison lanes.
- 3B uses a study-owned admissibility rule that is explicit, configurable, and replaceable later if a higher-fidelity recovery path becomes available.

## 3) Done criteria

The first-pass harness is complete when the repository can reproducibly:

1. extract historical HBAR/USDC V2 0.15% source data from Gigabrain
2. normalize that source data into replay-ready events and replay units
3. compute the realized V2 baseline
4. ingest the Lambdaplex benchmark panel
5. run 3A pure-book simulation
6. run 3B hybrid simulation
7. emit aggregate comparison outputs, bucket splits, and side splits
8. emit validation and reconciliation outputs
9. produce a compact human-readable review pack

## 4) Primary source inputs

### Historical source of truth
- Gigabrain historical HBAR/USDC V2 0.15% flow
- preferred extraction path: direct Gigabrain MySQL
- acceptable first-pass fallback: Metabase export against the same source data

### Benchmark input
- published Lambdaplex benchmark outputs, stored locally under `benchmarks/lambdaplex/`

### Locked study assumptions
- `docs/methodology/phase-0-lock.md`
- `config/study.yaml`
- `config/buckets.yaml`
- `config/fees.yaml`
- `config/hybrid_rule.yaml`
- `config/lambdaplex_book.yaml`
- `config/reporting.yaml`

## 5) Build sequence

### Phase 0 — freeze methodology

Purpose:
- lock the study-owned rules before pipeline behavior becomes sticky

Tasks:
- freeze study window and timezone
- freeze replay-unit definition and transaction-collapse rule
- freeze reference-price convention and fallback
- freeze requested-notional buckets
- freeze fee treatment in outputs
- freeze 3B admissibility rule

Artifacts:
- updated `docs/methodology/phase-0-lock.md`
- finalized `config/*.yaml`

Acceptance:
- no unresolved placeholders remain in the Phase 0 docs/configs that would change pipeline behavior materially

### Phase 1 — extract raw historical data

Purpose:
- pull raw historical HBAR/USDC V2 0.15% flow into the project

Tasks:
- finalize SQL extraction templates under `sql/`
- implement Gigabrain extraction wiring in `src/saucerswap_v3_replay/extract/`
- land raw outputs and extraction manifest under `data/raw/gigabrain/`

Artifacts:
- raw trades extract
- raw swap metadata extract
- raw price/reference extract
- `extract-manifest.json`

Acceptance:
- raw files exist locally
- row counts and date coverage are recorded
- key identifiers needed downstream are present or explicitly flagged

### Phase 2 — normalize into replay-ready datasets

Purpose:
- convert raw extracts into deterministic replay-ready tables

Tasks:
- normalize event rows
- infer side and requested notional consistently
- build replay-unit table from the frozen collapse rule
- persist normalized outputs under `data/interim/`

Artifacts:
- `normalized_events.parquet`
- `replay_units.parquet`
- `normalization-manifest.json`

Acceptance:
- normalization is deterministic
- requested-notional totals reconcile to raw input within explained rules
- dropped/invalid rows are flagged explicitly

### Phase 3 — realized V2 baseline + shared metrics

Purpose:
- establish the baseline lane and shared evaluation logic before synthetic lanes

Tasks:
- implement the realized V2 baseline
- finalize the common execution-record schema
- implement core metric functions and summary rollups

Artifacts:
- `lane_v2_baseline.parquet`
- baseline summary tables

Acceptance:
- baseline runs end-to-end on normalized replay units
- completion, slippage, and fee metrics compute consistently
- baseline outputs are inspectable per replay unit

### Phase 4 — 3A pure-book lane

Purpose:
- implement the Lambdaplex-style replenishing order-book lane

Tasks:
- build book profile allocation from `config/lambdaplex_book.yaml`
- implement deterministic book walk
- emit trade-level and replay-unit-level pure-book records

Artifacts:
- `lane_3a_pure_book.parquet`
- pure-book summary outputs

Acceptance:
- 3A runs end-to-end across the normalized replay dataset
- partial-fill and unfilled cases behave deterministically
- sampled outputs are manually explainable from the configured ladder

### Phase 5 — 3B hybrid lane

Purpose:
- implement the study-owned hybrid residual-backstop lane

Tasks:
- implement residual-size V2 quote / reconstruction path using available historical data
- implement the study-owned admissibility rule module
- blend pure-book fill with V2 backstop only when the rule passes

Artifacts:
- `lane_3b_hybrid.parquet`
- hybrid summary outputs

Acceptance:
- 3B runs end-to-end across the normalized replay dataset
- every routed residual is traceable to an explicit admissibility decision
- route breakdown is stored in lane outputs

### Phase 6 — reporting + validation

Purpose:
- turn lane outputs into decision-ready study outputs

Tasks:
- build aggregate comparison table
- build requested-notional bucket table
- build side-split table
- build review pack / memo outputs
- build reconciliation and validation reports

Artifacts:
- `comparison_aggregate.parquet`
- `comparison_by_bucket.parquet`
- `comparison_by_side.parquet`
- `reports/reconciliation.md`
- `reports/validation.md`
- `reports/final-comparison.md`

Acceptance:
- one reproducible run path builds the comparison pack
- validation and reconciliation outputs are present and readable
- review pack carries the study caveats prominently

## 6) Implementation order inside the codebase

Implement in this order:

1. config and methodology lock
2. extraction wiring
3. normalization
4. realized V2 baseline
5. shared metrics and summaries
6. pure-book lane
7. hybrid lane
8. reporting pack
9. validation polish

This order is intentional: baseline and metrics should stabilize before the synthetic lanes add complexity.

## 7) Required execution record fields

Each lane should emit one record per replay unit with at least:

- lane
- replay_unit_id
- timestamp
- tx_id
- event_index
- side
- requested_size
- requested_notional
- filled_size
- filled_notional
- completion_ratio
- reference_price
- avg_execution_price
- fees_paid
- remainder_size
- route_breakdown
- admissibility_passed

## 8) Validation requirements

Minimum validation for the first-pass harness:

- row-count reconciliation between raw and normalized layers
- requested-notional reconciliation
- deterministic rerun behavior for fixed inputs/config
- toy-case unit tests for pure-book and hybrid logic
- sampled sanity checks on realized V2 outputs

Higher-fidelity checks are welcome later, but they are not prerequisites for shipping the first-pass harness.

## 9) Risks to manage

### Replay-unit ambiguity
If multi-event transactions are collapsed badly, the synthetic book lanes can be overstated.

Mitigation:
- keep tx id + event ordering fields
- freeze the collapse rule early
- sample-check collapsed transactions

### Weak 3B admissibility proxy
If the rule is vague, 3B becomes hard to interpret.

Mitigation:
- keep the rule isolated in one module
- make it configurable
- disclose it in the review pack

### Fee-history gaps
Historical fee treatment may be incomplete.

Mitigation:
- keep fee policy explicit in config
- flag missing fields and continue with visible caveats

### Synthetic-lane over-reading
Readers may overinterpret 3A/3B as canonical V3 behavior.

Mitigation:
- keep caveat language in the review pack header
- label 3A/3B consistently as study-owned lanes

## 10) Repository boundary

This repository owns the full technical study pipeline:

- extraction
- normalization
- baseline
- benchmark ingestion
- 3A simulation
- 3B simulation
- metrics
- reporting
- validation

What it does not own:
- live product semantics for deployed V3
- production trading code
- external presentation beyond the repo’s own review outputs

## 11) Immediate next step

The next atomic implementation step is:

- finish Phase 0 by freezing the config values and methodology notes that still need explicit values before real extraction starts
