# RH-12 diagnosis memo — large-clip fidelity

## Objective

Attack the accepted study's main remaining modeling weakness: poor completion in the `25k+` requested-notional regime, without hiding new assumptions or collapsing the study back toward the realized V2 baseline.

## What RH-12 changed

RH-12 keeps the existing study-owned inputs and the same symmetric `50 bps` slippage cap, but changes the 3B admissibility measurement basis:

- before: test the raw recoverable V2 backstop quote in isolation
- after: test the **projected hybrid average execution price** after the mounted 3A fill plus the candidate residual route

This is the smallest defensible change found in-scope for the current event-level contract. It does **not** add synthetic depth, hidden replenishment, blended fees, or fabricated benchmark data.

## Ranked diagnosis of the `25k+` weakness

### 1) Structural pure-book depth ceiling creates a residual on every `25k+` row

Evidence from `diagnostics_summary.json`:

- `25k+` rows: `2,640`
- `25k+` pure-book residual rows: `2,640`
- residual share in `25k+`: `1.0`

Interpretation:

- The accepted 3A ladder is capped at `20k` USD total replenishing depth.
- Under the current bucketing, every `25k+` replay unit necessarily spills past that study-owned book slice.
- So the large-clip problem is not that a few outlier rows are malformed; it is a structural property of the current 3A lane.

### 2) The dominant 3B bottleneck was admissibility rejection, not missing quote recovery or size shortage

Evidence from the same diagnostic pass on the accepted inputs:

- current `25k+` residual rows admissible under the accepted rule: `1,353`
- current `25k+` residual rows inadmissible under the accepted rule: `1,287`
- `25k+` available-size-limited rows: `0`
- hybrid summary after RH-12 rerun still shows `backstop_quote_missing_rows: 0`

Interpretation:

- The mounted V2 backstop is present for the large residual rows.
- The recoverable size is not the bottleneck in the observed data slice.
- The main failure mode is that the accepted rule evaluates the backstop on the whole-event V2 average price in isolation, which is too punitive once 3A has already delivered a low-slippage first slice.

### 3) Quote-only admissibility was rejecting rows whose blended hybrid outcome still sat inside the same 50 bps guardrail

Evidence from `diagnostics_summary.json`:

- projected `25k+` blended-admissible residual rows: `1,760`
- incremental `25k+` rows unlocked by blended admissibility: `407`
- projected `25k+` fill-rate improvement before rerun: `0.5983774024 -> 0.6510806081`

Interpretation:

- The issue was not the existence of a slippage guardrail itself.
- The issue was the measurement basis: the accepted rule used the raw backstop quote instead of the hybrid lane's own projected blended execution.
- Switching the test basis preserves interpretability: 3B still routes only when the final hybrid execution remains inside the same study-owned cap.

## Why this change is defensible

1. **No new data source**: still uses mounted RH-05 pure-book fill and mounted RH-04 V2 realized execution price.
2. **No new cap**: still `50 bps` buy / `50 bps` sell.
3. **No hidden completion forcing**: residuals still remain visible when the projected blended execution breaches the cap.
4. **No fake liquidity**: the book shape and backstop size source stay unchanged.
5. **Lane-consistent measurement**: admissibility is now evaluated on the hybrid lane's own projected outcome, which is the quantity the lane ultimately reports.

## Measured impact after isolated rerun

From `before_after_delta_summary.md`:

### `25k+`

- fill rate: `0.5983774024 -> 0.6510806081` (`+0.0527032057`)
- avg completion ratio: `0.7394175522 -> 0.7980145359` (`+0.0585969837`)
- remainder: `290,491,678.411 -> 252,371,705.134` HBAR (`-38,119,973.277`)
- avg slippage: `34.0430 -> 35.3004` bps (`+1.2574`)

### `10k-25k`

- fill rate: `0.9942716992 -> 0.9990851799`
- remainder: `5,077,348.018 -> 810,861.789` HBAR
- avg slippage: `24.3784 -> 24.4674` bps

### aggregate 3B

- fill rate: `0.9877077761 -> 0.9894705584`
- avg completion ratio: `0.9999012678 -> 0.9999259229`
- remainder: `295,569,026.428 -> 253,182,566.923` HBAR
- avg slippage: `2.2605150 -> 2.2610919` bps

## Residual caveat after RH-12

RH-12 materially improves the large buckets, but it does **not** solve the whole problem.

After the rerun, `25k+` still contains `880` admissibility failures in the reporting pack, which means:

- the existing 20k study-owned book slice still leaves very large residuals, and
- for a non-trivial tail, even the blended hybrid execution remains outside the same `50 bps` cap

So the next narrow change, if another slice is warranted, should be a **better justified residual price proxy** or order-tail recovery path. The evidence does **not** support inventing deeper synthetic book liquidity as the next step.

## Files to trust

- diagnostics: `diagnostics_summary.json`
- actual rerun deltas: `before_after_delta_summary.md`
- rerun root: `rerun-root/`
