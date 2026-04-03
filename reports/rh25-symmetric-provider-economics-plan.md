# RH-25 — Symmetric Provider-Economics Comparison Plan

## Objective

Add a fully symmetric comparison between:

- **V2 liquidity providers**, and
- **V3-style makers** (`3A` pure-book and the pure-book leg of `3B` hybrid)

so the study compares provider economics on the same economic layers rather than comparing V2 gross LP fee accrual against V3 rebate-only transfer.

## Problem to fix

The current report still flatters V2 because the comparison is structurally uneven:

- V2 is presented with a single large gross liquidity-provider fee-accrual number.
- V3 is split across explicit maker rebate and a separate gross spread-capture section.
- V2 is not yet adjusted for provider-side adverse-selection / divergence loss.
- V3 is not yet adjusted for maker-side post-fill adverse selection / markout loss.

That means the report is fairer than before, but not yet fully symmetric.

## Phase A audit summary

### Existing row-level field coverage

#### V2 baseline (`data/processed/lane_v2_baseline.csv`)

Already materializes everything needed for the core RH-25 proxy without a simulator rerun:

- identity / ordering: `replay_unit_id`, `source_ordering_key`, `tradeTimestampSeconds`
- side / size / notional: `side`, `filled_size`, `filled_notional`, `requested_notional`, `baseVolumeRaw`
- pricing: `reference_price`, `avg_execution_price`
- explicit LP transfer: `active_lp_fee_earned_usd`

This is enough to compute a next-event LVR-style loss proxy directly from the baseline lane rows.

#### V3 maker lanes (`data/processed/lane_3a_pure_book.csv`, `data/processed/lane_3b_hybrid.csv`)

Already materialize everything needed for the core RH-25 maker proxy:

- identity / ordering: `replay_unit_id`, `source_ordering_key`, `tradeTimestampSeconds`
- side / pricing: `side`, `reference_price`
- explicit maker transfer: `maker_rebate_earned_usd`
- pure-book leg isolation:
  - `3A`: `filled_size`, `filled_notional`
  - `3B`: `route_breakdown` plus `fee_route_breakdown`

RH-24 already proved the `3B` pure-book leg can be isolated deterministically from the existing row contract via the current `resting_book_leg_from_row(...)` logic.

### Reporting-pack feasibility

The reporting pack already:

- reads row-level lane CSVs directly,
- computes row observations and aggregate / side / bucket rollups, and
- keeps `3B` pure-book-leg isolation explicit for RH-24 spread capture.

So RH-25 can slot into the same surface pattern. No raw on-chain re-extract is required for the primary next-event metric contract.

### Rerun requirement

- **No fresh heavy replay rerun is required** if the three lane CSVs already exist under `data/processed/`.
- If those row-level lane outputs are absent, rerun baseline / pure-book / hybrid once, then build reporting-pack outputs.
- Optional 1-minute / 5-minute sensitivities would require an extra reference-series lookup path and are **not** part of the core RH-25 contract.

## Target comparison framework

The comparison should be presented on **three aligned layers**.

### Layer 1 — Explicit protocol transfer

This is the narrowest surface and should remain explicitly labeled as such.

- **V2:** LP fee accrual
- **V3:** maker rebate

This is useful but incomplete.

### Layer 2 — Gross provider revenue proxy

This is the first materially fair provider-revenue comparison.

- **V2:** gross LP fee accrual
- **V3:** gross spread capture + maker rebate

This answers: before provider-side adverse selection / inventory effects, how much provider revenue does each design generate?

### Layer 3 — Net provider-economics proxy

This is the fully symmetric target surface for RH-25.

- **V2:** gross LP fee accrual minus divergence-loss / LVR proxy
- **V3:** gross spread capture plus maker rebate minus maker adverse-selection / markout proxy

This answers: after the first-order provider-side adverse-selection drag, how much economics remain on each side?

## Phase A decision — exact metric contract

### Horizon choice

Lock the primary horizon to **next replay-unit / next event reference** within the same lane ordering.

For row `i` in lane order:

- `r_i = reference_price_i`
- `r_i+1 = reference_price_(i+1)` from the **next row in the same lane file order**

Use the existing canonical row order written by the harness. `source_ordering_key` remains the explicit ordering audit field.

Availability rule:

- if a row has no next row in that lane, `next_event_reference_price` is unavailable,
- the RH-25 loss proxy for that row is set to `0`,
- and the row should be counted separately as `next_event_horizon_unavailable` rather than silently treated as fully observed.

This keeps the metric deterministic and avoids introducing a new reference-series dependency into the core contract.

### Sign conventions

Use the following sign rules everywhere:

- `lp_fee_accrual_usd`, `gross_spread_capture_usd`, and `maker_rebate_usd` are **provider-positive** when they help the provider.
- `lp_divergence_loss_proxy_usd` and `maker_markout_loss_proxy_usd` are **non-negative loss proxies**.
- Favorable post-fill moves are **not booked as gains** in the loss proxies; they clip to `0`.
- Net provider-economics proxies may be negative.

This keeps the RH-25 layer explicitly about adverse-selection drag, not full inventory PnL.

### Denominator choices

Canonical exported values should be USD totals first. Bps fields are secondary.

Primary denominator for RH-25 comparison tables:

- `requested_notional_raw_total / 1_000_000`

Use that across lanes for the headline comparison because it matches the current reporting-pack completion-aware normalization.

Secondary denominator for V3 maker-only surfaces:

- `resting_book_filled_notional_total`

Use that only for book-leg-specific components such as gross spread capture, markout loss, and net maker provider economics on the pure-book leg.

### Required row fields

#### V2 loss proxy inputs

From `lane_v2_baseline.csv`:

- `lane`
- `side`
- `filled_size`
- `filled_notional`
- `reference_price`
- `active_lp_fee_earned_usd`
- `source_ordering_key`
- `baseVolumeRaw` / `requested_notional`

#### V3 maker proxy inputs

From `lane_3a_pure_book.csv` / `lane_3b_hybrid.csv`:

- `lane`
- `side`
- `reference_price`
- `maker_rebate_earned_usd`
- `source_ordering_key`
- `baseVolumeRaw` / `requested_notional`
- pure-book leg sizing fields:
  - `3A`: `filled_size`, `filled_notional`
  - `3B`: `route_breakdown` and `fee_route_breakdown`

### Exact formulas

Notation for row `i`:

- `q_v2,i = filled_size_i` from V2 baseline
- `n_v2,i = filled_notional_i` from V2 baseline
- `q_book,i = pure-book leg filled size_i`
- `spread_i = gross_spread_capture_usd_i`
- `fee_i = active_lp_fee_earned_usd_i`
- `rebate_i = maker_rebate_earned_usd_i`
- `r_i = reference_price_i`
- `r_i+1 = next-event reference price_i`

#### V2

##### 1) `lp_fee_accrual_usd`

Keep the existing field:

- `lp_fee_accrual_usd_i = active_lp_fee_earned_usd_i`

##### 2) `lp_divergence_loss_proxy_usd`

Keep the field name for continuity, but define it precisely as a **next-event, adverse-only, LVR-style loss proxy**:

- for `side == buy`:
  - `lp_divergence_loss_proxy_usd_i = max(r_i+1 * q_v2,i - n_v2,i, 0)`
- for `side == sell`:
  - `lp_divergence_loss_proxy_usd_i = max(n_v2,i - r_i+1 * q_v2,i, 0)`

Interpretation:

- this is the adverse-only loss versus re-marking the executed inventory transfer at the next-event reference,
- it is equivalent to execution-to-next-reference markout loss on the filled V2 trade,
- and it cleanly fits the intended “fee accrual minus LVR-style drag” surface.

##### 3) `lp_net_provider_economics_proxy_usd`

- `lp_net_provider_economics_proxy_usd_i = lp_fee_accrual_usd_i - lp_divergence_loss_proxy_usd_i`

#### V3

##### 1) `maker_rebate_usd`

Keep the existing field:

- `maker_rebate_usd_i = maker_rebate_earned_usd_i`

For `3B`, this remains **pure-book-leg only**. Do **not** pull `active_lp_fee_earned_usd` from the V2 backstop leg into the V3 maker surface.

##### 2) `gross_spread_capture_usd`

Keep the RH-24 contract:

- `3A`: all filled pure-book size
- `3B`: pure-book leg only

##### 3) `maker_markout_loss_proxy_usd`

Define the maker adverse-selection proxy on the same next-event horizon, using the **reference move only** so gross spread capture stays separate:

- for `side == buy`:
  - `maker_markout_loss_proxy_usd_i = max((r_i+1 - r_i) * q_book,i, 0)`
- for `side == sell`:
  - `maker_markout_loss_proxy_usd_i = max((r_i - r_i+1) * q_book,i, 0)`

Interpretation:

- this is the adverse-only next-event reference move on the maker inventory transfer,
- it intentionally excludes favorable reversals,
- and it avoids double-counting RH-24 spread capture.

##### 4) `maker_net_provider_economics_proxy_usd`

- `maker_net_provider_economics_proxy_usd_i = gross_spread_capture_usd_i + maker_rebate_usd_i - maker_markout_loss_proxy_usd_i`

#### 3B pure-book-leg isolation rule

For all maker-side RH-25 metrics on `3B`:

- size basis must be the **pure-book leg only**,
- not the blended hybrid row total,
- and the isolation contract should reuse the existing RH-24 pure-book-leg extraction path.

## Reporting surfaces to add

### New comparison outputs

Add provider-economics outputs alongside existing fee and spread-capture surfaces:

- `comparison_provider_econ_aggregate.csv`
- `comparison_provider_econ_by_side.csv`
- `comparison_provider_econ_by_bucket.csv`

### New row / rollup fields

For rows / rollups where applicable:

- `next_event_reference_price`
- `next_event_reference_available`
- `lp_fee_accrual_usd`
- `lp_divergence_loss_proxy_usd`
- `lp_net_provider_economics_proxy_usd`
- `maker_rebate_usd`
- `gross_spread_capture_usd`
- `maker_markout_loss_proxy_usd`
- `maker_net_provider_economics_proxy_usd`

Suggested aggregate diagnostics:

- `next_event_horizon_supported_rows`
- `next_event_horizon_unavailable_rows`

### Report/table additions

Update `reports/final-comparison.md` and the standalone v2 report to include:

1. explicit protocol transfer layer
2. gross provider-revenue layer
3. net provider-economics proxy layer
4. caveat block explaining that RH-25 is still **not** full LP ROI or full maker PnL

## Execution phases

### Phase A — Metric feasibility audit

Goal:

- verify the cleanest implementable V2 divergence/LVR proxy
- verify the cleanest implementable V3 markout proxy
- choose horizons / denominators / sign conventions

Deliverable:

- metric contract note with exact formulas and required fields

### Phase B — Row-level provider-economics views

Goal:

- add row-level helpers / views for V2 LP divergence loss and V3 maker markout
- preserve the existing RH-24 spread-capture semantics
- make `3B` leg isolation explicit

Deliverable:

- new provider-economics view module(s)
- deterministic unit / golden tests

### Phase C — Reporting-pack integration

Goal:

- add aggregate / side / bucket provider-economics outputs
- integrate new tables into `final-comparison.md`
- update validation report invariants

Deliverable:

- provider-economics CSVs
- updated comparison report and validation surfaces

### Phase D — Standalone report integration

Goal:

- replace the current still-asymmetric narrative in `final-study-report-v2.md`
- present V2 LP vs V3 maker economics on the three aligned layers

Deliverable:

- updated standalone report wording / tables

## Acceptance checks

RH-25 is acceptance-complete only when all of the following are true:

1. The chosen V2 adverse-selection proxy and V3 markout proxy are documented with exact formulas.
2. Aggregate, side, and bucket provider-economics outputs exist.
3. `3B` provider metrics isolate the pure-book leg correctly where required.
4. Tests cover sign conventions, decomposition, and leg isolation.
5. `final-comparison.md` includes a net provider-economics comparison section.
6. `final-study-report-v2.md` no longer presents V2 LP fee accrual versus V3 maker rebate / spread as structurally uneven surfaces.

## First execution slice

Start with **Phase A**:

- audit available row fields for V2 adverse-selection / divergence-loss computation
- audit available row fields for V3 markout computation
- pick the exact metric contract
- identify whether a fresh heavy rerun is required or whether existing lane outputs are sufficient

This is the shortest path to avoid coding the wrong economics surface.
