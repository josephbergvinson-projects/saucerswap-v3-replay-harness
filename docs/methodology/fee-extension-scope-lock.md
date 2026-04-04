# Fee Extension Scope Lock (RH-20)

This document freezes the fee-attribution contract for the post-first-pass extension of the SaucerSwap V3 replay study.

Purpose:
- preserve the existing replay-study execution-quality outputs as the baseline comparison pack
- add an explicit fee-transfer layer for trader cost, liquidity-side earnings, and protocol earnings
- make RH-21, RH-22, and RH-23 implement against one locked fee contract instead of evolving ad hoc during reporting

## 1) Change boundary

This tranche is additive.

It does:
- extend the published replay study with fee-inclusive economic outputs
- add scenario comparisons for V3 fee discounts
- add route-aware fee attribution for the 3B hybrid lane

It does not:
- change the locked event-level replay contract
- change the claim boundary that 3A and 3B are study-owned lanes rather than canonical deployed V3 behavior
- convert the study into a full maker-PnL or LP-ROI model
- silently rewrite the existing RH-15 / RH-17 execution-quality conclusions

## 2) Measurable outputs vs out-of-scope claims

### Measurable in this study

The fee-extension may report the following as explicit fee transfers:

- V2 trader fee cost on executed notional
- V2 active-LP fee accrual on executed notional
- V2 protocol fee accrual on executed notional
- V3 taker fee cost on executed pure-book notional under locked fee scenarios
- V3 maker rebate accrual on executed pure-book notional under locked fee scenarios
- V3 protocol net fee accrual on executed pure-book notional under locked fee scenarios
- 3B blended fee attribution across the pure-book route and the V2 residual-backstop route
- all-in trader cost views that combine execution shortfall and explicit fees

`protocol_fee_earned_usd` in this study means gross trading-fee accrual to the protocol before downstream BrewSaucer/xSAUCE/development/POL routing. Downstream buyback-routing splits may be modeled later, but they are not required for the RH-20 / RH-21 fee contract.

### Explicitly out of scope

The fee-extension must not overclaim the following:

- V2 individual LP ROI or per-position performance
- V2 impermanent loss or inventory risk
- V3 full maker PnL, spread capture, inventory carry, or adverse-selection outcomes
- live product semantics beyond the locked study-owned fee schedules and hybrid routing rule
- hidden imputation of missing historical fee data

Interpretation guardrail:
- V2 liquidity-side output is aggregate active-range fee accrual, not individual LP profitability
- V3 liquidity-side output is explicit maker rebate capture, not total market-maker profitability

## 3) Locked fee semantics

### 3.1 V2 WHBAR/USDC baseline

The locked V2 fee schedule for the replay study is:

- trader gross swap fee: `15.0 bps`
- protocol cut: `1/6` of trader fee = `2.5 bps`
- active-LP cut: `5/6` of trader fee = `12.5 bps`

Per-record V2 identities:

- `trader_fee_paid_usd = 15.0 bps * filled_notional_usd`
- `protocol_fee_earned_usd = 2.5 bps * filled_notional_usd`
- `active_lp_fee_earned_usd = 12.5 bps * filled_notional_usd`
- `maker_rebate_earned_usd = 0`

### 3.2 V3 WHBAR/USDC pure-book route

The locked V3 WHBAR/USDC fee schedule for the replay study is based on the current launch draft:

- taker schedule: `12.0 bps`
- maker rebate schedule: `0.20 bps`
- rebate cap: `25%` of effective taker fees collected after discount
- market min order size: `1.0 USDC`

Two explicit V3 scenarios are locked for RH-21 onward:

#### Scenario A — `no_xsauce`
- taker fee paid: `12.0 bps`
- maker rebate earned: `0.20 bps`
- rebate cap: `3.0 bps`
- protocol net fee earned: `11.8 bps`
- cap status: `does_not_bind`

#### Scenario B — `tier2_10pct`
- taker schedule: `12.0 bps`
- xSAUCE discount: `10%`
- effective taker fee paid: `10.8 bps`
- maker rebate earned: `0.18 bps`
- rebate cap: `2.7 bps`
- protocol net fee earned: `10.62 bps`
- cap status: `does_not_bind`

Per-record V3 identities:

- `trader_fee_paid_usd = effective_taker_fee_bps * filled_notional_usd`
- `maker_rebate_earned_usd = scenario maker_rebate_bps * filled_notional_usd`
- `protocol_fee_earned_usd = protocol_net_fee_bps * filled_notional_usd`
- `active_lp_fee_earned_usd = 0`

### 3.3 Positive-sign convention

All fee-transfer fields are positive amounts in USD to avoid sign ambiguity.

- `trader_fee_paid_usd` = positive trader cost
- `protocol_fee_earned_usd` = positive protocol accrual
- `active_lp_fee_earned_usd` = positive V2 liquidity accrual
- `maker_rebate_earned_usd` = positive V3 maker accrual

At the per-record and aggregate level, the locked reconciliation identity is:

- `trader_fee_paid_usd = protocol_fee_earned_usd + active_lp_fee_earned_usd + maker_rebate_earned_usd`

Unused recipient buckets must stay zero rather than null when the lane semantics make them impossible.

## 4) Fee basis, normalization, and min-order handling

### 4.1 Fee-calculation basis

Explicit fee transfers are calculated on executed / filled notional, not on requested notional.

Reason:
- explicit fees only accrue on executed volume
- partial fills must not be charged as if the full requested size executed

Locked rule:
- `filled_notional_usd` is the canonical fee-calculation basis for recipient transfers and trader fee amounts

### 4.2 Headline normalization basis

Headline fee rollups in the report remain normalized by requested notional so the fee-inclusive economic view stays completion-aware and comparable to the current study surfaces.

Locked reporting rule:
- headline fee bps and all-in economic comparisons use `sum(requested_notional_usd)` in the denominator
- filled-notional-normalized fee bps may be reported as supplemental diagnostics, not the headline decision surface

### 4.3 V3 min-order handling

The locked V3 min order size for WHBAR/USDC is `1.0 USDC`.

Eligibility rule:
- V3 min-order eligibility is tested on replay-unit `requested_notional`

Handling rule:
- replay units below `1.0 USDC` remain in the dataset and in the pre-existing execution-quality tables for continuity
- fee reporting must flag them as `v3_min_order_ineligible`
- they must be surfaced separately rather than silently included in V3 fee rollups
- if a later run finds zero such rows, the count may be zero, but the field/logic remains part of the contract

## 5) Locked 3B hybrid fee attribution rule

3B fee attribution must stay route-aware.

Locked rule:
- the pure-book-filled portion uses the active V3 scenario fee schedule
- the routed V2 residual-backstop portion uses the locked V2 fee schedule
- unfilled remainder accrues zero explicit fee

Therefore 3B is allowed to carry both V2 liquidity accrual and V3 maker rebate accrual in the same replay-unit record when both routes execute.

Required traceability:
- RH-21 must preserve enough route-level fee detail to reconstruct how 3B totals were formed from `pure_book` and `v2_backstop`
- route-level fee detail may be stored as explicit subfields or as a structured nested fee-breakdown object, but it must be machine-readable and reproducible

## 6) Execution-record fee field contract

RH-21 must extend the execution-record contract so every lane can emit at least the following fee fields:

- `fee_contract_version`
- `fee_scenario_id`
- `v3_min_order_ineligible`
- `fee_basis_filled_notional_usd`
- `trader_fee_paid_usd`
- `protocol_fee_earned_usd`
- `active_lp_fee_earned_usd`
- `maker_rebate_earned_usd`

Required 3B traceability:
- `fee_route_breakdown` or equivalent machine-readable route-level structure
- route-level branches must be sufficient to reconstruct fee basis and recipient allocations for `pure_book` and `v2_backstop`

Derived reporting fields such as all-in cost, fee bps on requested notional, or fee bps on filled notional do not need to be stored per record if they can be reproduced deterministically from the locked fields above.

## 7) Reporting contract for RH-22 / RH-23

The fee-extension report must preserve a strict separation between:

- execution-quality outputs
- fee-inclusive economic outputs

Required reporting rule:
- the existing fill / completion / slippage surfaces remain visible and are not silently replaced by fee-inclusive metrics
- fee-inclusive tables must sit alongside them as a second surface

Minimum additional reporting surfaces:

- headline fee table by lane
- bucket split for trader fees, liquidity-side earnings, and protocol earnings
- side split for trader fees, liquidity-side earnings, and protocol earnings
- all-in trader cost view = execution shortfall + explicit trader fees
- scenario comparison for `no_xsauce` vs `tier2_10pct`
- explicit note or count for any `v3_min_order_ineligible` rows

## 8) Acceptance checks for downstream implementation

RH-21 / RH-22 / RH-23 are not acceptance-complete unless all of the following hold:

1. **Recipient reconciliation**
   - per-record and aggregate fee transfers satisfy:
     - `trader_fee_paid_usd = protocol_fee_earned_usd + active_lp_fee_earned_usd + maker_rebate_earned_usd`

2. **Locked V2 math**
   - V2 aggregate fee bps resolve to `15.0 / 12.5 / 2.5` for trader / LP / protocol on executed notional

3. **Locked V3 math**
   - `no_xsauce` resolves to `12.0 / 0.20 / 11.8`
   - `tier2_10pct` resolves to `10.8 / 0.18 / 10.62`

4. **Rebate-cap guardrail**
   - the implementation proves the 25% cap logic exists
   - the locked WHBAR/USDC scenarios report `does_not_bind`

5. **3B route reconciliation**
   - 3B totals equal the sum of route-level fee components
   - unfilled residual carries zero explicit fee

6. **No-fill handling**
   - records with zero filled notional carry zero explicit fee transfers

7. **Execution-surface continuity**
   - current fill / completion / slippage outputs remain unchanged relative to `main` unless a later explicitly approved lane changes execution logic

8. **Min-order transparency**
   - any rows below the V3 min order threshold are visible in reporting and not silently folded into eligible V3 fee rollups

## 9) Relationship to the current published report

The current `reports/final-comparison.md` explicitly states that 3A and 3B still carry `fees_paid=0.0` because the first-pass study had no grounded synthetic or blended fee model.

RH-20 freezes the contract that will replace that limitation in the report v2 tranche.
It does not invalidate the existing published execution-quality results; it defines the additive economic layer that comes next.
