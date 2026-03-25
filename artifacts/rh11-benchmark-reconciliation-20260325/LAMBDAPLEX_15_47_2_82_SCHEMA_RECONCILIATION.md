# RH-11 Benchmark Reconciliation Note — Lambdaplex `15.47` / `2.82`

## Question
Can the published Lambdaplex slide figures:

- `Average AMM slippage = 15.47 bps`
- `Grid strategy slippage = 2.82 bps`

be mapped into the repo's `comparable_headline_metrics` benchmark schema?

## Conclusion
**No, not yet.**

They can be stored as raw published `headline_metrics` for provenance, but they still cannot be promoted into `comparable_headline_metrics`.

## Why not

The comparable schema requires at minimum:

- `fill_rate`
- `avg_completion_ratio`
- `avg_slippage_bps`
- `avg_abs_slippage_bps`
- `remainder_size_hbar`

The slide values provide only partial slippage claims. They do not disclose enough to derive the other required fields.

## Specific blockers

1. **Missing required comparable fields**
   - no fill rate
   - no completion ratio
   - no remainder size
   - no average absolute slippage

2. **Methodology mismatch risk**
   - weighting basis is not explicit enough from the slide alone
   - reference-price convention is not explicit enough from the slide alone
   - fee treatment is not explicit enough from the slide alone
   - completion/failure treatment is not explicit enough from the slide alone

3. **Semantic mismatch risk**
   - `grid strategy slippage` is not yet shown to align directly with our `3A pure-book` or `3B hybrid` lane definitions

4. **Internal arithmetic ambiguity in the slide framing**
   - `15.47 - 2.82 = 12.65` bps
   - the slide framing shown to the operator also references a different slippage-delta figure
   - that suggests some alternate weighting/denominator, which is not disclosed well enough to normalize here

## Safe statement

Safe to say:

> Lambdaplex's published slide reports `15.47` bps average AMM slippage and `2.82` bps grid slippage, but those figures are currently stored as provenance-only published values and are not yet mergeable into the repo's comparable benchmark schema.

Not safe to say yet:

> Lambdaplex = `2.82` bps, directly comparable to our V2 / 3A / 3B study rollups.

## Repo action taken in RH-11

- benchmark payload status moved from `placeholder` to `incomplete`
- `15.47` / `2.82` stored in raw `headline_metrics`
- `comparable_headline_metrics` intentionally left empty
- source-notes updated with the exact blocker explanation

## Decision impact

This improves the honesty of the benchmark record, but it does **not** close the benchmark evidence gap.

The study still cannot claim Lambdaplex parity/outperformance until comparable headline metrics are recorded locally with sufficient methodological detail.
