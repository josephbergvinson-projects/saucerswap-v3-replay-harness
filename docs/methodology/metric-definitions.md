# Metric Definitions

Core metrics expected from the harness:

- full-fill rate
- partial-fill rate
- average completion ratio
- canonical external-reference slippage (`avg_slippage_bps`)
- Lambdaplex-parity AMM pre-trade spot gross slippage proxy (`avg_amm_pre_trade_spot_gross_slippage_bps`)
- completion-adjusted comparison metric
- savings / loss per requested notional
- side-split outputs
- requested-notional bucket outputs

Guardrail:

- `avg_slippage_bps` remains the study-owned headline metric based on the locked external `reference_price` convention.
- `avg_amm_pre_trade_spot_gross_slippage_bps` is a separate competitor-facing parity proxy based on RH-13's best-supported reconstructed AMM pre-trade pool-spot gross convention with a symmetric reference denominator.
