# Phase 0 Lock

These assumptions are frozen for RH-01. Extraction, normalization, and the first-pass replay lanes should treat them as the study-owned baseline until they are explicitly revised.

## Locked scope boundary

- Market: `HBAR/USDC`
- Source protocol: `SaucerSwap V2`
- Source pool: `HBAR/USDC V2 0.15%`
- Source pool id / address: `9` / `0.0.3964804`
- Canonical realized baseline lane: `v2_realized`
- 3A and 3B remain study-owned comparison lanes, not claims about canonical deployed V3 behavior.

## Locked study window and timezone

- Timezone is frozen to `UTC`.
- The first-pass extraction window is the full available Gigabrain history for the locked source pool at extraction time.
- Phase 1 does not apply calendar subsampling before the first real dataset is materialized.
- The exact realized minimum and maximum timestamps for any concrete run must be recorded in `extract-manifest.json` and treated as the realized study window for that run.

## Locked replay-unit rule

- Replay units collapse same-transaction, same-side event rows into one replay unit when multiple rows represent the same logical request.
- Replay units never collapse across opposite sides.
- Replay units never collapse across transaction ids.
- The normalized dataset must preserve the transaction id plus the event / log ordering fields needed to audit each collapse.
- Within a collapsed unit, the harness preserves the earliest ordering anchor and records collapsed-event count metadata.
- The synthetic book is reset per replay unit for both 3A and 3B.
- Downstream replay ordering remains timestamp-first with event / log index as the tie-breaker.

## Locked reference-price convention

- Primary rule: use a pre-trade event-time aligned reference price for the replay unit.
- First fallback: use the nearest earlier reference observation from the extracted source for the same market.
- Second fallback: if no earlier observation exists, use the nearest later observation and mark it with an explicit fallback flag in the normalized dataset / manifest.
- The same reference price convention is used both to center the synthetic book and to measure slippage.

## Locked requested-notional buckets

- Buckets remain:
  - `<1k`: `[0, 1,000)`
  - `1k-5k`: `[1,000, 5,000)`
  - `5k-10k`: `[5,000, 10,000)`
  - `10k-25k`: `[10,000, 25,000)`
  - `25k+`: `[25,000, +inf)`
- Bucket semantics are lower-inclusive and upper-exclusive except for the final open-ended bucket.
- Bucket attribution is based on requested notional, not filled notional.

## Locked fee treatment in outputs

- Headline comparisons remain fee-inclusive.
- Headline economics remain requested-notional-based rather than filled-only.
- Filled-only execution metrics remain supplemental diagnostics, not the headline decision surface.
- Historical fees are used when available.
- If historical fee fields are missing, the harness flags the gap and continues; it does not silently impute missing fees.
- Partial fills and unfilled residuals must remain visible in completion-aware reporting rather than being treated as hidden improvements.

## Locked first-pass 3B admissibility rule

- 3B requires a recoverable historical V2 residual quote before any backstop routing is allowed.
- The first-pass admissibility proxy is a symmetric `50 bps` maximum realized slippage allowance versus the replay-unit reference price.
- Buy-side residuals may route to V2 only if realized slippage versus the reference price is less than or equal to `50 bps`.
- Sell-side residuals may route to V2 only if realized slippage versus the reference price is less than or equal to `50 bps`.
- If admissibility fails, or no qualifying residual quote is recoverable, the residual remains unfilled.
- This rule is an explicit study-owned first-pass proxy. It is not a claim about canonical product behavior and may be replaced later if a higher-fidelity historical admissibility recovery path is found.

## Config mirrors

These locked assumptions are mirrored in:

- `config/study.yaml`
- `config/buckets.yaml`
- `config/fees.yaml`
- `config/hybrid_rule.yaml`
