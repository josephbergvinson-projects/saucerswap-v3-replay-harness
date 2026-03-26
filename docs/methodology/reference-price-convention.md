# Reference Price Convention

The reference price is used for two jobs:

1. centering the synthetic book
2. measuring slippage

## Locked first-pass rule

- Primary source: the pre-trade event-time aligned reference price for the replay unit.
- Fallback 1: the nearest earlier reference observation from the extracted source for the same market.
- Fallback 2: if no earlier observation exists, the nearest later reference observation for the same market.
- Any fallback use must be explicitly flagged in the normalized dataset and/or extract manifest so it remains auditable.

## Operational notes

- The same locked convention applies to both 3A and 3B.
- The reference-price rule is frozen in Phase 0 and mirrored in `config/study.yaml`.
- If a better canonical historical reference-price reconstruction becomes available later, it should be introduced as an explicit methodology revision rather than a silent pipeline change.
- The RH-14 Lambdaplex-parity proxy does not alter this locked canonical rule. It is surfaced separately as `amm_pre_trade_spot_gross_slippage_bps`, using the RH-13 best-supported reconstructed AMM pre-trade pool spot plus a symmetric reference denominator.
