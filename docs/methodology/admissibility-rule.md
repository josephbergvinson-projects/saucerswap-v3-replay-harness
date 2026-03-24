# Admissibility Rule

The hybrid lane routes residual size to historical V2 only when the lane's admissibility rule passes.

## Default first-pass rule

- Buy-side residual may route to V2 only if the reconstructed residual execution price is less than or equal to the configured buy-side cap.
- Sell-side residual may route to V2 only if the reconstructed residual execution price is greater than or equal to the configured sell-side floor.
- If an explicit historical order constraint is not recoverable, the harness may apply a disclosed study-owned proxy such as a slippage cap relative to the reference price.

## Design goal

Keep the rule explicit, configurable, testable, and easy to swap later if a higher-fidelity recovery path becomes available.
