# Phase 0 Lock

These assumptions must be frozen before extraction and simulation logic are treated as stable.

## To lock

- study window and timezone
- replay-unit definition and transaction-collapse rule
- reference-price convention and fallback
- requested-notional bucket edges
- fee treatment in outputs
- hybrid admissibility rule

## Current default posture

- Study is HBAR/USDC only
- Source pool is V2 0.15%
- 3A uses Lambdaplex-style replenishing book assumptions
- 3B uses a study-owned admissibility rule, not a claim about canonical product behavior
