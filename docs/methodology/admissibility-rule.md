# Admissibility Rule

The hybrid lane routes residual size to historical V2 only when the lane's admissibility rule passes.

## Locked first-pass rule

- A recoverable historical V2 residual quote is required before any residual may route.
- The first-pass proxy uses a symmetric `50 bps` maximum realized slippage allowance versus the replay-unit reference price.
- Buy-side residual may route to V2 only if realized slippage versus the replay-unit reference price is less than or equal to `50 bps`.
- Sell-side residual may route to V2 only if realized slippage versus the replay-unit reference price is less than or equal to `50 bps`.
- If the quote is missing or the admissibility test fails, the residual remains unfilled.

## Design goal

Keep the rule explicit, configurable, testable, and easy to swap later if a higher-fidelity recovery path becomes available.

## Claim boundary

This is a study-owned first-pass proxy, not a claim about canonical product behavior. If a recoverable order-level admissibility rule becomes available later, it should replace this proxy through an explicit methodology change.
