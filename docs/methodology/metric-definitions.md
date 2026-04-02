# Metric Definitions

Core metrics expected from the harness now live on two parallel surfaces:

## 1) Execution-quality surface

- full-fill rate
- partial-fill rate
- average completion ratio
- canonical external-reference slippage (`avg_slippage_bps`)
- Lambdaplex-parity AMM pre-trade spot gross slippage proxy (`avg_amm_pre_trade_spot_gross_slippage_bps`)
- completion-adjusted comparison metric
- savings / loss per requested notional
- side-split outputs
- requested-notional bucket outputs

## 2) Fee-inclusive economic surface

- explicit trader fee paid (`trader_fee_paid_usd`)
- protocol fee earned (`protocol_fee_earned_usd`)
- V2 active-LP fee earned (`active_lp_fee_earned_usd`)
- V3 maker rebate earned (`maker_rebate_earned_usd`)
- requested-notional-normalized fee bps (headline)
- filled-notional-normalized fee bps (supplemental)
- all-in trader cost = execution shortfall + explicit trader fee
- side-split fee outputs
- requested-notional bucket fee outputs
- fee-scenario comparison outputs (`no_xsauce` vs `tier2_10pct`)

Guardrails:

- `avg_slippage_bps` remains the study-owned headline execution metric based on the locked external `reference_price` convention.
- `avg_amm_pre_trade_spot_gross_slippage_bps` is a separate competitor-facing parity proxy based on RH-13's best-supported reconstructed AMM pre-trade pool-spot gross convention with a symmetric reference denominator.
- Explicit fee transfers are calculated on filled notional.
- Headline fee-inclusive rollups are normalized by requested notional so they remain completion-aware.
- V2 liquidity-side output is aggregate active-LP fee accrual, not LP ROI.
- V3 liquidity-side output is explicit maker rebate capture, not full maker PnL.
- Fee-inclusive tables must remain visually and conceptually separate from execution-quality tables; they are an additive second surface, not a silent replacement.
